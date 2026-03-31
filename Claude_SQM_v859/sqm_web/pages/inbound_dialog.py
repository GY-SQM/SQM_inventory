# -*- coding: utf-8 -*-
"""
SQM Web — Inbound Dialog (입고 다이얼로그)
============================================
Upload-based inbound processing dialog for NiceGUI.
"""

import logging
from nicegui import ui

from sqm_web.components.theme import (
    BG_CARD, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT,
    COLOR_SUCCESS, COLOR_DANGER, BORDER_RADIUS
)

logger = logging.getLogger(__name__)


def create_inbound_dialog():
    """Create and return a modal inbound dialog.

    Usage:
        dialog = create_inbound_dialog()
        dialog.open()
    """

    with ui.dialog().props('persistent maximized=false') as dialog, \
         ui.card().style(
             f'min-width:680px;max-width:900px;padding:24px;'
             f'background:{BG_CARD};border:1px solid {BORDER};border-radius:16px;'
         ):

        # ── Header ──
        with ui.row().classes('w-full items-center justify-between').style('margin-bottom:20px'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('add_circle').style(f'font-size:24px;color:{ACCENT}')
                ui.label('신규 입고').style(
                    f'font-size:18px;font-weight:700;color:{TEXT_PRIMARY}'
                )
            ui.button(icon='close', on_click=dialog.close).props(
                'flat round dense'
            ).style(f'color:{TEXT_MUTED}')

        ui.separator().style(f'background:{BORDER}')

        # ── Form Section ──
        with ui.column().classes('w-full gap-4').style('margin-top:16px'):
            # Row 1: LOT / SAP
            with ui.row().classes('w-full gap-4'):
                lot_input = ui.input('LOT No.', placeholder='예: 1234567890').props(
                    'outlined dense'
                ).classes('flex-1').style(f'color:{TEXT_PRIMARY}')
                sap_input = ui.input('SAP No.', placeholder='선택사항').props(
                    'outlined dense'
                ).classes('flex-1')

            # Row 2: B/L / Product
            with ui.row().classes('w-full gap-4'):
                bl_input = ui.input('B/L No.', placeholder='MSKU1234567').props(
                    'outlined dense'
                ).classes('flex-1')
                product_select = ui.select(
                    ['MIC9000', 'MIC9000P', 'MIC9200', 'MIC9300', 'SQM Li2CO3'],
                    value='MIC9000',
                    label='제품'
                ).props('outlined dense').classes('flex-1')

            # Row 3: Container / Weight
            with ui.row().classes('w-full gap-4'):
                container_input = ui.input('컨테이너 No.', placeholder='MSCU1234567').props(
                    'outlined dense'
                ).classes('flex-1')
                weight_input = ui.number('총 중량 (kg)', value=0, min=0).props(
                    'outlined dense'
                ).classes('flex-1')

            # Row 4: Tonbag count / Unit weight
            with ui.row().classes('w-full gap-4'):
                tonbag_count = ui.number('톤백 수량', value=0, min=0).props(
                    'outlined dense'
                ).classes('flex-1')
                unit_weight = ui.select(
                    [500, 1000],
                    value=1000,
                    label='단위 중량 (kg)'
                ).props('outlined dense').classes('flex-1')

            # Row 5: Arrival date / Vessel
            with ui.row().classes('w-full gap-4'):
                arrival_input = ui.input('입항일', placeholder='2026-03-21').props(
                    'outlined dense'
                ).classes('flex-1')
                vessel_input = ui.input('선박명', placeholder='선택사항').props(
                    'outlined dense'
                ).classes('flex-1')

        ui.separator().style(f'background:{BORDER};margin-top:16px')

        # ── File Upload Section ──
        with ui.column().classes('w-full gap-3').style('margin-top:16px'):
            ui.label('문서 업로드 (선택)').style(
                f'font-size:12px;font-weight:600;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.05em'
            )
            with ui.row().classes('w-full gap-3 items-center'):
                upload = ui.upload(
                    label='PDF 파일 선택 (B/L, Invoice, Packing List, COA)',
                    multiple=True,
                    auto_upload=False,
                ).props('accept=".pdf,.xlsx,.xls"').classes('flex-1').style(
                    f'border:1px dashed {BORDER};border-radius:8px;'
                )

        # ── Status messages ──
        status_label = ui.label('').style(f'font-size:13px;color:{TEXT_MUTED};margin-top:8px')

        # ── Progress bar ──
        progress = ui.linear_progress(value=0, show_value=False).style(
            'margin-top:8px;display:none'
        )

        ui.separator().style(f'background:{BORDER};margin-top:16px')

        # ── Action Buttons ──
        with ui.row().classes('w-full justify-end gap-3').style('margin-top:16px'):
            ui.button('취소', on_click=dialog.close).props(
                'outline'
            ).style(f'color:{TEXT_MUTED};border-color:{BORDER};padding:8px 16px')

            async def _on_submit():
                lot = lot_input.value
                if not lot or not lot.strip():
                    ui.notify('LOT No.를 입력해주세요.', type='warning')
                    return

                bl = bl_input.value or ''
                product = product_select.value or 'MIC9000'
                container = container_input.value or ''
                total_weight = float(weight_input.value or 0)
                tb_count = int(tonbag_count.value or 0)

                if total_weight <= 0:
                    ui.notify('총 중량을 입력해주세요.', type='warning')
                    return
                if tb_count <= 0:
                    ui.notify('톤백 수량을 입력해주세요.', type='warning')
                    return

                status_label.text = '입고 처리 중...'
                status_label.style(f'color:{ACCENT}')
                progress.style('display:block')
                progress.value = 0.3

                try:
                    from sqm_web.bridge import engine_bridge as bridge
                    engine = bridge.get_engine()

                    packing_data = {
                        'lot_no': lot.strip(),
                        'sap_no': sap_input.value or '',
                        'bl_no': bl.strip(),
                        'product': product,
                        'container_no': container.strip(),
                        'net_weight': total_weight,
                        'gross_weight': total_weight,
                        'mxbg_pallet': tb_count,
                        'arrival_date': arrival_input.value or '',
                        'vessel': vessel_input.value or '',
                        'unit_weight': int(unit_weight.value or 1000),
                    }

                    progress.value = 0.6

                    result = await bridge.async_call(
                        engine.process_inbound, packing_data
                    )

                    progress.value = 1.0

                    if result and result.get('success'):
                        status_label.text = f"입고 완료: {lot.strip()}"
                        status_label.style(f'color:{COLOR_SUCCESS}')
                        ui.notify(
                            f'입고 완료: {lot.strip()} ({tb_count}개 톤백, {total_weight:.0f}kg)',
                            type='positive'
                        )
                    else:
                        err = result.get('error', '알 수 없는 오류') if result else '응답 없음'
                        status_label.text = f"입고 실패: {err}"
                        status_label.style(f'color:{COLOR_DANGER}')
                        ui.notify(f'입고 실패: {err}', type='negative')

                except Exception as ex:
                    status_label.text = f"오류: {ex}"
                    status_label.style(f'color:{COLOR_DANGER}')
                    ui.notify(f'입고 처리 오류: {ex}', type='negative')
                    logger.error(f"[Inbound] submit error: {ex}")

            ui.button('입고 처리', icon='add', on_click=_on_submit).props(
                'unelevated'
            ).style(
                f'background:{ACCENT};color:white;padding:8px 20px;font-weight:600'
            )

    return dialog
