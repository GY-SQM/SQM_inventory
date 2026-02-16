# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 심플 엑셀 출고
=====================================

v5.6.0: 최소 필드(lot_no + weight_kg)만으로 출고 처리

엑셀 양식:
  | lot_no | weight_kg | customer | sale_ref |
  |--------|-----------|----------|----------|
  | LOT001 | 2500      | ABC Corp | SR001    |

필수: lot_no, weight_kg (또는 qty_mt)
선택: customer, sale_ref
"""

import logging
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SimpleExcelOutboundMixin:
    """심플 엑셀 출고 Mixin"""

    def _on_simple_excel_outbound(self) -> None:
        """심플 엑셀 출고 — 파일 선택 → 미리보기 → 확정"""
        from utils.constants import tk, ttk, filedialog, BOTH, YES
        from ..utils.custom_messagebox import CustomMessageBox

        file_path = filedialog.askopenfilename(
            title="심플 출고 엑셀 선택",
            filetypes=[
                ("Excel", "*.xlsx *.xls"),
                ("CSV", "*.csv"),
                ("All", "*.*"),
            ]
        )
        if not file_path:
            return

        try:
            import pandas as pd
        except ImportError:
            CustomMessageBox.error(None, "오류", "pandas 라이브러리가 필요합니다.")
            return

        try:
            # 파일 읽기
            ext = Path(file_path).suffix.lower()
            if ext == '.csv':
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)

            # 컬럼명 정규화 (소문자, 공백→언더스코어)
            df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

            # 필수 컬럼 확인
            lot_col = None
            weight_col = None
            customer_col = None
            sale_ref_col = None

            for c in df.columns:
                if c in ('lot_no', 'lot', 'lotno', 'lot_number'):
                    lot_col = c
                elif c in ('weight_kg', 'weight', 'qty_kg', 'kg'):
                    weight_col = c
                elif c in ('qty_mt', 'mt', 'weight_mt'):
                    weight_col = c  # MT → 나중에 ×1000
                elif c in ('customer', 'sold_to', 'buyer'):
                    customer_col = c
                elif c in ('sale_ref', 'sales_ref', 'reference', 'ref'):
                    sale_ref_col = c

            if not lot_col:
                CustomMessageBox.error(None, "컬럼 오류",
                    "lot_no 컬럼을 찾을 수 없습니다.\n\n"
                    "필수 컬럼: lot_no (또는 lot, lotno)\n"
                    f"발견된 컬럼: {list(df.columns)}")
                return

            if not weight_col:
                CustomMessageBox.error(None, "컬럼 오류",
                    "weight_kg 컬럼을 찾을 수 없습니다.\n\n"
                    "필수 컬럼: weight_kg (또는 qty_mt, weight, kg)\n"
                    f"발견된 컬럼: {list(df.columns)}")
                return

            # 데이터 파싱
            is_mt = weight_col in ('qty_mt', 'mt', 'weight_mt')
            outbound_items = []

            for idx, row in df.iterrows():
                lot_no = str(row.get(lot_col, '')).strip()
                if not lot_no:
                    continue

                try:
                    weight = float(str(row.get(weight_col, 0)).replace(',', ''))
                    if is_mt:
                        weight = weight * 1000  # MT → KG
                except (ValueError, TypeError):
                    continue

                if weight <= 0:
                    continue

                customer = str(row.get(customer_col, '')).strip() if customer_col else ''
                sale_ref = str(row.get(sale_ref_col, '')).strip() if sale_ref_col else ''

                outbound_items.append({
                    'lot_no': lot_no,
                    'weight_kg': weight,
                    'customer': customer,
                    'sale_ref': sale_ref,
                })

            if not outbound_items:
                CustomMessageBox.warning(None, "데이터 없음", "유효한 출고 데이터가 없습니다.")
                return

            # 미리보기 다이얼로그
            self._show_simple_outbound_preview(outbound_items)

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"심플 엑셀 출고 오류: {e}", exc_info=True)
            CustomMessageBox.error(None, "오류", f"파일 처리 중 오류:\n{e}")

    def _show_simple_outbound_preview(self, items: List[Dict]) -> None:
        """심플 출고 미리보기"""
        from utils.constants import tk, ttk, BOTH, YES
        from ..utils.custom_messagebox import CustomMessageBox

        dialog = tk.Toplevel(self.root)
        dialog.title("📤 심플 엑셀 출고 — 미리보기")
        dialog.geometry("700x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # 상단 요약
        summary = tk.Frame(dialog, padx=10, pady=8)
        summary.pack(fill='x')
        tk.Label(summary, text=f"총 {len(items)}건 출고 예정",
                 font=('', 13, 'bold')).pack(side='left')

        total_kg = sum(i['weight_kg'] for i in items)
        tk.Label(summary, text=f"총 {total_kg:,.0f} kg ({total_kg/1000:,.2f} MT)",
                 font=('', 12)).pack(side='right')

        # Treeview
        cols = ('lot_no', 'weight_kg', 'weight_mt', 'customer', 'sale_ref', 'status')
        tree = ttk.Treeview(dialog, columns=cols, show='headings', height=15)

        headers = {
            'lot_no': ('LOT NO', 120),
            'weight_kg': ('KG', 90),
            'weight_mt': ('MT', 80),
            'customer': ('Customer', 150),
            'sale_ref': ('Sale Ref', 100),
            'status': ('Status', 100),
        }
        for c, (label, w) in headers.items():
            tree.heading(c, text=label)
            tree.column(c, width=w, anchor='center')

        # 검증: 각 LOT 재고 확인
        for item in items:
            lot_no = item['lot_no']
            weight_kg = item['weight_kg']

            # DB에서 LOT 확인
            lot_data = self.engine.db.fetchone(
                "SELECT current_weight, status FROM inventory WHERE lot_no = ?",
                (lot_no,))

            if not lot_data:
                status = "❌ LOT 없음"
            elif lot_data['status'] == 'DEPLETED':
                status = "❌ 소진됨"
            elif float(lot_data['current_weight'] or 0) < weight_kg:
                avail = float(lot_data['current_weight'] or 0)
                status = f"⚠️ 부족 ({avail:,.0f}kg)"
            else:
                status = "✅ OK"

            tree.insert('', 'end', values=(
                lot_no,
                f"{weight_kg:,.0f}",
                f"{weight_kg/1000:,.3f}",
                item.get('customer', ''),
                item.get('sale_ref', ''),
                status
            ))

        tree.pack(fill=BOTH, expand=YES, padx=10, pady=5)

        # 버튼
        btn_frame = tk.Frame(dialog, padx=10, pady=10)
        btn_frame.pack(fill='x')

        def execute():
            # 에러 있는 항목 확인
            has_error = any('❌' in str(tree.item(iid, 'values')[5]) for iid in tree.get_children())
            if has_error:
                CustomMessageBox.warning(dialog, "확인",
                    "❌ 오류가 있는 항목이 포함되어 있습니다.\n오류 항목은 건너뛰고 진행할까요?")

            success = 0
            errors = []

            for item in items:
                lot_no = item['lot_no']
                weight_kg = item['weight_kg']
                customer = item.get('customer', '')
                sale_ref = item.get('sale_ref', '')

                try:
                    result = self.engine.process_outbound({
                        'lot_no': lot_no,
                        'weight_kg': weight_kg,
                        'customer': customer,
                        'sale_ref': sale_ref,
                    })
                    if result.get('success'):
                        success += 1
                    else:
                        errors.append(f"{lot_no}: {result.get('message', '실패')}")
                except (ValueError, TypeError, KeyError) as e:
                    errors.append(f"{lot_no}: {e}")

            dialog.destroy()

            msg = f"✅ 출고 완료: {success}/{len(items)}건"
            if errors:
                msg += f"\n\n❌ 실패 {len(errors)}건:\n" + '\n'.join(errors[:5])
            CustomMessageBox.info(self.root, "출고 결과", msg)

            # 새로고침
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()

        ttk.Button(btn_frame, text="✅ 출고 실행", command=execute).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="❌ 취소", command=dialog.destroy).pack(side='right', padx=5)

    def _download_simple_outbound_template(self) -> None:
        """심플 출고 엑셀 양식 다운로드"""
        from utils.constants import filedialog
        from ..utils.custom_messagebox import CustomMessageBox

        try:
            import pandas as pd
        except ImportError:
            CustomMessageBox.error(None, "오류", "pandas 라이브러리가 필요합니다.")
            return

        save_path = filedialog.asksaveasfilename(
            title="심플 출고 양식 저장",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"simple_outbound_template_{date.today().strftime('%Y%m%d')}.xlsx"
        )
        if not save_path:
            return

        df = pd.DataFrame({
            'lot_no': ['1125081447', '1125081448'],
            'weight_kg': [2500, 3000],
            'customer': ['ABC Corp', 'XYZ Inc'],
            'sale_ref': ['SR-001', 'SR-002'],
        })

        df.to_excel(save_path, index=False, sheet_name='Outbound')
        CustomMessageBox.info(None, "완료", f"양식 저장 완료:\n{save_path}")
