# -*- coding: utf-8 -*-
"""
SQM Web — Logs Page (로그) — Iteration 3
==========================================
Stock movement log viewer with colored movement types.
"""

import logging
from nicegui import ui

from sqm_web.bridge import engine_bridge as bridge
from sqm_web.components.data_table import weight_fmt
from sqm_web.components.theme import TEXT_MUTED, BG_CARD, BORDER

logger = logging.getLogger(__name__)

COLUMNS = [
    {'name': 'created_at', 'label': '일시', 'field': 'created_at', 'sortable': True, 'align': 'center'},
    {'name': 'movement_type', 'label': '유형', 'field': 'movement_type', 'sortable': True, 'align': 'center'},
    {'name': 'lot_no', 'label': 'LOT No.', 'field': 'lot_no', 'sortable': True, 'align': 'left'},
    {'name': 'qty_kg', 'label': '중량', 'field': 'qty_kg', 'sortable': True, 'align': 'right'},
    {'name': 'remarks', 'label': '비고', 'field': 'remarks', 'sortable': False, 'align': 'left'},
    {'name': 'source_type', 'label': '출처유형', 'field': 'source_type', 'sortable': True, 'align': 'center'},
    {'name': 'source_file', 'label': '출처파일', 'field': 'source_file', 'sortable': True, 'align': 'left'},
]

MOVEMENT_COLORS = {
    'INBOUND': '#34d399',
    'OUTBOUND': '#f87171',
    'RETURN': '#fbbf24',
    'RETURN_TO_AVAILABLE': '#60a5fa',
    'PICKING': '#fbbf24',
    'CANCEL': '#9ca3af',
    'CANCEL_OUTBOUND': '#9ca3af',
    'RELOCATION': '#818cf8',
    'MOVE': '#818cf8',
}


async def logs_page():
    """Render the logs page — Iteration 3."""
    try:
        movements = await bridge.get_stock_movements(limit=500)
    except Exception as e:
        ui.notify(f'로그 로드 실패: {e}', type='negative')
        movements = []

    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        with ui.row().classes('items-center gap-3'):
            ui.label('재고 이동 로그').classes('sqm-section-title').style('margin-bottom:0')
            ui.label(f'{len(movements)}건').style(
                f'font-size:12px;color:{TEXT_MUTED};background:{BG_CARD};'
                f'padding:2px 10px;border-radius:12px;border:1px solid {BORDER}'
            )

        async def _refresh():
            nonlocal movements
            movements = await bridge.get_stock_movements(limit=500)
            _update()
            ui.notify('새로고침 완료', type='positive', position='bottom-right', timeout=1500)

        ui.button('', icon='refresh', on_click=_refresh).props('flat dense round').tooltip('새로고침')

    # Filter
    with ui.row().classes('sqm-filter-bar w-full items-center'):
        search_input = ui.input(placeholder='LOT / 유형 검색...').props(
            'outlined dense clearable'
        ).style('max-width:360px;flex:1')
        type_sel = ui.select(
            ['ALL', 'INBOUND', 'OUTBOUND', 'RETURN', 'PICKING', 'CANCEL', 'RELOCATION'],
            value='ALL', label='유형'
        ).props('outlined dense').style('min-width:150px')

    def _make_rows(raw, type_f='ALL', kw=''):
        result = []
        for m in raw:
            r = dict(m)
            mt = (r.get('movement_type') or '').upper()
            if type_f != 'ALL' and mt != type_f:
                continue
            if kw:
                searchable = f"{r.get('lot_no','')} {mt} {r.get('remarks','')}".lower()
                if kw.lower() not in searchable:
                    continue
            color = MOVEMENT_COLORS.get(mt, '#9ca3af')
            r['movement_type'] = (
                f'<span style="color:{color};font-weight:600;font-size:12px">{mt}</span>'
            )
            r['qty_kg'] = weight_fmt(r.get('qty_kg'))
            r['created_at'] = str(r.get('created_at', '-'))[:19]
            r['remarks'] = str(r.get('remarks', '-'))[:80]
            r['source_type'] = str(r.get('source_type', '-'))
            r['source_file'] = str(r.get('source_file', '-'))[:40]
            result.append(r)
        return result

    table = ui.table(
        columns=COLUMNS, rows=_make_rows(movements), row_key='id',
        pagination={'rowsPerPage': 30, 'sortBy': 'created_at', 'descending': True},
    ).classes('w-full')

    table.add_slot('body-cell-movement_type',
        '<q-td :props="props"><span v-html="props.value"></span></q-td>')
    table.add_slot('no-data',
        '<div class="sqm-empty"><div class="sqm-empty-icon">📝</div>'
        '<div style="font-size:14px">이동 로그가 없습니다</div></div>')

    def _update():
        table.rows = _make_rows(movements, type_sel.value or 'ALL', search_input.value or '')
        table.update()

    search_input.on('update:model-value', lambda _: _update())
    type_sel.on('update:model-value', lambda _: _update())
