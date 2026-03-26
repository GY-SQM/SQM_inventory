# -*- coding: utf-8 -*-
"""
SQM Web — Picking Page (피킹) — Iteration 3
==============================================
"""

import logging
from nicegui import ui

from sqm_web.bridge import engine_bridge as bridge
from sqm_web.components.kpi_cards import inventory_kpi_row
from sqm_web.components.status_badge import status_badge_html
from sqm_web.components.data_table import weight_fmt
from sqm_web.components.theme import TEXT_MUTED, BG_CARD, BORDER

logger = logging.getLogger(__name__)

COLUMNS = [
    {'name': 'lot_no', 'label': 'LOT No.', 'field': 'lot_no', 'sortable': True, 'align': 'left'},
    {'name': 'sub_lt', 'label': 'Sub-LT', 'field': 'sub_lt', 'sortable': True, 'align': 'center'},
    {'name': 'tonbag_no', 'label': '톤백 No.', 'field': 'tonbag_no', 'sortable': True, 'align': 'left'},
    {'name': 'status', 'label': '상태', 'field': 'status', 'sortable': True, 'align': 'center'},
    {'name': 'weight', 'label': '중량', 'field': 'weight', 'sortable': True, 'align': 'right'},
    {'name': 'location', 'label': '위치', 'field': 'location', 'sortable': True, 'align': 'left'},
    {'name': 'picked_to', 'label': '고객사', 'field': 'picked_to', 'sortable': True, 'align': 'left'},
    {'name': 'picked_date', 'label': '피킹일', 'field': 'picked_date', 'sortable': True, 'align': 'center'},
]


async def picking_page():
    """Render the picking page — Iteration 3."""
    try:
        summary = await bridge.get_inventory_summary()
        tonbags = await bridge.get_tonbags(status='PICKED')
    except Exception as e:
        ui.notify(f'데이터 로드 실패: {e}', type='negative')
        summary = {}
        tonbags = []

    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        with ui.row().classes('items-center gap-3'):
            ui.label('피킹 관리').classes('sqm-section-title').style('margin-bottom:0')
            ui.label(f'{len(tonbags)}개 톤백').style(
                f'font-size:12px;color:{TEXT_MUTED};background:{BG_CARD};'
                f'padding:2px 10px;border-radius:12px;border:1px solid {BORDER}'
            )

        async def _refresh():
            nonlocal tonbags, summary
            summary = await bridge.get_inventory_summary()
            tonbags = await bridge.get_tonbags(status='PICKED')
            _update_table()
            ui.notify('새로고침 완료', type='positive', position='bottom-right', timeout=1500)

        ui.button('', icon='refresh', on_click=_refresh).props('flat dense round').tooltip('새로고침')

    inventory_kpi_row(summary)

    with ui.row().classes('sqm-filter-bar w-full items-center').style('margin-top:16px'):
        search_input = ui.input(placeholder='LOT / 톤백 / 고객사 검색...').props(
            'outlined dense clearable'
        ).style('max-width:360px;flex:1')

    def _make_rows(raw, kw=''):
        result = []
        for t in raw:
            r = dict(t)
            if kw:
                searchable = f"{r.get('lot_no','')} {r.get('tonbag_no','')} {r.get('picked_to','')}".lower()
                if kw.lower() not in searchable:
                    continue
            r['status'] = status_badge_html(r.get('status', ''))
            r['weight'] = weight_fmt(r.get('weight'))
            r['picked_date'] = str(r.get('picked_date', '-'))[:10]
            r['picked_to'] = r.get('picked_to', '-') or '-'
            r['location'] = r.get('location', '-') or '-'
            r['tonbag_no'] = r.get('tonbag_no', '-') or '-'
            result.append(r)
        return result

    table = ui.table(
        columns=COLUMNS, rows=_make_rows(tonbags), row_key='id',
        pagination={'rowsPerPage': 25, 'sortBy': 'picked_date', 'descending': True},
    ).classes('w-full')

    table.add_slot('body-cell-status', '<q-td :props="props"><span v-html="props.value"></span></q-td>')
    table.add_slot('no-data',
        '<div class="sqm-empty"><div class="sqm-empty-icon">🚛</div>'
        '<div style="font-size:14px">피킹된 톤백이 없습니다</div>'
        '<div style="font-size:12px;color:#6b7280">배정 후 피킹 처리된 톤백이 여기에 표시됩니다</div></div>')

    def _update_table():
        table.rows = _make_rows(tonbags, search_input.value or '')
        table.update()

    search_input.on('update:model-value', lambda _: _update_table())

    with ui.expansion('피킹 상세', icon='info_outline').classes('w-full').style(
        f'margin-top:16px;background:{BG_CARD};border:1px solid {BORDER};border-radius:12px'
    ).props('dense header-class="text-grey-5"'):
        ui.label('테이블에서 톤백을 클릭하면 상세 정보가 표시됩니다.').style(f'color:{TEXT_MUTED};font-size:13px')

    ui.timer(30, _refresh, active=True)
