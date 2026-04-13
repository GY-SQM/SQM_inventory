# -*- coding: utf-8 -*-
"""
SQM Inventory - Simple Outbound Flow Mixin (HA)
================================================

v8.7.4 - Extracted from outbound_handlers.py

Methods with `_sob_*` prefix + _on_simple_outbound + _build_simple_outbound_ui
"""

from gui_app_modular.utils.ui_constants import create_themed_toplevel  # v8.0.9
from gui_app_modular.utils.ui_constants import tc
import logging
import csv
import os
import hashlib
import shutil
from datetime import datetime

from ..utils.ui_constants import CustomMessageBox, ThemeColors, apply_tooltip, setup_dialog_geometry_persistence
logger = logging.getLogger(__name__)

try:
    import openpyxl  # type: ignore
    HAS_OPENPYXL = True
except Exception:
    HAS_OPENPYXL = False


class SimpleOutboundFlowMixin:
    """Simple outbound UI flow mixin (HA).

    Mixed into OutboundHandlersMixin → SQMInventoryApp.
    """

    def _on_simple_outbound(self) -> None:
        """Simple outbound dialog - enter LOT and quantity (v4.0.3: UI 분리, v8.6.4: SRP 분해)"""
        from ..utils.constants import tk, ttk, LEFT, RIGHT, X, END, filedialog
        from ..utils.constants import HAS_TTKBOOTSTRAP

        # v4.0.3: UI 위젯 생성을 별도 메서드로 분리
        w = self._build_simple_outbound_ui()
        dialog, lot_text, preview_tree = w['dialog'], w['lot_text'], w['preview_tree']
        summary_var, customer_var = w['summary_var'], w['customer_var']
        sale_ref_var, btn_frame = w['sale_ref_var'], w['btn_frame']

        # 공유 상태 번들
        st = {
            "dialog": dialog, "lot_text": lot_text, "preview_tree": preview_tree,
            "summary_var": summary_var, "customer_var": customer_var,
            "sale_ref_var": sale_ref_var, "btn_frame": btn_frame,
            "proof_docs": [], "proof_hashes": set(),
            "tonbag_meta_by_item": {},
            "out_scan_state": {"loaded": False, "records": [], "matched": [], "unmatched": []},
            "proof_status_var": tk.StringVar(value="첨부 없음"),
            "out_scan_status_var": tk.StringVar(value="파일 미선택"),
            "unmatched_var": tk.StringVar(value=""),
            "proof_base_dir": self._s1_get_proof_base_dir(),
            "proof_listbox": None,  # set after widget creation
        }

        # v6.3.0: 근거문서 자동정리
        cleanup_result = self._s1_cleanup_old_proof_docs(retention_days=90)
        if cleanup_result.get("removed_dirs", 0) > 0:
            self._s1_write_audit(
                "PROOF_CLEANUP",
                cleanup_result,
                user_note=f"근거문서 자동정리 {cleanup_result['removed_dirs']}개 폴더",
            )

        # 클로저 → sub-method 호출 래퍼
        def _attach_proof_doc():
            self._sob_attach_proof_doc(st)

        def _preview_proof_doc(event=None):
            self._sob_preview_proof_doc(st)

        def _load_out_scan_file():
            self._sob_load_out_scan_file(st)

        def on_preview():
            self._sob_on_preview(st)

        def on_execute():
            self._sob_on_execute(st)

        def on_get_selected_lot():
            self._sob_on_get_selected_lot(st)

        # v6.3.0: 근거문서 + OUT 스캔 업로드 바
        self._sob_build_aux_widgets(st, _attach_proof_doc, _preview_proof_doc, _load_out_scan_file)

        # 버튼 및 키바인딩
        self._sob_build_buttons(
            st, on_preview, on_execute, on_get_selected_lot, HAS_TTKBOOTSTRAP,
        )

    # ------------------------------------------------------------------
    # _on_simple_outbound sub-methods (v8.6.4 [SRP])
    # ------------------------------------------------------------------

    @staticmethod
    def _sob_normalize_tonbag_key(raw):  # v8.6.4 [SRP]
        """톤백 키 정규화."""
        if raw is None:
            return ""
        return str(raw).strip().upper().replace(" ", "").replace("-", "").replace("_", "")

    @staticmethod
    def _sob_hash_file(path):  # v8.6.4 [SRP]
        """SHA-256 해시 계산."""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def _sob_attach_proof_doc(self, st):  # v8.6.4 [SRP]
        """근거문서 첨부 처리."""
        from ..utils.constants import END, filedialog
        dialog = st["dialog"]
        proof_docs = st["proof_docs"]
        proof_hashes = st["proof_hashes"]
        proof_base_dir = st["proof_base_dir"]
        proof_listbox = st["proof_listbox"]
        proof_status_var = st["proof_status_var"]

        paths = filedialog.askopenfilenames(
            parent=dialog,
            title="근거문서 선택",
            filetypes=[
                ("지원 파일", "*.pdf *.png *.jpg *.jpeg *.xlsx *.csv *.txt *.docx"),
                ("모든 파일", "*.*"),
            ],
        )
        for fpath in paths:
            try:
                fhash = self._sob_hash_file(fpath)
                if fhash in proof_hashes:
                    CustomMessageBox.showwarning(dialog, "중복 파일",
                                                 f"{os.path.basename(fpath)}\n이미 첨부된 문서입니다.")
                    continue
                fname = os.path.basename(fpath)
                stored_name = f"{fhash[:8]}_{fname}"
                stored_path = os.path.join(proof_base_dir, stored_name)
                if not os.path.exists(stored_path):
                    shutil.copy2(fpath, stored_path)
                proof_hashes.add(fhash)
                proof_docs.append({
                    "id": fhash[:16],
                    "name": fname,
                    "path": stored_path,
                    "original_path": fpath,
                    "size": os.path.getsize(fpath),
                    "hash": fhash,
                    "added_at": datetime.now().strftime("%H:%M:%S"),
                })
                self._s1_write_audit(
                    "PROOF_ATTACH",
                    {
                        "name": fname,
                        "hash": fhash,
                        "size": os.path.getsize(fpath),
                        "stored_path": stored_path,
                    },
                    user_note=f"근거문서 첨부: {fname}",
                )
            except Exception as e:
                logger.error(f"[SimpleOutbound] 근거문서 첨부 실패: {fpath} -> {e}")
                CustomMessageBox.showerror(dialog, "첨부 오류", str(e))
        proof_listbox.delete(0, END)
        for d in proof_docs:
            proof_listbox.insert(END, f"📄 {d['name']} ({d['size']/1024:.1f}KB) [{d['added_at']}]")
        proof_status_var.set(f"📎 {len(proof_docs)}건 첨부" if proof_docs else "첨부 없음")

    def _sob_preview_proof_doc(self, st):  # v8.6.4 [SRP]
        """근거문서 미리보기."""
        from ..utils.constants import tk
        dialog = st["dialog"]
        proof_docs = st["proof_docs"]
        proof_listbox = st["proof_listbox"]

        sel = proof_listbox.curselection()
        if not sel:
            return
        doc = proof_docs[sel[0]]
        path = doc["path"]
        if not os.path.exists(path):
            CustomMessageBox.showwarning(dialog, "파일 없음", path)
            return
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            try:
                os.startfile(path)
            except Exception:
                CustomMessageBox.showinfo(dialog, "문서 정보", f"PDF 파일:\n{path}")
            return
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            try:
                from PIL import Image, ImageTk
            except Exception:
                CustomMessageBox.showwarning(dialog, "미리보기 불가", "Pillow 미설치로 이미지 미리보기를 열 수 없습니다.")
                return
            win = create_themed_toplevel(dialog)
            win.title(f"미리보기 - {doc['name']}")
            img = Image.open(path)
            img.thumbnail((800, 600), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
            ph = ImageTk.PhotoImage(img)
            lb = tk.Label(win, image=ph)
            lb.image = ph
            lb.pack()
            return
        CustomMessageBox.showinfo(
            dialog, "문서 정보",
            f"파일: {doc['name']}\n크기: {doc['size']/1024:.1f}KB\nhash: {doc['hash'][:24]}..."
        )

    def _sob_parse_out_scan_file(self, path):  # v8.6.4 [SRP]
        """OUT 스캔 파일 파싱 (xlsx/csv/tsv)."""
        ext = os.path.splitext(path)[1].lower()
        records = []
        if ext in (".xlsx", ".xls") and HAS_OPENPYXL:
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not rows:
                return []
            header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
            key_idx = next((i for i, h in enumerate(header) if any(k in h for k in ["tonbag_id", "tonbag", "tb_id", "uid", "id", "톤백"])), None)
            wt_idx = next((i for i, h in enumerate(header) if any(k in h for k in ["weight", "kg", "무게", "중량"])), None)
            start = 1 if key_idx is not None else 0
            if key_idx is None:
                key_idx, wt_idx = 0, 1
            for row in rows[start:]:
                if not row or len(row) <= key_idx:
                    continue
                key = str(row[key_idx]).strip() if row[key_idx] is not None else ""
                if not key:
                    continue
                w = 0.0
                if wt_idx is not None and len(row) > wt_idx and row[wt_idx] is not None:
                    try:
                        w = float(str(row[wt_idx]).replace(",", "").strip())
                    except Exception:
                        w = 0.0
                records.append({"raw_key": key, "key": self._sob_normalize_tonbag_key(key), "weight": w})
            return records

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(2048)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t|;")
            except Exception:
                dialect = csv.excel
            rows = list(csv.reader(f, dialect))
        if not rows:
            return []
        header = [str(c).strip().lower() for c in rows[0]]
        key_idx = next((i for i, h in enumerate(header) if any(k in h for k in ["tonbag_id", "tonbag", "tb_id", "uid", "id", "톤백"])), None)
        wt_idx = next((i for i, h in enumerate(header) if any(k in h for k in ["weight", "kg", "무게", "중량"])), None)
        start = 1 if key_idx is not None else 0
        if key_idx is None:
            key_idx, wt_idx = 0, 1
        for row in rows[start:]:
            if not row or len(row) <= key_idx:
                continue
            key = str(row[key_idx]).strip()
            if not key:
                continue
            w = 0.0
            if wt_idx is not None and len(row) > wt_idx:
                try:
                    w = float(str(row[wt_idx]).replace(",", "").strip() or 0)
                except Exception:
                    w = 0.0
            records.append({"raw_key": key, "key": self._sob_normalize_tonbag_key(key), "weight": w})
        return records

    def _sob_load_out_scan_file(self, st):  # v8.6.4 [SRP]
        """OUT 스캔 파일 불러오기 및 매칭."""
        from ..utils.constants import filedialog
        dialog = st["dialog"]
        preview_tree = st["preview_tree"]
        tonbag_meta_by_item = st["tonbag_meta_by_item"]
        out_scan_state = st["out_scan_state"]
        out_scan_status_var = st["out_scan_status_var"]
        unmatched_var = st["unmatched_var"]

        path = filedialog.askopenfilename(
            parent=dialog,
            title="OUT 스캔 파일 선택",
            filetypes=[("스캔 파일", "*.csv *.tsv *.txt *.xlsx *.xls"), ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            recs = self._sob_parse_out_scan_file(path)
        except Exception as e:
            CustomMessageBox.showerror(dialog, "파싱 오류", f"OUT 파일 파싱 실패:\n{e}")
            return
        if not recs:
            CustomMessageBox.showwarning(dialog, "경고", "유효한 스캔 데이터가 없습니다.")
            return

        selected_items = preview_tree.selection()
        selected_keys = set()
        for iid in selected_items:
            meta = tonbag_meta_by_item.get(iid, {})
            if meta.get("key"):
                selected_keys.add(meta["key"])
        if not selected_keys:
            CustomMessageBox.showwarning(dialog, "안내", "Preview 후 출고 톤백을 먼저 선택하세요.")
            return

        matched = [r for r in recs if r["key"] in selected_keys]
        unmatched = [r for r in recs if r["key"] not in selected_keys]
        out_scan_state["loaded"] = True
        out_scan_state["records"] = recs
        out_scan_state["matched"] = matched
        out_scan_state["unmatched"] = unmatched

        out_scan_status_var.set(
            f"📊 {os.path.basename(path)} | 전체 {len(recs)}건 | 매칭 {len(matched)} | 미매칭 {len(unmatched)}"
        )
        if unmatched:
            preview_ids = ", ".join(r["raw_key"] for r in unmatched[:5])
            more = f" 외 {len(unmatched)-5}건" if len(unmatched) > 5 else ""
            unmatched_var.set(f"⛔ 미매칭 {len(unmatched)}건 (무단 출고 의심): {preview_ids}{more}")
            self._s1_write_audit(
                "UNMATCHED_SCAN",
                {
                    "file": os.path.basename(path),
                    "count": len(unmatched),
                    "sample": [r.get("raw_key", "") for r in unmatched[:20]],
                },
                user_note=f"OUT 스캔 미매칭 {len(unmatched)}건",
            )
        else:
            unmatched_var.set("")

    def _sob_on_preview(self, st):  # v8.6.4 [SRP]
        """Preview: LOT별 톤백 상세 표시 (v3.8.4)."""
        from ..utils.constants import END
        preview_tree = st["preview_tree"]
        lot_text = st["lot_text"]
        summary_var = st["summary_var"]
        tonbag_meta_by_item = st["tonbag_meta_by_item"]

        preview_tree.delete(*preview_tree.get_children())
        tonbag_meta_by_item.clear()

        lines_input = lot_text.get("1.0", END).strip().split('\n')
        total_kg = 0
        tonbag_count = 0
        warnings = []
        lot_requests = {}

        for line in lines_input:
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.replace('\t', ',').split(',')]

            if len(parts) < 2:
                warnings.append(f"형식 오류: {line}")
                continue

            lot_no = parts[0]
            try:
                qty_mt = float(parts[1])
            except ValueError:
                warnings.append(f"수량 오류: {line}")
                continue
            lot_requests[lot_no] = lot_requests.get(lot_no, 0.0) + (qty_mt * 1000)

        # v8.2.0 N+1 최적화: inventory + tonbag 일괄 pre-fetch
        _inv_map_oh, _tb_map_oh = self._sob_prefetch_lot_data(lot_requests)

        for lot_no, qty_kg in lot_requests.items():
            t_kg, t_cnt = self._sob_preview_single_lot(
                st, lot_no, qty_kg, _inv_map_oh, _tb_map_oh, warnings,
            )
            total_kg += t_kg
            tonbag_count += t_cnt

        # 스타일
        preview_tree.tag_configure('error', foreground=tc('danger'))
        preview_tree.tag_configure('lot_header', background=tc('shipped'), font=('', 13, 'bold'))
        preview_tree.tag_configure('tonbag', foreground=ThemeColors.get('text_primary', False))

        summary_var.set(f"톤백 {tonbag_count}개 / {total_kg/1000:.3f} MT 출고 예정")

        if warnings:
            CustomMessageBox.showwarning(self.root, "확인 필요", "\n".join(warnings[:10]))

    def _sob_prefetch_lot_data(self, lot_requests):  # v8.6.4 [SRP]
        """inventory + tonbag 일괄 pre-fetch (N+1 최적화)."""
        from collections import defaultdict as _ddict
        _lot_keys = list(lot_requests.keys())
        _ph_oh = ','.join('?' * len(_lot_keys))
        _inv_rows_oh = self.engine.db.fetchall(
            f"SELECT lot_no, current_weight, product FROM inventory WHERE lot_no IN ({_ph_oh})",
            tuple(_lot_keys)
        ) or [] if _lot_keys else []
        _inv_map_oh = {
            (r.get('lot_no') if isinstance(r, dict) else r[0]): r
            for r in _inv_rows_oh
        }
        _tb_rows_oh = self.engine.db.fetchall(
            f"SELECT id, lot_no, sub_lt, weight, status, location "
            f"FROM inventory_tonbag "
            f"WHERE lot_no IN ({_ph_oh}) AND status = 'AVAILABLE' "
            f"ORDER BY lot_no, sub_lt DESC",
            tuple(_lot_keys)
        ) or [] if _lot_keys else []
        _tb_map_oh = _ddict(list)
        for _r in _tb_rows_oh:
            _k = _r.get('lot_no') if isinstance(_r, dict) else _r[1]
            _tb_map_oh[_k].append(_r)
        return _inv_map_oh, _tb_map_oh

    def _sob_preview_single_lot(self, st, lot_no, qty_kg, inv_map, tb_map, warnings):  # v8.6.4 [SRP]
        """단일 LOT에 대한 프리뷰 행 생성. (total_kg, tonbag_count) 반환."""
        from ..utils.constants import END
        preview_tree = st["preview_tree"]
        tonbag_meta_by_item = st["tonbag_meta_by_item"]
        total_kg = 0
        tonbag_count = 0

        # LOT 존재 확인 (cache)
        lot_info = inv_map.get(lot_no)

        if not lot_info:
            preview_tree.insert('', END, values=(
                lot_no, '-', '-', '-', '❌ 미발견', '-'
            ), tags=('error',))
            warnings.append(f"LOT 미발견: {lot_no}")
            return total_kg, tonbag_count

        avail_kg = (lot_info.get('current_weight') if isinstance(lot_info, dict)
                    else lot_info[1]) or 0
        product = (lot_info.get('product') if isinstance(lot_info, dict)
                   else lot_info[2]) or '-'

        if avail_kg < qty_kg - 0.01:
            warnings.append(f"재고 부족: {lot_no} (판매가능: {avail_kg:.0f}kg, 요청: {qty_kg:.0f}kg)")

        # 판매가능 톤백 (cache)
        tonbags = tb_map.get(lot_no, [])

        # LOT 헤더 행
        preview_tree.insert('', END, iid=f"LOT_{lot_no}",
            values=(f"📦 {lot_no}", '', product, f"{avail_kg:,.0f}",
                    f"요청: {qty_kg:,.0f}kg", ''),
            tags=('lot_header',))

        remaining = qty_kg
        for tb in tonbags:
            if remaining <= 0.01:
                break
            tb_weight = tb['weight'] or 0
            sub_lt = tb['sub_lt']
            loc = tb['location'] or ''
            tb_id = str(tb.get('id') or f"{lot_no}-{sub_lt}")
            normalized_key = self._sob_normalize_tonbag_key(tb_id)

            status = '✅ 출고' if remaining >= tb_weight else '⚠️ 초과'

            item_id = preview_tree.insert('', END, values=(
                f"  └ {lot_no}", str(sub_lt), product,
                f"{tb_weight:,.0f}", status, loc
            ), tags=('tonbag',))
            tonbag_meta_by_item[item_id] = {
                "lot_no": lot_no,
                "tonbag_id": tb_id,
                "key": normalized_key,
                "weight": float(tb_weight or 0),
            }

            # 자동 선택 (요청 수량 만큼)
            preview_tree.selection_add(item_id)

            remaining -= tb_weight
            total_kg += tb_weight
            tonbag_count += 1

        return total_kg, tonbag_count

    def _sob_on_execute(self, st):  # v8.6.4 [SRP]
        """Execute outbound (v3.8.4: 선택된 톤백 기반)."""
        import sqlite3
        from ..utils.constants import END
        dialog = st["dialog"]
        preview_tree = st["preview_tree"]
        lot_text = st["lot_text"]
        customer_var = st["customer_var"]
        sale_ref_var = st["sale_ref_var"]
        proof_docs = st["proof_docs"]
        tonbag_meta_by_item = st["tonbag_meta_by_item"]
        out_scan_state = st["out_scan_state"]

        customer = customer_var.get().strip()
        sale_ref = sale_ref_var.get().strip()

        if not customer:
            CustomMessageBox.showwarning(self.root, "입력 필요", "고객명을 입력하세요.")
            return

        # 선택된 톤백 항목 수집
        allocation_items = self._sob_collect_allocation_items(
            st, customer, sale_ref,
        )
        if allocation_items is None:
            return  # 중단됨 (에러 메시지 이미 표시)

        if not allocation_items:
            CustomMessageBox.showwarning(self.root, "입력 필요", "Preview 후 톤백을 선택하거나 LOT를 입력하세요.")
            return

        # v5.0.9: 톤백/샘플 구분 카운트
        from ..dialogs.allocation_preview import _is_sample_item
        tonbag_items = [i for i in allocation_items if not _is_sample_item(i)]
        sample_items = [i for i in allocation_items if _is_sample_item(i)]
        tonbag_qty = sum(i.get('qty_mt', 0) for i in tonbag_items)
        sample_qty = sum(i.get('qty_mt', 0) for i in sample_items)
        total_qty = tonbag_qty + sample_qty

        # v6.1.0: 빠른 출고 8개 톤백 제한 (초과 시 일반 출고 전환 안내)
        if len(tonbag_items) > 8:
            go_normal = CustomMessageBox.askyesno(
                self.root, "수량 초과",
                f"빠른 출고는 최대 8개 톤백까지 가능합니다.\n"
                f"(선택: {len(tonbag_items)}개)\n\n"
                f"일반 출고(배정표)로 전환하시겠습니까?"
            )
            if go_normal and hasattr(self, '_on_allocation_dialog'):
                dialog.destroy()
                self._on_allocation_dialog()
            return

        # v6.1.0: source='QUICK' 마킹 (allocation_plan 추적용)
        for _qi in allocation_items:
            _qi['source'] = 'QUICK'

        # Confirm (v6.1.0: 판매화물 결정 용어 + PICKED 멈춤 안내)
        confirm_msg = (
            f"판매화물 결정을 진행할까요?\n\n"
            f"고객: {customer}\n"
            f"📦 톤백: {len(tonbag_items)}개 ({tonbag_qty:.3f} MT)\n"
            f"🧪 샘플: {len(sample_items)}개 ({sample_qty:.3f} MT)\n"
            f"📎 근거문서: {len(proof_docs)}건\n"
            f"합계: {len(allocation_items)}건 ({total_qty:.3f} MT)\n\n"
            f"※ 현장 출고 후 [출고 확정]으로 최종 처리하세요."
        )
        if not CustomMessageBox.askyesno(self.root, "출고 확인", confirm_msg):
            return

        # Execute
        self._sob_run_outbound_engine(st, allocation_items, customer, sale_ref)

    def _sob_collect_allocation_items(self, st, customer, sale_ref):  # v8.6.4 [SRP]
        """선택된 톤백 / fallback 텍스트에서 allocation_items 수집.
        Returns list on success, None if hard-stopped."""
        from ..utils.constants import END
        preview_tree = st["preview_tree"]
        lot_text = st["lot_text"]
        proof_docs = st["proof_docs"]
        tonbag_meta_by_item = st["tonbag_meta_by_item"]
        out_scan_state = st["out_scan_state"]

        selected = preview_tree.selection()
        allocation_items = []

        if selected:
            # 선택된 톤백에서 LOT별 수량 집계
            lot_weights = {}
            selected_keys = set()
            selected_count = 0
            for item_id in selected:
                values = preview_tree.item(item_id)['values']
                tags = preview_tree.item(item_id).get('tags', ())

                if 'lot_header' in tags:
                    continue  # LOT 헤더는 건너뜀
                selected_count += 1
                meta = tonbag_meta_by_item.get(item_id, {})
                lot_no = str(meta.get("lot_no") or str(values[0]).replace('└', '').strip())
                weight = float(meta.get("weight") or 0)
                if weight <= 0:
                    try:
                        weight = float(str(values[3]).replace(',', ''))
                    except (ValueError, IndexError):
                        continue
                if meta.get("key"):
                    selected_keys.add(meta["key"])
            if selected_count > 0 and len(selected_keys) < selected_count:
                CustomMessageBox.showerror(
                    self.root,
                    "출고 중단",
                    "선택 톤백 키가 중복되어 출고를 중단합니다.\n"
                    "톤백 선택을 해제 후 다시 선택해 주세요.",
                )
                return None

                if lot_no not in lot_weights:
                    lot_weights[lot_no] = 0
                lot_weights[lot_no] += weight

            for lot_no, weight_kg in lot_weights.items():
                allocation_items.append({
                    'lot_no': lot_no,
                    'weight_kg': weight_kg,
                    'qty_mt': weight_kg / 1000.0,
                    'sold_to': customer,
                    'customer': customer,
                    'sale_ref': sale_ref,
                    'proof_doc_ids': [d['id'] for d in proof_docs],
                })

            # OUT 스캔 파일이 있으면 미매칭 하드스톱
            if out_scan_state.get("loaded"):
                unmatched = out_scan_state.get("unmatched", [])
                if unmatched:
                    CustomMessageBox.showerror(
                        self.root, "출고 중단",
                        f"OUT 스캔 파일에 미매칭 톤백 {len(unmatched)}건이 있어 출고를 중단합니다.\n"
                        f"(무단 출고 의심)\n미매칭을 정리한 후 다시 진행하세요."
                    )
                    return None

        if not allocation_items:
            # Fallback: 텍스트 입력에서 추출
            lines = lot_text.get("1.0", END).strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.replace('\t', ',').split(',')]
                if len(parts) < 2:
                    continue
                lot_no = parts[0]
                try:
                    qty_mt = float(parts[1])
                except ValueError:
                    continue
                allocation_items.append({
                    'lot_no': lot_no,
                    'qty_mt': qty_mt,
                    'sold_to': customer,
                    'customer': customer,
                    'sale_ref': sale_ref,
                    'proof_doc_ids': [d['id'] for d in proof_docs],
                })

        return allocation_items

    def _sob_run_outbound_engine(self, st, allocation_items, customer, sale_ref):  # v8.6.4 [SRP]
        """엔진 호출 및 결과 처리 (v3.8.4: All-or-Nothing)."""
        import sqlite3
        dialog = st["dialog"]
        proof_docs = st["proof_docs"]
        out_scan_state = st["out_scan_state"]

        try:
            if hasattr(self.engine, 'process_outbound_safe'):
                try:
                    result = self.engine.process_outbound_safe(
                        allocation_items, source='QUICK', stop_at_picked=True
                    )
                except TypeError:
                    result = self.engine.process_outbound(
                        allocation_items, source='QUICK', stop_at_picked=True
                    )
                except (ValueError, RuntimeError, sqlite3.OperationalError) as pf_err:
                    err_msg = str(pf_err)
                    display_msg = err_msg[:500] + '...' if len(err_msg) > 500 else err_msg
                    self._log(f"❌ 출고 검증 실패 (All-or-Nothing): {display_msg[:200]}")
                    CustomMessageBox.showerror(self.root, "출고 검증 실패",
                        f"All-or-Nothing 검증에서 오류가 발견되어\n전체 출고가 중단되었습니다.\n\n{display_msg}")
                    return
            else:
                result = self.engine.process_outbound(
                    allocation_items, source='QUICK', stop_at_picked=True
                )

            if result.get('success') or result.get('processed', 0) > 0:
                processed = result.get('lots_processed', result.get('processed', 0))
                picked = result.get('total_picked', 0)
                msg = (f"판매화물 결정 완료!\n\n"
                       f"처리: {processed}건\n"
                       f"총 중량: {picked:.3f} MT\n\n"
                       f"현장 출고 확인 후 [출고 확정]을 실행하세요.")

                if result.get('warnings'):
                    msg += "\n\n경고:\n" + "\n".join(result['warnings'][:5])

                CustomMessageBox.showinfo(self.root, "완료", msg)
                self._log(f"✅ 빠른 출고: {processed}건, {picked:.3f} MT")
                self._s1_write_audit(
                    "OUTBOUND_EXECUTE",
                    {
                        "customer": customer,
                        "sale_ref": sale_ref,
                        "lots": len(allocation_items),
                        "picked_mt": picked,
                        "proof_docs": len(proof_docs),
                        "out_scan_loaded": bool(out_scan_state.get("loaded")),
                    },
                    user_note=f"빠른 출고 실행: {customer}, {picked:.3f} MT",
                )

                dialog.destroy()
                self._refresh_after_outbound_action("SIMPLE_OUTBOUND_EXECUTE")
            else:
                errs = '\n'.join(result.get('errors', ['알 수 없는 오류']))
                CustomMessageBox.showerror(self.root, "출고 실패", f"출고 처리 실패:\n{errs}")

        except (ValueError, RuntimeError, KeyError, sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            logger.error(f"출고 오류: {e}")
            err_msg = str(e)[:500]
            CustomMessageBox.showerror(self.root, "출고 오류", f"출고 처리 중 오류:\n\n{err_msg}")

    def _sob_build_aux_widgets(self, st, attach_cmd, preview_cmd, load_scan_cmd):  # v8.6.4 [SRP]
        """근거문서 + OUT 스캔 업로드 위젯 생성."""
        from ..utils.constants import tk, ttk, LEFT, X
        dialog = st["dialog"]
        btn_frame = st["btn_frame"]
        proof_status_var = st["proof_status_var"]
        out_scan_status_var = st["out_scan_status_var"]
        unmatched_var = st["unmatched_var"]

        aux_frame = ttk.Frame(btn_frame.master)
        aux_frame.pack(fill=X, pady=(0, 6))

        proof_frame = ttk.LabelFrame(aux_frame, text="📎 근거문서 (선택)")
        proof_frame.pack(fill=X, pady=(0, 4))
        proof_btn_row = ttk.Frame(proof_frame)
        proof_btn_row.pack(fill=X, padx=6, pady=4)
        ttk.Button(proof_btn_row, text="+ 파일 첨부", command=attach_cmd).pack(side=LEFT, padx=2)
        ttk.Label(proof_btn_row, textvariable=proof_status_var).pack(side=LEFT, padx=8)
        proof_listbox = tk.Listbox(proof_frame, height=3, font=("Consolas", 9))
        proof_listbox.pack(fill=X, padx=6, pady=(0, 6))
        proof_listbox.bind("<Double-1>", lambda e: preview_cmd(e))
        st["proof_listbox"] = proof_listbox

        out_frame = ttk.LabelFrame(aux_frame, text="📊 OUT 스캔 파일")
        out_frame.pack(fill=X)
        out_btn_row = ttk.Frame(out_frame)
        out_btn_row.pack(fill=X, padx=6, pady=4)
        ttk.Button(out_btn_row, text="📂 파일 불러오기 (csv/xlsx)", command=load_scan_cmd).pack(side=LEFT, padx=2)
        ttk.Button(out_btn_row, text="📋 감사 로그", command=self._s1_open_audit_viewer).pack(side=LEFT, padx=2)
        ttk.Label(out_btn_row, textvariable=out_scan_status_var).pack(side=LEFT, padx=8)
        ttk.Label(out_frame, textvariable=unmatched_var, foreground=tc('danger')).pack(fill=X, padx=6, pady=(0, 6))

    def _sob_build_buttons(self, st, on_preview, on_execute, on_get_selected_lot, HAS_TTKBOOTSTRAP):  # v8.6.4 [SRP]
        """메인 버튼 및 키바인딩 생성."""
        from ..utils.constants import ttk, LEFT, RIGHT
        dialog = st["dialog"]
        btn_frame = st["btn_frame"]
        lot_text = st["lot_text"]

        btn_style = {"bootstyle": "info"} if HAS_TTKBOOTSTRAP else {}
        btn_style_success = {"bootstyle": "success"} if HAS_TTKBOOTSTRAP else {}
        btn_style_secondary = {"bootstyle": "secondary"} if HAS_TTKBOOTSTRAP else {}
        btn_style_outline = {"bootstyle": "outline"} if HAS_TTKBOOTSTRAP else {}

        _bp = ttk.Button(btn_frame, text="Preview", command=on_preview, **btn_style)
        _bp.pack(side=LEFT, padx=5)
        apply_tooltip(_bp, "입력한 LOT·수량·출고처로 출고 미리보기를 표시합니다. DB에는 반영되지 않습니다.")
        _be = ttk.Button(btn_frame, text="Execute", command=on_execute, **btn_style_success)
        _be.pack(side=LEFT, padx=5)
        apply_tooltip(_be, "미리보기한 내용으로 실제 출고를 실행합니다. 재고가 차감되고 출고 이력에 기록됩니다.")
        _bc = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, **btn_style_secondary)
        _bc.pack(side=RIGHT, padx=5)
        apply_tooltip(_bc, "출고 대화상자를 닫습니다. 실행하지 않은 출고는 반영되지 않습니다.")

        _badd = ttk.Button(btn_frame, text="Add Selected", command=on_get_selected_lot,
                           **btn_style_outline)
        _badd.pack(side=LEFT, padx=20)
        apply_tooltip(_badd, "LOT 리스트에서 선택한 LOT를 출고 목록에 추가합니다. 여러 LOT를 쉼표로 구분해 넣을 수 있습니다.")

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 700) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
        dialog.geometry(f"+{x}+{y}")

        # Key bindings
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def _sob_on_get_selected_lot(self, st):  # v8.6.4 [SRP]
        """Get selected LOT from inventory list."""
        from ..utils.constants import END
        lot_text = st["lot_text"]
        selected = self.tree_inventory.selection()
        if selected:
            values = self.tree_inventory.item(selected[0])['values']
            lot_no = values[0]
            current_text = lot_text.get("1.0", END).strip()
            if current_text:
                lot_text.insert(END, f"\n{lot_no}, ")
            else:
                lot_text.insert(END, f"{lot_no}, ")
            lot_text.focus_set()

    def _build_simple_outbound_ui(self):
        """v4.0.3: Simple Outbound UI 위젯 생성 (~80줄 추출)"""
        from ..utils.constants import tk, ttk, VERTICAL, BOTH, LEFT, RIGHT, X, Y, W

        dialog = create_themed_toplevel(self.root)
        dialog.title("Simple Outbound")
        dialog.transient(self.root)
        dialog.grab_set()
        setup_dialog_geometry_persistence(dialog, "simple_outbound_dialog", self.root, "medium")

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # Input area
        input_frame = ttk.LabelFrame(main_frame, text="Outbound Information")
        input_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(input_frame, text="Customer:").grid(row=0, column=0, sticky=W, pady=2)
        customer_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=customer_var, width=30).grid(row=0, column=1, sticky=W, pady=2)

        ttk.Label(input_frame, text="Sales Ref:").grid(row=0, column=2, sticky=W, padx=(20, 0), pady=2)
        sale_ref_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=sale_ref_var, width=20).grid(row=0, column=3, sticky=W, pady=2)

        ttk.Label(input_frame, text="Enter LOT number and quantity (one per line):",
                  font=('', 16)).grid(row=1, column=0, columnspan=4, sticky=W, pady=(10, 2))
        ttk.Label(input_frame, text="Format: LOT_NO, Qty(MT)  e.g.) 1234567890, 5.0",
                  foreground=tc('text_muted')).grid(row=2, column=0, columnspan=4, sticky=W)

        # LOT text
        lot_frame = ttk.Frame(main_frame)
        lot_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        lot_text = tk.Text(lot_frame, height=10, width=60)
        lot_sb = tk.Scrollbar(lot_frame, orient=VERTICAL, command=lot_text.yview)
        lot_text.configure(yscrollcommand=lot_sb.set)
        lot_text.pack(side=LEFT, fill=BOTH, expand=True)
        lot_sb.pack(side=RIGHT, fill=Y)
        try:
            from gui_app_modular.utils.tree_enhancements import TreeviewTotalFooter as _TTF
            _TTF(frm, tree, [], {}, {}).pack(fill='x')
        except Exception as e:
            logger.warning(f'[UI] outbound_handlers: {e}')
        # Preview tree
        preview_frame = ttk.LabelFrame(main_frame, text="Outbound Preview")
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        columns = ('lot_no', 'sub_lt', 'product', 'weight_kg', 'status', 'location')
        preview_tree = ttk.Treeview(preview_frame, columns=columns, show='headings',
                                     height=10, selectmode='extended')
        for col, text, w in [('lot_no', 'LOT No', 110), ('sub_lt', '톤백#', 55),
                              ('product', 'Product', 80), ('weight_kg', '중량(kg)', 90),
                              ('status', '상태', 80), ('location', '위치', 70)]:
            preview_tree.heading(col, text=text, anchor='center')
            anchor = 'e' if col == 'weight_kg' else 'center' if col in ('sub_lt', 'status') else 'w'
            preview_tree.column(col, width=w, anchor=anchor)
        pv_sb = tk.Scrollbar(preview_frame, orient=VERTICAL, command=preview_tree.yview)
        preview_tree.configure(yscrollcommand=pv_sb.set)
        preview_tree.pack(side=LEFT, fill=BOTH, expand=True)
        pv_sb.pack(side=RIGHT, fill=Y)

        ttk.Label(main_frame, text="💡 Preview 후 출고할 톤백을 선택하세요 (미선택 시 자동 배정)",
                  foreground=tc('text_muted'), font=('', 16)).pack(pady=(0, 5))
        summary_var = tk.StringVar(value="Click Preview to check outbound details")
        ttk.Label(main_frame, textvariable=summary_var, font=('', 13, 'bold')).pack(pady=5)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        return {
            'dialog': dialog, 'lot_text': lot_text, 'preview_tree': preview_tree,
            'summary_var': summary_var, 'customer_var': customer_var,
            'sale_ref_var': sale_ref_var, 'btn_frame': btn_frame,
        }
