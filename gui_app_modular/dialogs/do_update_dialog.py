# -*- coding: utf-8 -*-
"""
SQM 재고관리 - D/O 후속 연결 다이얼로그 (v5.6.6)
==================================================

입고 완료 후 D/O가 나중에 도착한 경우,
기존 LOT에 도착일/Free Time 정보를 UPDATE하는 전용 다이얼로그.

흐름:
  1. D/O PDF 파일 선택
  2. Gemini 파싱 → BL No., 도착일, Free Time 추출
  3. BL No. 기준으로 DB에서 LOT 매칭
  4. 미리보기 → 확인 → UPDATE
"""

import os
import sqlite3
import logging
import threading
from datetime import datetime as _dt
from typing import Optional

logger = logging.getLogger(__name__)

from core.constants import DEFAULT_WAREHOUSE


class DOUpdateDialog:
    """D/O 후속 연결 다이얼로그"""

    def __init__(self, parent, engine, log_fn=None, app=None):
        self.parent = parent
        self.engine = engine
        self.app = app
        self._log = log_fn or (lambda msg, **kw: logger.info(msg))

        self.file_path = None
        self.do_data = None
        self.matched_lots = []

        self.dialog = None
        self.tree = None
        self.btn_parse = None
        self.btn_apply = None

    def show(self) -> None:
        """다이얼로그 표시"""
        self._create_dialog()

    def _create_dialog(self) -> None:
        """UI 구성"""
        from ..utils.constants import tk, ttk, BOTH, X, Y, LEFT, RIGHT, TOP, BOTTOM, W, E
        from ..utils.ui_constants import ThemeColors, CustomMessageBox, DialogSize, center_dialog

        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("📋 D/O 후속 연결 — SQM v5.6.6")
        self.dialog.geometry(DialogSize.get_geometry(self.parent, 'medium'))
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        center_dialog(self.dialog, self.parent)

        _is_dark = ThemeColors.is_dark_theme(
            getattr(self.app, 'current_theme', 'flatly') if self.app else 'flatly')
        bg = ThemeColors.get('bg_card', _is_dark)
        fg = ThemeColors.get('text_primary', _is_dark)
        self.dialog.configure(bg=bg)

        # ── 상단: 파일 선택 ──
        top_frame = ttk.Frame(self.dialog, padding=10)
        top_frame.pack(fill=X)

        ttk.Label(top_frame, text="📋 D/O (인도지시서) PDF:").pack(side=LEFT)
        self.file_label = ttk.Label(top_frame, text="파일을 선택하세요", width=50)
        self.file_label.pack(side=LEFT, padx=5)
        ttk.Button(top_frame, text="📂 파일 선택", command=self._select_file).pack(side=LEFT)

        # ── 중단: 파싱 결과 ──
        info_frame = ttk.LabelFrame(self.dialog, text="📊 D/O 파싱 결과", padding=10)
        info_frame.pack(fill=X, padx=10, pady=5)

        self.info_labels = {}
        for key, label in [('bl_no', 'B/L No.'), ('arrival_date', '입항일'),
                           ('free_time_date', 'Free Time 만료'), ('free_time', 'Free Time (일)'),
                           ('warehouse', '창고')]:
            row = ttk.Frame(info_frame)
            row.pack(fill=X, pady=1)
            ttk.Label(row, text=f"  {label}:", width=18, anchor=W).pack(side=LEFT)
            lbl = ttk.Label(row, text="—", anchor=W)
            lbl.pack(side=LEFT)
            self.info_labels[key] = lbl

        # ── 매칭 LOT 리스트 ──
        tree_frame = ttk.LabelFrame(self.dialog, text="📦 매칭된 LOT 목록", padding=5)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        columns = ('lot_no', 'bl_no', 'product', 'net_weight', 'status', 'arrival_before')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)
        for col, hdr, w in [('lot_no', 'LOT No.', 130), ('bl_no', 'B/L No.', 120),
                             ('product', '제품', 120), ('net_weight', 'NET(Kg)', 90),
                             ('status', '상태', 80), ('arrival_before', '기존 입항일', 100)]:
            self.tree.heading(col, text=hdr)
            self.tree.column(col, width=w, anchor='center')
        self.tree.pack(fill=BOTH, expand=True)

        # ── 하단: 버튼 ──
        btn_frame = ttk.Frame(self.dialog, padding=10)
        btn_frame.pack(fill=X)

        self.status_label = ttk.Label(btn_frame, text="D/O PDF를 선택한 후 파싱하세요")
        self.status_label.pack(side=LEFT, padx=5)

        ttk.Button(btn_frame, text="❌ 닫기", command=self.dialog.destroy).pack(side=RIGHT, padx=5)
        self.btn_apply = ttk.Button(btn_frame, text="✅ 적용", command=self._apply_update, state='disabled')
        self.btn_apply.pack(side=RIGHT, padx=5)
        self.btn_parse = ttk.Button(btn_frame, text="🔍 파싱", command=self._start_parsing, state='disabled')
        self.btn_parse.pack(side=RIGHT, padx=5)

    def _select_file(self) -> None:
        """PDF 파일 선택"""
        from ..utils.constants import filedialog
        path = filedialog.askopenfilename(
            title="D/O PDF 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            self.file_path = path
            self.file_label.configure(text=os.path.basename(path))
            self.btn_parse.configure(state='normal')
            self.status_label.configure(text="🔍 파싱 버튼을 클릭하세요")

    def _start_parsing(self) -> None:
        """파싱 시작 (백그라운드)"""
        if not self.file_path:
            return
        self.btn_parse.configure(state='disabled')
        self.status_label.configure(text="⏳ D/O 파싱 중...")
        threading.Thread(target=self._parse_thread, daemon=True).start()

    def _parse_thread(self) -> None:
        """백그라운드 파싱"""
        try:
            from ..utils.constants import HAS_GEMINI, GEMINI_API_KEY
            if not HAS_GEMINI or not GEMINI_API_KEY:
                self._update_ui(lambda: self.status_label.configure(
                    text="❌ Gemini API Key 필요"))
                return

            from parsers.document_parser_v2 import DocumentParserV2
            parser = DocumentParserV2(gemini_api_key=GEMINI_API_KEY)

            do_data = None
            if hasattr(parser, 'parse_do'):
                do_data = parser.parse_do(self.file_path)
            elif hasattr(parser, 'parse_document'):
                do_data = parser.parse_document(self.file_path, doc_type='DO')

            if do_data:
                self.do_data = do_data
                self._update_ui(self._display_results)
            else:
                self._update_ui(lambda: self.status_label.configure(
                    text="❌ D/O 파싱 실패 — 결과 없음"))

        except Exception as e:
            logger.error(f"D/O 파싱 오류: {e}", exc_info=True)
            self._update_ui(lambda: self.status_label.configure(
                text=f"❌ 파싱 오류: {e}"))

    def _update_ui(self, fn):
        """메인 스레드에서 UI 업데이트"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, fn)

    def _display_results(self) -> None:
        """파싱 결과 표시 + LOT 매칭"""
        do = self.do_data

        # D/O 정보 표시
        bl_no = str(getattr(do, 'bl_no', '') or '')
        arrival = str(getattr(do, 'arrival_date', '') or '')
        warehouse = str(getattr(do, 'warehouse', DEFAULT_WAREHOUSE) or DEFAULT_WAREHOUSE)

        # Free Time 계산
        ft_date = ''
        ft_days = 0
        ft_infos = getattr(do, 'free_time_info', []) or []
        if ft_infos:
            for ft in ft_infos:
                ftd = getattr(ft, 'free_time_date', '') or (
                    ft.get('free_time_date', '') if isinstance(ft, dict) else '')
                if ftd:
                    ft_date = str(ftd)
                    break
        if not ft_date:
            ft_date = str(getattr(do, 'free_time_date', '') or '')

        if ft_date and arrival:
            try:
                _ft_dt = _dt.strptime(str(ft_date)[:10], '%Y-%m-%d').date()
                _arr_dt = _dt.strptime(str(arrival)[:10], '%Y-%m-%d').date()
                ft_days = max(0, (_ft_dt - _arr_dt).days)
            except (ValueError, TypeError):
                ft_days = 0

        self.info_labels['bl_no'].configure(text=bl_no or '—')
        self.info_labels['arrival_date'].configure(text=arrival or '—')
        self.info_labels['free_time_date'].configure(text=ft_date or '—')
        self.info_labels['free_time'].configure(text=f"{ft_days}일" if ft_days > 0 else '—')
        self.info_labels['warehouse'].configure(text=warehouse)

        # 파싱 결과 저장 (적용 시 사용)
        self._parsed_bl = bl_no
        self._parsed_arrival = arrival
        self._parsed_ft_date = ft_date
        self._parsed_ft_days = ft_days
        self._parsed_warehouse = warehouse

        # BL No.로 LOT 매칭
        self.matched_lots = []
        self.tree.delete(*self.tree.get_children())

        if not bl_no:
            self.status_label.configure(text="⚠️ B/L No.가 없어 LOT 매칭 불가")
            return

        try:
            rows = self.engine.db.fetchall(
                "SELECT lot_no, bl_no, product, net_weight, status, arrival_date "
                "FROM inventory WHERE bl_no LIKE ?",
                (f"%{bl_no}%",))

            if not rows:
                # BL prefix 제거 후 재시도
                bl_clean = bl_no
                for prefix in ['MAEU', 'MSCU', 'HLCU', 'CMDU', 'EGLV', 'COSU', 'OOLU', 'YMLU']:
                    if bl_no.upper().startswith(prefix):
                        bl_clean = bl_no[len(prefix):]
                        break
                if bl_clean != bl_no:
                    rows = self.engine.db.fetchall(
                        "SELECT lot_no, bl_no, product, net_weight, status, arrival_date "
                        "FROM inventory WHERE bl_no LIKE ?",
                        (f"%{bl_clean}%",))

            if rows:
                for row in rows:
                    r = dict(row) if hasattr(row, 'keys') else {
                        'lot_no': row[0], 'bl_no': row[1], 'product': row[2],
                        'net_weight': row[3], 'status': row[4], 'arrival_date': row[5]}
                    self.matched_lots.append(r)
                    self.tree.insert('', 'end', values=(
                        r.get('lot_no', ''),
                        r.get('bl_no', ''),
                        r.get('product', ''),
                        f"{float(r.get('net_weight', 0) or 0):,.1f}",
                        r.get('status', ''),
                        r.get('arrival_date', '') or '없음',
                    ))
                self.status_label.configure(
                    text=f"✅ {len(rows)}개 LOT 매칭됨 — '적용' 클릭 시 UPDATE")
                self.btn_apply.configure(state='normal')
            else:
                self.status_label.configure(text=f"⚠️ BL '{bl_no}'에 매칭되는 LOT 없음")

        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"LOT 매칭 오류: {e}")
            self.status_label.configure(text=f"❌ DB 오류: {e}")

    def _apply_update(self) -> None:
        """매칭된 LOT에 D/O 정보 UPDATE"""
        from ..utils.ui_constants import CustomMessageBox

        if not self.matched_lots:
            return

        count = len(self.matched_lots)
        if not CustomMessageBox.askyesno(self.dialog, "D/O 적용 확인",
                f"{count}개 LOT에 다음 정보를 업데이트합니다:\n\n"
                f"  입항일: {self._parsed_arrival}\n"
                f"  Free Time: {self._parsed_ft_days}일\n"
                f"  Free Time 만료: {self._parsed_ft_date}\n\n"
                f"진행하시겠습니까?"):
            return

        updated = 0
        try:
            with self.engine.db.transaction():
                for lot in self.matched_lots:
                    lot_no = lot.get('lot_no', '')
                    updates = []
                    params = []

                    if self._parsed_arrival:
                        updates.append("arrival_date = ?")
                        params.append(self._parsed_arrival)
                    if self._parsed_ft_days > 0:
                        updates.append("free_time = ?")
                        params.append(self._parsed_ft_days)

                    if updates:
                        updates.append("updated_at = ?")
                        params.append(_dt.now().strftime('%Y-%m-%d %H:%M:%S'))
                        sql = f"UPDATE inventory SET {', '.join(updates)} WHERE lot_no = ?"
                        params.append(lot_no)
                        self.engine.db.execute(sql, tuple(params))
                        updated += 1
                        self._log(f"  ✅ LOT {lot_no} ← 입항일={self._parsed_arrival}, FT={self._parsed_ft_days}일")

            self._log(f"📋 D/O 후속 연결 완료: {updated}/{count}개 LOT 업데이트")

            CustomMessageBox.showinfo(self.dialog, "D/O 적용 완료",
                f"✅ {updated}개 LOT 업데이트 완료\n\n"
                f"입항일: {self._parsed_arrival}\n"
                f"Free Time: {self._parsed_ft_days}일")

            # 새로고침
            if self.app:
                if hasattr(self.app, '_refresh_inventory'):
                    self.app._refresh_inventory()
                if hasattr(self.app, '_refresh_tonbag'):
                    self.app._refresh_tonbag()

            self.dialog.destroy()

        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"D/O 적용 오류: {e}", exc_info=True)
            self._log(f"❌ D/O 적용 실패 (롤백됨): {e}")
            CustomMessageBox.showerror(self.dialog, "오류", f"D/O 적용 실패:\n{e}")
