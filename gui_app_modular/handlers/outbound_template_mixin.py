# -*- coding: utf-8 -*-
"""
SQM v4.0.1 — 출고 템플릿/Allocation Mixin
===========================================

outbound_handlers.py에서 분리:
- 출고 양식 다운로드
- Allocation Table 생성 (샘플)
- Virtual Allocation 생성
"""
import logging
from ..utils.custom_messagebox import CustomMessageBox
from datetime import datetime

logger = logging.getLogger(__name__)


class OutboundTemplateMixin:
    """출고 템플릿 및 Allocation Table Mixin"""

    def _download_outbound_template(self) -> None:
        """v3.9.2: 출고 Allocation Table 샘플 Excel 템플릿 생성
        
        업로드된 양식 기준:
        Row 1: 타이틀 (Allocation - 제품명 수량)
        Row 2: 합계 행
        Row 3: 헤더 (Product, SAP NO, Date in stock, QTY(MT), Lot No, WH, Customs, Export, SOLD TO, SALE REF, GW)
        Row 4~: 데이터 (일반 + 샘플)
        """
        from ..utils.constants import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="출고 Allocation Table 샘플 저장",
            defaultextension=".xlsx",
            initialfile="출고_Allocation_Table_샘플.xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        
        if not file_path:
            return
        
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Allocation Table"
            
            # === 스타일 정의 ===
            title_font = Font(bold=True, size=14, color="2C3E50")
            header_font = Font(bold=True, color="FFFFFF", size=10)
            data_font = Font(size=10)
            sample_font = Font(size=10, color="0066CC")  # 샘플은 파란색
            header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
            data_fill = PatternFill(start_color="F7F9FC", end_color="F7F9FC", fill_type="solid")
            sample_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
            return_fill = PatternFill(start_color="FDEBD0", end_color="FDEBD0", fill_type="solid")
            split_fill = PatternFill(start_color="E8F8F5", end_color="E8F8F5", fill_type="solid")
            summary_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
            thin_border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            center = Alignment(horizontal='center', vertical='center')
            right_align = Alignment(horizontal='right', vertical='center')
            
            # === Row 1: 타이틀 ===
            ws.merge_cells('A1:K1')
            ws['A1'] = "Allocation - LBM AP 450MT"
            ws['A1'].font = title_font
            ws.row_dimensions[1].height = 30
            
            # === Row 2: 합계 (나중에 채움) ===
            ws.row_dimensions[2].height = 20
            
            # === Row 3: 헤더 ===
            headers = [
                ('Product',       16),
                ('SAP NO',        14),
                ('Date in stock', 14),
                ('QTY (MT)',      12),
                ('Lot No',        14),
                ('WH',             8),
                ('Customs',       12),
                ('Export',        12),
                ('SOLD TO',       28),
                ('SALE REF',      12),
                ('GW',            12),
            ]
            
            for col, (text, width) in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col, value=text)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center
                cell.border = thin_border
                ws.column_dimensions[get_column_letter(col)].width = width
            
            # === Row 4~: 샘플 데이터 ===
            # 업로드한 양식 기반: 일반 톤백 + 샘플 톤백 + 반송/분할반송
            sample_lots = [
                '1125072340', '1125072341', '1125072342', '1125072343',
                '1125072405', '1125072406', '1125072407', '1125072408',
                '1125072409', '1125072410', '1125072411', '1125072412',
            ]
            
            row_num = 4
            
            # --- 반송 (일반 톤백) ---
            for lot in sample_lots[:12]:
                vals = ['MIC9000', '2200032833', '2025-09-18', 5.0, lot,
                        'GY', 'Uncleared', '반송',
                        'LBM AP - Q4 2025 2nd 450MT', '2929', 5.13]
                fill = return_fill
                for col, val in enumerate(vals, 1):
                    cell = ws.cell(row=row_num, column=col, value=val)
                    cell.font = data_font
                    cell.fill = fill
                    cell.border = thin_border
                    if col in (4, 11):  # QTY, GW
                        cell.number_format = '#,##0.000'
                        cell.alignment = right_align
                    else:
                        cell.alignment = center
                row_num += 1
            
            # --- 반송 (샘플 톤백) ---
            for lot in sample_lots[:12]:
                vals = ['MIC9000 Sample', '2200032833', '2025-09-18', 0.001, lot,
                        'GY', 'Uncleared', '반송',
                        'LBM AP - Q4 2025 2nd 450MT', '2929', 0.00125]
                for col, val in enumerate(vals, 1):
                    cell = ws.cell(row=row_num, column=col, value=val)
                    cell.font = sample_font
                    cell.fill = sample_fill
                    cell.border = thin_border
                    if col in (4, 11):
                        cell.number_format = '#,##0.000'
                        cell.alignment = right_align
                    else:
                        cell.alignment = center
                row_num += 1
            
            # --- 분할/반송 (일반 톤백) ---
            split_lots = [
                '1125081215', '1125081222', '1125081223', '1125081224',
                '1125081314', '1125081315',
            ]
            for lot in split_lots:
                vals = ['MIC9000', '2200032833', '2025-10-05', 5.0, lot,
                        'GY', 'Cleared', '분할/반송',
                        'LBM AP - Q4 2025 2nd 450MT', '2929', 5.13]
                for col, val in enumerate(vals, 1):
                    cell = ws.cell(row=row_num, column=col, value=val)
                    cell.font = data_font
                    cell.fill = split_fill
                    cell.border = thin_border
                    if col in (4, 11):
                        cell.number_format = '#,##0.000'
                        cell.alignment = right_align
                    else:
                        cell.alignment = center
                row_num += 1
            
            # --- 분할/반송 (샘플 톤백) ---
            for lot in split_lots:
                vals = ['MIC9000 Sample', '2200032833', '2025-10-05', 0.001, lot,
                        'GY', 'Cleared', '분할/반송',
                        'LBM AP - Q4 2025 2nd 450MT', '2929', 0.00125]
                for col, val in enumerate(vals, 1):
                    cell = ws.cell(row=row_num, column=col, value=val)
                    cell.font = sample_font
                    cell.fill = sample_fill
                    cell.border = thin_border
                    if col in (4, 11):
                        cell.number_format = '#,##0.000'
                        cell.alignment = right_align
                    else:
                        cell.alignment = center
                row_num += 1
            
            # === Row 2: 합계 채우기 ===
            last_data = row_num - 1
            ws.cell(row=2, column=3, value="합계").font = Font(bold=True, size=10)
            ws.cell(row=2, column=4, value=f"=SUM(D4:D{last_data})").font = Font(bold=True)
            ws['D2'].number_format = '#,##0.000'
            ws.cell(row=2, column=10, value="합계 GW").font = Font(bold=True, size=10)
            ws.cell(row=2, column=11, value=f"=SUM(K4:K{last_data})").font = Font(bold=True)
            ws['K2'].number_format = '#,##0.000'
            
            # === 오른쪽 요약 테이블 (N~S열) ===
            summary_start_col = 14  # N열
            sum_headers = ['Export', 'SAP NO', 'Product', 'Lot No', '합계 : QTY (MT)', '합계 : GW']
            for i, h in enumerate(sum_headers):
                cell = ws.cell(row=3, column=summary_start_col + i, value=h)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center
                cell.border = thin_border
                ws.column_dimensions[get_column_letter(summary_start_col + i)].width = 16
            
            # 요약 데이터
            summary_data = [
                ['반송', '2200032833', '', '', 90.012, 92.363],
                ['반송 요약', '', '', '', 90.012, 92.363],
                ['분할/반송', '2200032833', '', '', 30.006, 30.780],
                ['분할/반송 요약', '', '', '', 30.006, 30.780],
                ['총합계', '', '', '', 120.018, 123.143],
            ]
            for r, data in enumerate(summary_data, 4):
                for c, val in enumerate(data):
                    cell = ws.cell(row=r, column=summary_start_col + c, value=val)
                    cell.border = thin_border
                    cell.alignment = center
                    if c >= 4:
                        cell.number_format = '#,##0.000'
                        cell.alignment = right_align
                    if '요약' in str(data[0]) or '총합계' in str(data[0]):
                        cell.font = Font(bold=True)
                        cell.fill = summary_fill
            
            # === 작성 안내 시트 ===
            ws2 = wb.create_sheet("📋 작성 안내")
            guides = [
                ("📋 출고 Allocation Table 작성 안내", ""),
                ("", ""),
                ("구분", "설명"),
                ("Row 1", "타이틀: 'Allocation - [제품] [수량]'"),
                ("Row 2", "합계 행 (자동 계산)"),
                ("Row 3", "헤더: Product | SAP NO | Date in stock | QTY(MT) | Lot No | WH | Customs | Export | SOLD TO | SALE REF | GW"),
                ("Row 4~", "데이터 행 (일반 + 샘플)"),
                ("", ""),
                ("★ Export 유형", ""),
                ("반송", "전량 반송 (입고분 그대로 반출)"),
                ("분할/반송", "일부 반송 (분할 후 일부만 반출)"),
                ("출고", "일반 출고 (판매)"),
                ("", ""),
                ("★ 샘플 톤백", ""),
                ("Product", "원래 제품명 + ' Sample' (예: MIC9000 Sample)"),
                ("QTY (MT)", "0.001 (= 1kg)"),
                ("GW", "0.00125"),
                ("", ""),
                ("★ 필수 항목", "Product, QTY (MT), Lot No"),
                ("★ 색상 규칙", "연한 주황=반송, 연한 초록=분할/반송, 연한 파랑=샘플"),
            ]
            for r, (a, b) in enumerate(guides, 1):
                ws2.cell(row=r, column=1, value=a)
                ws2.cell(row=r, column=2, value=b)
                if r == 1:
                    ws2.cell(row=1, column=1).font = Font(bold=True, size=13)
                elif r == 3:
                    ws2.cell(row=r, column=1).font = Font(bold=True)
                    ws2.cell(row=r, column=2).font = Font(bold=True)
            ws2.column_dimensions['A'].width = 25
            ws2.column_dimensions['B'].width = 60
            
            try:
                from gui_app_modular.utils.report_footer import add_gy_logistics_footer
                add_gy_logistics_footer(ws)
            except (ImportError, ModuleNotFoundError) as _e:
                logger.debug(f'Suppressed: {_e}')
            wb.save(file_path)
            
            self._log(f"✅ 출고 Allocation Table 샘플 저장: {file_path}")
            CustomMessageBox.showinfo(self.root, "완료",
                f"출고 Allocation Table 샘플이 저장되었습니다.\n\n"
                f"파일: {file_path}\n\n"
                "★ 3행 헤더에 'Product', 'QTY (MT)', 'Lot No'가 필수\n"
                "★ 샘플은 Product에 'Sample' 추가, QTY=0.001\n"
                "★ Export: 반송/분할반송/출고 구분")
                
        except ImportError:
            CustomMessageBox.showerror(self.root, "오류", "openpyxl 패키지가 필요합니다.\npip install openpyxl")
        except (RuntimeError, ValueError) as e:
            logger.error(f"Allocation Table 템플릿 생성 오류: {e}")
            CustomMessageBox.show_detailed_error(self.root, "오류", "Allocation Table 생성 실패", exception=e)

    def _generate_virtual_allocation(self) -> None:
        """v3.9.3: 가상 출고 Allocation Table 생성
        
        현재 DB 재고 기준:
        - 60% → 출고 (분할/반송, 입고일~2026-02-08 사이 랜덤 출고)
        - 20% → 반품 (반송)
        - 20% → 재고 유지
        - 일반 + 샘플 톤백 모두 포함
        """
        from ..utils.constants import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="가상 출고 Allocation Table 저장",
            defaultextension=".xlsx",
            initialfile="출고_Allocation_Table_가상.xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if not file_path:
            return
        
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            import random
            from datetime import datetime, timedelta
            
            # DB에서 재고 로드
            all_lots = self.engine.get_inventory()
            if not all_lots:
                CustomMessageBox.showwarning(self.root, "데이터 없음",
                    "DB에 재고 데이터가 없습니다.\n먼저 입고를 진행해주세요.")
                return
            
            random.seed(42)
            random.shuffle(all_lots)
            
            total = len(all_lots)
            n_out = int(total * 0.6)
            n_ret = int(total * 0.2)
            
            out_lots = sorted(all_lots[:n_out], key=lambda x: x.get('lot_no', ''))
            ret_lots = sorted(all_lots[n_out:n_out+n_ret], key=lambda x: x.get('lot_no', ''))
            stk_lots = sorted(all_lots[n_out+n_ret:], key=lambda x: x.get('lot_no', ''))
            
            # 스타일
            hdr_font = Font(bold=True, color="FFFFFF", size=10)
            hdr_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
            out_fill = PatternFill(start_color="E8F8F5", end_color="E8F8F5", fill_type="solid")
            ret_fill = PatternFill(start_color="FDEBD0", end_color="FDEBD0", fill_type="solid")
            smp_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
            stk_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
            sum_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
            border = Border(left=Side(style='thin'), right=Side(style='thin'),
                          top=Side(style='thin'), bottom=Side(style='thin'))
            ctr = Alignment(horizontal='center', vertical='center')
            rgt = Alignment(horizontal='right', vertical='center')
            
            sold_tos = ['LBM AP - Q4 2025', 'PT ABC - Q1 2026', 'Samsung SDI', 'LG Energy', 'CATL']
            
            def rand_date(start_str):
                try:
                    s = datetime.strptime(str(start_str)[:10], '%Y-%m-%d')
                except (ValueError, TypeError, KeyError):
                    s = datetime(2025, 9, 1)
                e = datetime(2026, 2, 8)
                d = max((e - s).days, 7)
                return (s + timedelta(days=random.randint(7, d))).strftime('%Y-%m-%d')
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Allocation Table"
            
            # 타이틀
            ws.merge_cells('A1:K1')
            ws['A1'] = f"Allocation - {total} LOTs (가상 60/20/20)"
            ws['A1'].font = Font(bold=True, size=14)
            
            # 헤더
            headers = ['Product','SAP NO','Date in stock','QTY (MT)','Lot No',
                       'WH','Customs','Export','SOLD TO','SALE REF','GW']
            widths = [16,14,14,12,14,8,12,12,28,14,12]
            for i, (h, w) in enumerate(zip(headers, widths), 1):
                c = ws.cell(row=3, column=i, value=h)
                c.font = hdr_font; c.fill = hdr_fill; c.alignment = ctr; c.border = border
                ws.column_dimensions[get_column_letter(i)].width = w
            
            row = 4
            out_qty = out_gw = ret_qty = ret_gw = 0
            
            def write_row(r, vals, fill, is_sample=False):
                for i, v in enumerate(vals, 1):
                    c = ws.cell(row=r, column=i, value=v)
                    c.font = Font(size=10, color="0066CC") if is_sample else Font(size=10)
                    c.fill = smp_fill if is_sample else fill
                    c.border = border
                    c.alignment = rgt if i in (4, 11) else ctr
                    if i in (4, 11):
                        c.number_format = '#,##0.00000' if is_sample else '#,##0.000'
            
            # 출고 (60%)
            for lot in out_lots:
                qty_mt = (lot.get('net_weight', 5000) or 5000) / 1000
                gw_mt = qty_mt * 1.026
                write_row(row, [lot.get('product',''), lot.get('sap_no',''),
                    lot.get('arrival_date',''), qty_mt, lot.get('lot_no',''),
                    lot.get('warehouse','GY'), lot.get('customs','Cleared'), '분할/반송',
                    random.choice(sold_tos), str(2900+random.randint(1,99)), gw_mt], out_fill)
                row += 1; out_qty += qty_mt; out_gw += gw_mt
            
            for lot in out_lots:
                write_row(row, [f"{lot.get('product','')}_sample", lot.get('sap_no',''),
                    lot.get('arrival_date',''), 0.001, lot.get('lot_no',''),
                    lot.get('warehouse','GY'), lot.get('customs','Cleared'), '분할/반송',
                    random.choice(sold_tos), '', 0.00125], out_fill, is_sample=True)
                row += 1; out_qty += 0.001; out_gw += 0.00125
            
            # 반품 (20%)
            for lot in ret_lots:
                qty_mt = (lot.get('net_weight', 5000) or 5000) / 1000
                gw_mt = qty_mt * 1.026
                write_row(row, [lot.get('product',''), lot.get('sap_no',''),
                    lot.get('arrival_date',''), qty_mt, lot.get('lot_no',''),
                    lot.get('warehouse','GY'), 'Uncleared', '반송',
                    'RETURN - 반품', '', gw_mt], ret_fill)
                row += 1; ret_qty += qty_mt; ret_gw += gw_mt
            
            for lot in ret_lots:
                write_row(row, [f"{lot.get('product','')}_sample", lot.get('sap_no',''),
                    lot.get('arrival_date',''), 0.001, lot.get('lot_no',''),
                    lot.get('warehouse','GY'), 'Uncleared', '반송',
                    'RETURN - 반품', '', 0.00125], ret_fill, is_sample=True)
                row += 1; ret_qty += 0.001; ret_gw += 0.00125
            
            last = row - 1
            ws.cell(row=2, column=3, value="합계 QTY").font = Font(bold=True)
            ws.cell(row=2, column=4, value=f"=SUM(D4:D{last})").font = Font(bold=True)
            ws['D2'].number_format = '#,##0.000'
            ws.cell(row=2, column=10, value="합계 GW").font = Font(bold=True)
            ws.cell(row=2, column=11, value=f"=SUM(K4:K{last})").font = Font(bold=True)
            ws['K2'].number_format = '#,##0.000'
            
            # 요약
            sc = 14
            for i, h in enumerate(['Export','LOTs','합계 QTY(MT)','합계 GW']):
                c = ws.cell(row=3, column=sc+i, value=h)
                c.font = hdr_font; c.fill = hdr_fill; c.alignment = ctr; c.border = border
                ws.column_dimensions[get_column_letter(sc+i)].width = 16
            
            stk_qty = sum((l.get('net_weight', 5000) or 5000)/1000 for l in stk_lots)
            for r, d in enumerate([
                ['분할/반송 (출고)', f'{len(out_lots)}', out_qty, out_gw],
                ['반송 (반품)', f'{len(ret_lots)}', ret_qty, ret_gw],
                ['재고 유지', f'{len(stk_lots)}', stk_qty, stk_qty*1.026],
                ['총합계', f'{total}', out_qty+ret_qty+stk_qty, out_gw+ret_gw+stk_qty*1.026],
            ], 4):
                for c, v in enumerate(d):
                    cell = ws.cell(row=r, column=sc+c, value=v)
                    cell.border = border; cell.alignment = rgt if c >= 2 else ctr
                    if c >= 2: cell.number_format = '#,##0.000'
                    if '총합계' in str(d[0]):
                        cell.font = Font(bold=True); cell.fill = sum_fill
            
            # 재고 유지 시트
            ws2 = wb.create_sheet("재고 유지 (20%)")
            ws2.cell(row=1, column=1, value="재고 유지 LOT (미출고)").font = Font(bold=True, size=13)
            for i, h in enumerate(['No.','Product','SAP NO','Lot No','QTY(MT)','WH','STATUS'], 1):
                c = ws2.cell(row=3, column=i, value=h)
                c.font = hdr_font; c.fill = hdr_fill; c.alignment = ctr; c.border = border
                ws2.column_dimensions[get_column_letter(i)].width = 16
            for idx, lot in enumerate(stk_lots, 1):
                qty_mt = (lot.get('net_weight', 5000) or 5000)/1000
                for j, v in enumerate([idx, lot.get('product',''), lot.get('sap_no',''),
                    lot.get('lot_no',''), qty_mt, lot.get('warehouse','GY'), 'AVAILABLE'], 1):
                    c = ws2.cell(row=3+idx, column=j, value=v)
                    c.fill = stk_fill; c.border = border; c.alignment = ctr
                    if j == 5: c.number_format = '#,##0.000'
            
            wb.save(file_path)
            self._log(f"✅ 가상 Allocation Table 저장: {file_path}")
            self._log(f"  출고: {len(out_lots)} LOTs | 반품: {len(ret_lots)} LOTs | 재고: {len(stk_lots)} LOTs")
            CustomMessageBox.showinfo(self.root, "완료",
                f"가상 Allocation Table 생성 완료\n\n"
                f"출고 (60%): {len(out_lots)} LOTs\n"
                f"반품 (20%): {len(ret_lots)} LOTs\n"
                f"재고 유지 (20%): {len(stk_lots)} LOTs\n\n"
                f"파일: {file_path}")
            
        except ImportError:
            CustomMessageBox.showerror(self.root, "오류", "openpyxl 필요: pip install openpyxl")
        except (RuntimeError, ValueError) as e:
            logger.error(f"가상 Allocation 생성 오류: {e}", exc_info=True)
            CustomMessageBox.show_detailed_error(self.root, "오류", "생성 실패", exception=e)
