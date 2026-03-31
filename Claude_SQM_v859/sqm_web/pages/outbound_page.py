# -*- coding: utf-8 -*-
"""
SQM Web — Outbound Page (출고) — Iteration 3
===============================================
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
    {'name': 'picked_to', 'label': '고객사', 'field': 'picked_to', 'sortable': True, 'align': 'left'},
    {'name': 'product', 'label': '제품', 'field': 'product', 'sortable': True, 'align': 'left'},
    {'name': 'bl_no', 'label': 'B/L No.', 'field': 'bl_no', 'sortable': True, 'align': 'left'},
    {'name': 'updated_at', 'label': '출고일', 'field': 'updated_at', 'sortable': True, 'align': 'center'},
]


async def outbound_page():
    """Render the outbound page — Iteration 3."""
    try:
        summary = await bridge.get_inventory_summary()
        records = await bridge.get_outbound_history()
    except Exception as e:
        ui.notify(f'데이터 로드 실패: {e}', type='negative')
        summary = {}
        records = []

    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        with ui.row().classes('items-center gap-3'):
            ui.label('출고 현황').classes('sqm-section-title').style('margin-bottom:0')
            ui.label(f'{len(records)}건').style(
                f'font-size:12px;color:{TEXT_MUTED};background:{BG_CARD};'
                f'padding:2px 10px;border-radius:12px;border:1px solid {BORDER}'
            )

        async def _refresh():
            nonlocal records, summary
            summary = await bridge.get_inventory_summary()
            records = await bridge.get_outbound_history()
            _update()
            ui.notify('새로고침 완료', type='positive', position='bottom-right', timeout=1500)

        ui.button('', icon='refresh', on_click=_refresh).props('flat dense round').tooltip('새로고침')

    inventory_kpi_row(summary)

    with ui.row().classes('sqm-filter-bar w-full items-center').style('margin-top:16px'):
        search_input = ui.input(placeholder='LOT / 고객사 검색...').props(
            'outlined dense clearable'
        ).style('max-width:360px;flex:1')
        status_sel = ui.select(
            ['ALL', 'PICKED', 'OUTBOUND', 'SOLD', 'CONFIRMED'],
            value='ALL', label='상태'
        ).props('outlined dense').style('min-width:150px')

    def _make_rows(raw, status_f='ALL', kw=''):
        result = []
        for rec in raw:
            r = dict(rec)
            st = (r.get('status') or '').upper()
            if status_f != 'ALL' and st != status_f:
                continue
            if kw:
                searchable = f"{r.get('lot_no','')} {r.get('picked_to','')} {r.get('bl_no','')}".lower()
                if kw.lower() not in searchable:
                    continue
            r['status'] = status_badge_html(st)
            r['weight'] = weight_fmt(r.get('weight'))
            r['picked_to'] = r.get('picked_to', '-') or '-'
            r['product'] = r.get('product', '-') or '-'
            r['bl_no'] = r.get('bl_no', '-') or '-'
            r['tonbag_no'] = r.get('tonbag_no', '-') or '-'
            r['updated_at'] = str(r.get('updated_at', '-'))[:16]
            result.append(r)
        return result

    table = ui.table(
        columns=COLUMNS, rows=_make_rows(records), row_key='id',
        pagination={'rowsPerPage': 25, 'sortBy': 'updated_at', 'descending': True},
    ).classes('w-full')

    table.add_slot('body-cell-status', '<q-td :props="props"><span v-html="props.value"></span></q-td>')
    table.add_slot('no-data',
        '<div class="sqm-empty"><div class="sqm-empty-icon">✅</div>'
        '<div style="font-size:14px">출고 이력이 없습니다</div></div>')

    def _update():
        table.rows = _make_rows(records, status_sel.value or 'ALL', search_input.value or '')
        table.update()

    search_input.on('update:model-value', lambda _: _update())
    status_sel.on('update:model-value', lambda _: _update())

    with ui.expansion('출고 상세', icon='info_outline').classes('w-full').style(
        f'margin-top:16px;background:{BG_CARD};border:1px solid {BORDER};border-radius:12px'
    ).props('dense header-class="text-grey-5"'):
        ui.label('테이블에서 행을 클릭하면 상세 정보가 표시됩니다.').style(f'color:{TEXT_MUTED};font-size:13px')

    ui.timer(30, _refresh, active=True)
