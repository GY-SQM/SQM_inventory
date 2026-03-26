# -*- coding: utf-8 -*-
"""
SQM Web — Inventory Page (재고) — Iteration 3
================================================
World-class inventory view: KPI cards, filter bar, data table,
detail panel, action buttons, auto-refresh.
"""

import logging
from nicegui import ui

from sqm_web.bridge import engine_bridge as bridge
from sqm_web.components.kpi_cards import inventory_kpi_row
from sqm_web.components.status_badge import status_badge_html
from sqm_web.components.data_table import weight_fmt
from sqm_web.components.theme import (
    TEXT_PRIMARY, TEXT_MUTED, ACCENT, BG_CARD, BORDER,
    COLOR_AVAILABLE, COLOR_RESERVED, COLOR_PICKED, COLOR_OUTBOUND
)

logger = logging.getLogger(__name__)

COLUMNS = [
    {'name': 'lot_no', 'label': 'LOT No.', 'field': 'lot_no', 'sortable': True, 'align': 'left'},
    {'name': 'sap_no', 'label': 'SAP No.', 'field': 'sap_no', 'sortable': True, 'align': 'left'},
    {'name': 'bl_no', 'label': 'B/L No.', 'field': 'bl_no', 'sortable': True, 'align': 'left'},
    {'name': 'product', 'label': '제품', 'field': 'product', 'sortable': True, 'align': 'left'},
    {'name': 'status', 'label': '상태', 'field': 'status', 'sortable': True, 'align': 'center'},
    {'name': 'current_weight', 'label': '현재중량', 'field': 'current_weight', 'sortable': True, 'align': 'right'},
    {'name': 'initial_weight', 'label': '초기중량', 'field': 'initial_weight', 'sortable': True, 'align': 'right'},
    {'name': 'picked_weight', 'label': '피킹중량', 'field': 'picked_weight', 'sortable': True, 'align': 'right'},
    {'name': 'mxbg_pallet', 'label': '톤백수', 'field': 'mxbg_pallet', 'sortable': True, 'align': 'center'},
    {'name': 'container_no', 'label': '컨테이너', 'field': 'container_no', 'sortable': True, 'align': 'left'},
    {'name': 'warehouse', 'label': '창고', 'field': 'warehouse', 'sortable': True, 'align': 'center'},
    {'name': 'arrival_date', 'label': '입항일', 'field': 'arrival_date', 'sortable': True, 'align': 'center'},
]


async def inventory_page():
    """Render the inventory page — Iteration 3."""

    # ── Load data ──
    try:
        summary = await bridge.get_inventory_summary()
        rows = await bridge.get_inventory()
    except Exception as e:
        ui.notify(f'데이터 로드 실패: {e}', type='negative')
        summary = {}
        rows = []

    # ── Header row: title + action buttons ──
    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        with ui.row().classes('items-center gap-3'):
            ui.label('재고 현황').classes('sqm-section-title').style('margin-bottom:0')
            ui.label(f'{len(rows)} LOTs').style(
                f'font-size:12px;color:{TEXT_MUTED};background:{BG_CARD};'
                f'padding:2px 10px;border-radius:12px;border:1px solid {BORDER}'
            )

        with ui.row().classes('gap-2'):
            async def _open_inbound():
                from sqm_web.pages.inbound_dialog import create_inbound_dialog
                dlg = create_inbound_dialog()
                dlg.open()

            ui.button('입고', icon='add', on_click=_open_inbound).props('unelevated dense').style(
                f'background:{ACCENT};color:white;padding:6px 16px;font-weight:600;font-size:13px'
            )
            ui.button('Excel 내보내기', icon='download').props('outline dense').style(
                f'color:{TEXT_MUTED};border-color:{BORDER};padding:6px 14px;font-size:12px'
            )

    # ── KPI Cards ──
    kpi_container = ui.row().classes('w-full')
    with kpi_container:
        inventory_kpi_row(summary)

    # ── Filter Bar ──
    with ui.row().classes('sqm-filter-bar w-full items-center').style('margin-top:16px'):
        search_input = ui.input(
            placeholder='LOT / B/L / 제품 / 컨테이너 검색...'
        ).props('outlined dense clearable').style('max-width:380px;flex:1')
        search_input.props('bg-color="grey-10"')

        status_select = ui.select(
            ['ALL', 'AVAILABLE', 'RESERVED', 'PICKED', 'OUTBOUND', 'DEPLETED', 'RETURN'],
            value='ALL',
            label='상태 필터'
        ).props('outlined dense').style('min-width:150px')

        # Spacer
        ui.space()

        refresh_btn = ui.button('', icon='refresh', on_click=lambda: _on_refresh()).props(
            'flat dense round'
        ).tooltip('새로고침')

    # ── Process rows for table ──
    def _process_rows(raw_rows, status_f='ALL', keyword=''):
        processed = []
        for row in raw_rows:
            r = dict(row) if not isinstance(row, dict) else dict(row)

            # Filter by status
            st = (r.get('status') or '').upper()
            if status_f != 'ALL' and st != status_f:
                continue

            # Filter by keyword
            if keyword:
                kw = keyword.lower()
                searchable = ' '.join(
                    str(r.get(f, ''))
                    for f in ('lot_no', 'bl_no', 'product', 'container_no', 'sap_no', 'warehouse')
                ).lower()
                if kw not in searchable:
                    continue

            # Format values
            r['current_weight'] = weight_fmt(r.get('current_weight'))
            r['initial_weight'] = weight_fmt(r.get('initial_weight'))
            r['picked_weight'] = weight_fmt(r.get('picked_weight'))
            r['status'] = status_badge_html(st)
            r['mxbg_pallet'] = str(r.get('mxbg_pallet', '-'))
            r['arrival_date'] = str(r.get('arrival_date', '-'))[:10]
            r['warehouse'] = str(r.get('warehouse', '-'))
            r['container_no'] = str(r.get('container_no', '-'))
            processed.append(r)
        return processed

    table_rows = _process_rows(rows)

    # ── Data Table ──
    table = ui.table(
        columns=COLUMNS,
        rows=table_rows,
        row_key='lot_no',
        pagination={'rowsPerPage': 25, 'sortBy': 'lot_no', 'descending': True},
    ).classes('w-full').style('margin-top:4px')

    # Status badge slot
    table.add_slot(
        'body-cell-status',
        '<q-td :props="props"><span v-html="props.value"></span></q-td>'
    )
    # Right-align weight columns
    for col_name in ('current_weight', 'initial_weight', 'picked_weight'):
        table.add_slot(
            f'body-cell-{col_name}',
            f'<q-td :props="props" style="text-align:right;font-family:monospace;font-size:12px">{{{{ props.value }}}}</q-td>'
        )

    # Empty state
    table.add_slot(
        'no-data',
        '<div class="sqm-empty">'
        '<div class="sqm-empty-icon">📦</div>'
        '<div style="font-size:14px;margin-bottom:4px">재고 데이터가 없습니다</div>'
        '<div style="font-size:12px;color:#6b7280">입고 버튼으로 새 LOT를 등록하세요</div>'
        '</div>'
    )

    # ── Detail Panel (collapsible, starts closed) ──
    detail_panel = ui.expansion('LOT 상세 정보', icon='info_outline').classes('w-full').style(
        f'margin-top:16px;background:{BG_CARD};border:1px solid {BORDER};border-radius:12px'
    )
    detail_panel.props('dense header-class="text-grey-5"')
    detail_content = None

    with detail_panel:
        detail_content = ui.column().classes('w-full gap-3 pa-3')
        with detail_content:
            ui.label('테이블에서 LOT를 클릭하면 상세 정보가 표시됩니다.').style(
                f'color:{TEXT_MUTED};font-size:13px'
            )

    # ── Tonbag sub-table container ──
    tonbag_container = ui.column().classes('w-full').style('display:none')

    # ── Event handlers ──
    async def _on_filter_change():
        sf = status_select.value or 'ALL'
        kw = search_input.value or ''
        new_rows = _process_rows(rows, sf, kw)
        table.rows = new_rows
        table.update()

    async def _on_refresh():
        nonlocal summary, rows
        try:
            summary = await bridge.get_inventory_summary()
            rows = await bridge.get_inventory()
            await _on_filter_change()
            kpi_container.clear()
            with kpi_container:
                inventory_kpi_row(summary)
            ui.notify('새로고침 완료', type='positive', position='bottom-right', timeout=1500)
        except Exception as e:
            ui.notify(f'새로고침 실패: {e}', type='negative')

    async def _on_row_click(e):
        try:
            row_data = e.args[1] if len(e.args) > 1 else e.args[0]
            lot = row_data.get('lot_no', '')
            if not lot:
                return

            detail_content.clear()
            with detail_content:
                # ── LOT info grid ──
                with ui.row().classes('w-full gap-6 flex-wrap'):
                    for field, label, style_extra in [
                        ('lot_no', 'LOT No.', 'font-weight:700;font-size:16px'),
                        ('sap_no', 'SAP No.', ''),
                        ('bl_no', 'B/L No.', ''),
                        ('product', '제품', ''),
                        ('container_no', '컨테이너', ''),
                        ('mxbg_pallet', '톤백수', ''),
                        ('warehouse', '창고', ''),
                        ('arrival_date', '입항일', ''),
                        ('current_weight', '현재중량', f'color:{COLOR_AVAILABLE};font-weight:600'),
                        ('initial_weight', '초기중량', ''),
                        ('picked_weight', '피킹중량', f'color:{COLOR_PICKED}'),
                    ]:
                        with ui.column().classes('gap-0'):
                            ui.label(label).style(f'color:{TEXT_MUTED};font-size:11px;font-weight:500')
                            val = str(row_data.get(field, '-'))
                            # Strip HTML from status badge
                            if '<span' in val:
                                val = (row_data.get('_raw_status', '') or
                                       val.split('</span>')[-2].split('>')[-1] if '>' in val else val)
                            ui.label(val).style(
                                f'font-size:13px;color:{TEXT_PRIMARY};{style_extra}'
                            )

                ui.separator().style(f'background:{BORDER};margin:8px 0')

                # ── Tonbag sub-table ──
                ui.label('톤백 목록').style(
                    f'font-size:12px;font-weight:600;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.05em'
                )
                try:
                    tonbags = await bridge.get_tonbags(lot_no=lot)
                    if tonbags:
                        tb_cols = [
                            {'name': 'sub_lt', 'label': 'Sub-LT', 'field': 'sub_lt', 'align': 'center'},
                            {'name': 'tonbag_no', 'label': '톤백 No.', 'field': 'tonbag_no', 'align': 'left'},
                            {'name': 'status', 'label': '상태', 'field': 'status', 'align': 'center'},
                            {'name': 'weight', 'label': '중량(kg)', 'field': 'weight', 'align': 'right'},
                            {'name': 'location', 'label': '위치', 'field': 'location', 'align': 'left'},
                            {'name': 'is_sample', 'label': '샘플', 'field': 'is_sample', 'align': 'center'},
                        ]
                        tb_rows = []
                        for t in tonbags:
                            tr = dict(t)
                            tr['status'] = status_badge_html(tr.get('status', ''))
                            tr['weight'] = f"{float(tr.get('weight', 0)):.0f}"
                            tr['location'] = str(tr.get('location', '-'))
                            tr['tonbag_no'] = str(tr.get('tonbag_no', '-'))
                            tr['is_sample'] = 'Yes' if tr.get('is_sample') else '-'
                            tb_rows.append(tr)

                        tb_table = ui.table(
                            columns=tb_cols, rows=tb_rows, row_key='sub_lt',
                            pagination={'rowsPerPage': 50},
                        ).classes('w-full').style('font-size:12px')

                        tb_table.add_slot(
                            'body-cell-status',
                            '<q-td :props="props"><span v-html="props.value"></span></q-td>'
                        )
                    else:
                        ui.label('톤백 데이터가 없습니다.').style(f'color:{TEXT_MUTED};font-size:13px')
                except Exception as ex:
                    ui.label(f'톤백 로드 실패: {ex}').style(f'color:#f87171;font-size:13px')

            detail_panel.open()

        except Exception as ex:
            logger.warning(f"[UI] row click: {ex}")

    search_input.on('update:model-value', lambda _: _on_filter_change())
    status_select.on('update:model-value', lambda _: _on_filter_change())
    table.on('row-click', _on_row_click)

    # ── Auto-refresh every 30 seconds ──
    ui.timer(30, _on_refresh, active=True)
