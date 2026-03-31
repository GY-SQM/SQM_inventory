# -*- coding: utf-8 -*-
"""
SQM Web — Allocation Page (배정) — Iteration 3
=================================================
"""

import logging
from nicegui import ui

from sqm_web.bridge import engine_bridge as bridge
from sqm_web.components.kpi_cards import inventory_kpi_row
from sqm_web.components.status_badge import status_badge_html
from sqm_web.components.theme import TEXT_MUTED, BG_CARD, BORDER, TEXT_PRIMARY

logger = logging.getLogger(__name__)

COLUMNS = [
    {'name': 'lot_no', 'label': 'LOT No.', 'field': 'lot_no', 'sortable': True, 'align': 'left'},
    {'name': 'bl_no', 'label': 'B/L No.', 'field': 'bl_no', 'sortable': True, 'align': 'left'},
    {'name': 'product', 'label': '제품', 'field': 'product', 'sortable': True, 'align': 'left'},
    {'name': 'status', 'label': '상태', 'field': 'status', 'sortable': True, 'align': 'center'},
    {'name': 'customer', 'label': '고객사', 'field': 'customer', 'sortable': True, 'align': 'left'},
    {'name': 'qty', 'label': '수량', 'field': 'qty', 'sortable': True, 'align': 'right'},
    {'name': 'current_weight', 'label': '중량', 'field': 'current_weight', 'sortable': True, 'align': 'right'},
    {'name': 'created_at', 'label': '생성일', 'field': 'created_at', 'sortable': True, 'align': 'center'},
]


async def allocation_page():
    """Render the allocation page — Iteration 3."""
    try:
        summary = await bridge.get_inventory_summary()
        plans = await bridge.get_allocation_plans()
    except Exception as e:
        ui.notify(f'데이터 로드 실패: {e}', type='negative')
        summary = {}
        plans = []

    # Header
    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        with ui.row().classes('items-center gap-3'):
            ui.label('배정 관리').classes('sqm-section-title').style('margin-bottom:0')
            ui.label(f'{len(plans)}건').style(
                f'font-size:12px;color:{TEXT_MUTED};background:{BG_CARD};'
                f'padding:2px 10px;border-radius:12px;border:1px solid {BORDER}'
            )
        ui.button('', icon='refresh').props('flat dense round').tooltip('새로고침')

    inventory_kpi_row(summary)

    # Filter
    with ui.row().classes('sqm-filter-bar w-full items-center').style('margin-top:16px'):
        search_input = ui.input(placeholder='LOT / 고객사 검색...').props(
            'outlined dense clearable'
        ).style('max-width:360px;flex:1')
        status_sel = ui.select(
            ['ALL', 'RESERVED', 'EXECUTED', 'STAGED', 'CANCELLED'],
            value='ALL', label='상태'
        ).props('outlined dense').style('min-width:150px')

    # Process rows
    def _process(raw, status_f='ALL', kw=''):
        result = []
        for p in raw:
            r = dict(p)
            st = (r.get('status') or '').upper()
            if status_f != 'ALL' and st != status_f:
                continue
            if kw:
                searchable = f"{r.get('lot_no','')} {r.get('customer','')} {r.get('sold_to','')} {r.get('bl_no','')}".lower()
                if kw.lower() not in searchable:
                    continue
            r['status'] = status_badge_html(st)
            r['customer'] = r.get('customer', r.get('sold_to', '-'))
            r['qty'] = str(r.get('tonbag_count', r.get('qty', '-')))
            r['current_weight'] = f"{float(r.get('current_weight', 0)):.0f} kg" if r.get('current_weight') else '-'
            r['created_at'] = str(r.get('created_at', '-'))[:16]
            r['bl_no'] = r.get('bl_no', '-') or '-'
            r['product'] = r.get('product', '-') or '-'
            result.append(r)
        return result

    table_rows = _process(plans)

    table = ui.table(
        columns=COLUMNS, rows=table_rows, row_key='lot_no',
        pagination={'rowsPerPage': 25, 'sortBy': 'created_at', 'descending': True},
    ).classes('w-full')

    table.add_slot('body-cell-status', '<q-td :props="props"><span v-html="props.value"></span></q-td>')
    table.add_slot('no-data',
        '<div class="sqm-empty"><div class="sqm-empty-icon">📋</div>'
        '<div style="font-size:14px">배정 데이터가 없습니다</div>'
        '<div style="font-size:12px;color:#6b7280">배정 계획이 생성되면 여기에 표시됩니다</div></div>')

    async def _filter():
        table.rows = _process(plans, status_sel.value or 'ALL', search_input.value or '')
        table.update()

    search_input.on('update:model-value', lambda _: _filter())
    status_sel.on('update:model-value', lambda _: _filter())

    # Detail
    with ui.expansion('배정 상세', icon='info_outline').classes('w-full').style(
        f'margin-top:16px;background:{BG_CARD};border:1px solid {BORDER};border-radius:12px'
    ).props('dense header-class="text-grey-5"'):
        ui.label('테이블에서 행을 클릭하면 상세 정보가 표시됩니다.').style(f'color:{TEXT_MUTED};font-size:13px')
