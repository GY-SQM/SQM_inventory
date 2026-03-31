# -*- coding: utf-8 -*-
"""
SQM Web — Return Page (반품) — Iteration 3
=============================================
"""

import logging
from nicegui import ui

from sqm_web.bridge import engine_bridge as bridge
from sqm_web.components.kpi_cards import inventory_kpi_row
from sqm_web.components.theme import TEXT_MUTED, BG_CARD, BORDER

logger = logging.getLogger(__name__)

COLUMNS = [
    {'name': 'lot_no', 'label': 'LOT No.', 'field': 'lot_no', 'sortable': True, 'align': 'left'},
    {'name': 'sub_lt', 'label': 'Sub-LT', 'field': 'sub_lt', 'sortable': True, 'align': 'center'},
    {'name': 'reason', 'label': '반품사유', 'field': 'reason', 'sortable': True, 'align': 'left'},
    {'name': 'original_customer', 'label': '원래 고객', 'field': 'original_customer', 'sortable': True, 'align': 'left'},
    {'name': 'weight_kg', 'label': '중량(kg)', 'field': 'weight_kg', 'sortable': True, 'align': 'right'},
    {'name': 'status', 'label': '상태', 'field': 'status', 'sortable': True, 'align': 'center'},
    {'name': 'created_at', 'label': '반품일', 'field': 'created_at', 'sortable': True, 'align': 'center'},
]


async def return_page():
    """Render the return page — Iteration 3."""
    try:
        summary = await bridge.get_inventory_summary()
        returns = await bridge.get_return_history()
    except Exception as e:
        ui.notify(f'데이터 로드 실패: {e}', type='negative')
        summary = {}
        returns = []

    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        with ui.row().classes('items-center gap-3'):
            ui.label('반품 관리').classes('sqm-section-title').style('margin-bottom:0')
            ui.label(f'{len(returns)}건').style(
                f'font-size:12px;color:{TEXT_MUTED};background:{BG_CARD};'
                f'padding:2px 10px;border-radius:12px;border:1px solid {BORDER}'
            )

        async def _refresh():
            nonlocal returns, summary
            summary = await bridge.get_inventory_summary()
            returns = await bridge.get_return_history()
            _update()
            ui.notify('새로고침 완료', type='positive', position='bottom-right', timeout=1500)

        ui.button('', icon='refresh', on_click=_refresh).props('flat dense round').tooltip('새로고침')

    inventory_kpi_row(summary)

    with ui.row().classes('sqm-filter-bar w-full items-center').style('margin-top:16px'):
        search_input = ui.input(placeholder='LOT / 고객사 / 사유 검색...').props(
            'outlined dense clearable'
        ).style('max-width:360px;flex:1')

    def _make_rows(raw, kw=''):
        result = []
        for rec in raw:
            r = dict(rec)
            if kw:
                searchable = f"{r.get('lot_no','')} {r.get('original_customer','')} {r.get('reason','')}".lower()
                if kw.lower() not in searchable:
                    continue
            r['created_at'] = str(r.get('created_at', '-'))[:16]
            r['original_customer'] = r.get('original_customer', '-') or '-'
            r['reason'] = r.get('reason', '-') or '-'
            r['weight_kg'] = f"{float(r.get('weight_kg', 0)):.0f}" if r.get('weight_kg') else '-'
            r['status'] = r.get('status', '-') or '-'
            result.append(r)
        return result

    table = ui.table(
        columns=COLUMNS, rows=_make_rows(returns), row_key='id',
        pagination={'rowsPerPage': 25, 'sortBy': 'created_at', 'descending': True},
    ).classes('w-full')

    table.add_slot('no-data',
        '<div class="sqm-empty"><div class="sqm-empty-icon">↩️</div>'
        '<div style="font-size:14px">반품 이력이 없습니다</div>'
        '<div style="font-size:12px;color:#6b7280">반품 처리된 항목이 여기에 표시됩니다</div></div>')

    def _update():
        table.rows = _make_rows(returns, search_input.value or '')
        table.update()

    search_input.on('update:model-value', lambda _: _update())

    with ui.expansion('반품 상세', icon='info_outline').classes('w-full').style(
        f'margin-top:16px;background:{BG_CARD};border:1px solid {BORDER};border-radius:12px'
    ).props('dense header-class="text-grey-5"'):
        ui.label('테이블에서 행을 클릭하면 상세 정보가 표시됩니다.').style(f'color:{TEXT_MUTED};font-size:13px')

    ui.timer(30, _refresh, active=True)
