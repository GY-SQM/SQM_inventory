# -*- coding: utf-8 -*-
"""
SQM Inventory - Audit Flow Mixin (HD)
======================================

v8.7.4 - Extracted from outbound_handlers.py

Methods with `_s1_*` prefix + _on_s1_onestop_outbound — Audit flow
"""

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
import logging
import csv
import os
import json
import shutil
from datetime import datetime, date, timedelta

from ..utils.ui_constants import CustomMessageBox, setup_dialog_geometry_persistence
from utils.path_utils import get_app_base_dir
logger = logging.getLogger(__name__)


class AuditFlowMixin:
    """Audit flow mixin (HD).

    Mixed into OutboundHandlersMixin → SQMInventoryApp.
    """

    def _s1_get_proof_base_dir(self) -> str:
        """S1 근거문서 저장 폴더(일자별) 경로를 반환한다."""
        day_dir = os.path.join(
            get_app_base_dir(),
            "data",
            "proof_docs",
            date.today().isoformat(),
        )
        os.makedirs(day_dir, exist_ok=True)
        return day_dir

    def _s1_cleanup_old_proof_docs(self, retention_days: int = 90) -> dict:
        """보관기간 초과 근거문서 폴더를 정리한다."""
        base_dir = os.path.join(get_app_base_dir(), "data", "proof_docs")
        result = {"removed_dirs": 0, "removed_files": 0}
        if not os.path.isdir(base_dir):
            return result

        cutoff = date.today() - timedelta(days=retention_days)
        for name in os.listdir(base_dir):
            target_dir = os.path.join(base_dir, name)
            if not os.path.isdir(target_dir):
                continue
            try:
                folder_day = date.fromisoformat(name)
            except ValueError:
                continue
            if folder_day >= cutoff:
                continue
            file_count = 0
            for _, _, files in os.walk(target_dir):
                file_count += len(files)
            shutil.rmtree(target_dir, ignore_errors=True)
            result["removed_dirs"] += 1
            result["removed_files"] += file_count
        return result

    def _s1_get_audit_columns(self) -> set:
        """audit_log 테이블 컬럼 목록을 안전하게 조회한다."""
        try:
            rows = self.engine.db.fetchall("PRAGMA table_info(audit_log)")
            cols = set()
            for row in rows or []:
                if isinstance(row, dict):
                    name = row.get("name")
                else:
                    name = row[1] if len(row) > 1 else None
                if name:
                    cols.add(str(name))
            return cols
        except Exception:
            return set()

    def _s1_write_audit(self, event_type: str, payload=None, **meta) -> None:
        """환경별 audit_log 스키마 차이를 흡수해 이벤트를 기록한다."""
        cols = self._s1_get_audit_columns()
        if not cols:
            return
        if "event_type" not in cols or "created_at" not in cols:
            return
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        record = {
            "event_type": event_type,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if "payload" in cols:
            record["payload"] = payload_json
        if "event_data" in cols:
            record["event_data"] = payload_json
        for key, value in meta.items():
            if key in cols:
                record[key] = value
        col_names = list(record.keys())
        placeholders = ", ".join(["?"] * len(col_names))
        sql = f"INSERT INTO audit_log ({', '.join(col_names)}) VALUES ({placeholders})"
        try:
            self.engine.db.execute(sql, tuple(record[c] for c in col_names))
            if hasattr(self.engine.db, "conn") and self.engine.db.conn:
                self.engine.db.conn.commit()
        except Exception as e:
            logger.debug(f"[S1] audit 기록 스킵: {e}")

    def _s1_open_audit_viewer(self) -> None:
        """S1 감사 로그 뷰어를 연다."""
        from ..utils.constants import tk, ttk, BOTH, LEFT, RIGHT, X, END, filedialog

        cols = self._s1_get_audit_columns()
        if not cols:
            CustomMessageBox.showwarning(self.root, "안내", "audit_log 테이블을 찾지 못했습니다.")
            return

        note_col = "user_note" if "user_note" in cols else ("event_data" if "event_data" in cols else "payload")
        dialog = create_themed_toplevel(self.root)
        dialog.title("감사 로그")
        dialog.transient(self.root)
        setup_dialog_geometry_persistence(dialog, "audit_log_dialog", self.root, "large")

        top = ttk.Frame(dialog)
        top.pack(fill=X, padx=8, pady=6)
        ttk.Label(top, text="이벤트").pack(side=LEFT, padx=4)
        event_var = tk.StringVar(value="전체")
        ttk.Entry(top, textvariable=event_var, width=24).pack(side=LEFT, padx=4)
        ttk.Label(top, text="시작일").pack(side=LEFT, padx=4)
        from_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(top, textvariable=from_var, width=12).pack(side=LEFT, padx=2)
        ttk.Label(top, text="종료일").pack(side=LEFT, padx=4)
        to_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(top, textvariable=to_var, width=12).pack(side=LEFT, padx=2)

        tree = ttk.Treeview(dialog, columns=("id", "event_type", "note", "created_at"), show="headings", height=18)
        tree.heading("id", text="ID", anchor='center')
        tree.heading("event_type", text="EVENT", anchor='center')
        tree.heading("note", text="NOTE", anchor='center')
        tree.heading("created_at", text="TIME", anchor='center')
        tree.column("id", width=60, anchor="center")
        tree.column("event_type", width=220, anchor="w")
        tree.column("note", width=430, anchor="w")
        tree.column("created_at", width=180, anchor="center")
        tree.pack(fill=BOTH, expand=True, padx=8, pady=4)
        status_var = tk.StringVar(value="")
        ttk.Label(dialog, textvariable=status_var).pack(fill=X, padx=8, pady=(0, 6))

        cache_rows = {"rows": []}

        def _search():
            tree.delete(*tree.get_children())
            sql = (
                f"SELECT id, event_type, {note_col} AS note, created_at "
                f"FROM audit_log WHERE 1=1"
            )
            params = []
            event_text = event_var.get().strip()
            if event_text and event_text != "전체":
                sql += " AND event_type = ?"
                params.append(event_text)
            if "created_at" in cols and from_var.get().strip():
                sql += " AND created_at >= ?"
                params.append(f"{from_var.get().strip()} 00:00:00")
            if "created_at" in cols and to_var.get().strip():
                sql += " AND created_at <= ?"
                params.append(f"{to_var.get().strip()} 23:59:59")
            sql += " ORDER BY id DESC LIMIT 500"
            rows = self.engine.db.fetchall(sql, tuple(params))
            cache_rows["rows"] = rows
            for row in rows:
                note = (row.get("note") or "") if isinstance(row, dict) else ""
                tree.insert(
                    "",
                    END,
                    values=(
                        row.get("id", ""),
                        row.get("event_type", ""),
                        str(note)[:90],
                        row.get("created_at", ""),
                    ),
                )
            status_var.set(f"조회 {len(rows)}건")

        def _export_csv():
            rows = cache_rows["rows"]
            if not rows:
                CustomMessageBox.showwarning(dialog, "안내", "내보낼 데이터가 없습니다.")
                return
            out_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="감사 로그 CSV 저장",
                defaultextension=".csv",
                initialfile=f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
            )
            if not out_path:
                return
            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "EVENT", "NOTE", "TIME"])
                for row in rows:
                    writer.writerow([
                        row.get("id", ""),
                        row.get("event_type", ""),
                        row.get("note", ""),
                        row.get("created_at", ""),
                    ])
            status_var.set(f"CSV 저장 완료: {os.path.basename(out_path)}")
            self._s1_write_audit(
                "AUDIT_EXPORT",
                {"count": len(rows), "file": os.path.basename(out_path)},
                user_note=f"감사 로그 CSV 내보내기 {len(rows)}건",
            )

        btn = ttk.Frame(dialog)
        btn.pack(fill=X, padx=8, pady=6)
        ttk.Button(top, text="조회", command=_search).pack(side=LEFT, padx=6)
        ttk.Button(btn, text="CSV 저장", command=_export_csv).pack(side=LEFT, padx=4)
        ttk.Button(btn, text="닫기", command=dialog.destroy).pack(side=RIGHT, padx=4)
        _search()

    def _on_s1_onestop_outbound(self) -> None:
        """S1 원스톱 출고: 4단계 워크플로우 (v6.3.1)
        입력(붙여넣기) → 톤백선택(LOT일괄/랜덤/수동) → 스캔검증(하드스톱) → 확정
        """
        try:
            from ..dialogs.onestop_outbound import S1OneStopOutboundDialog
            dlg = S1OneStopOutboundDialog(self, self.engine)
            dlg.show()
        except (ImportError, AttributeError) as e:
            logger.error(f"S1 원스톱 출고 오류: {e}", exc_info=True)
            from ..utils.ui_constants import CustomMessageBox
            CustomMessageBox.showerror(self.root, "오류", f"S1 원스톱 출고 열기 실패:\n{e}")
