# -*- coding: utf-8 -*-
"""
SQM Web — Dashboard Page (통계) — Iteration 3
================================================
Comprehensive analytics dashboard with charts and breakdowns.
"""

import logging
from nicegui import ui

from sqm_web.bridge import engine_bridge as bridge
from sqm_web.components.theme import (
    COLOR_AVAILABLE, COLOR_RESERVED, COLOR_PICKED,
    COLOR_OUTBOUND, COLOR_RETURN, TEXT_PRIMARY, TEXT_MUTED,
    BG_CARD, BG_SECONDARY, BORDER, ACCENT
)

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    'AVAILABLE': COLOR_AVAILABLE,
    'RESERVED': COLOR_RESERVED,
    'PICKED': COLOR_PICKED,
    'OUTBOUND': COLOR_OUTBOUND,
    'SOLD': COLOR_OUTBOUND,
    'SHIPPED': COLOR_OUTBOUND,
    'CONFIRMED': COLOR_OUTBOUND,
    'RETURN': COLOR_RETURN,
    'DEPLETED': '#6b7280',
    'PARTIAL': '#fbbf24',
}


async def dashboard_page():
    """Render the dashboard/stats page — Iteration 3."""
    try:
        stats = await bridge.get_dashboard_stats()
        summary = await bridge.get_inventory_summary()
    except Exception as e:
        ui.notify(f'통계 로드 실패: {e}', type='negative')
        stats = {'total_lots': 0, 'total_tonbags': 0, 'total_weight_mt': 0,
                 'by_status': {}, 'by_product': [], 'recent_movements': []}
        summary = {}

    # ── Header ──
    with ui.row().classes('w-full items-center justify-between').style('margin-bottom:4px'):
        ui.label('통계 대시보드').classes('sqm-section-title').style('margin-bottom:0')
        ui.button('', icon='refresh').props('flat dense round').tooltip('새로고침')

    # ── Top KPI row: 5 cards ──
    with ui.row().classes('w-full gap-3 flex-wrap'):
        for label, value, sub, color in [
            ('총 LOT', str(stats['total_lots']), '전체 LOT 수', TEXT_PRIMARY),
            ('총 톤백', str(stats['total_tonbags']), '전체 톤백 수', TEXT_PRIMARY),
            ('총 중량', f"{stats['total_weight_mt']:.1f}", 'MT (메트릭톤)', ACCENT),
            ('가용', str(summary.get('AVAILABLE', {}).get('count', 0)),
             f"{summary.get('AVAILABLE', {}).get('weight_mt', 0):.1f} MT", COLOR_AVAILABLE),
            ('출고', str(
                sum(summary.get(s, {}).get('count', 0) for s in ('OUTBOUND', 'SOLD', 'SHIPPED', 'CONFIRMED'))
            ), '출고 완료 LOT', COLOR_OUTBOUND),
        ]:
            with ui.column().classes('sqm-kpi flex-1'):
                ui.label(label).classes('sqm-kpi-label')
                ui.label(value).classes('sqm-kpi-value').style(f'color:{color}')
                ui.label(sub).classes('sqm-kpi-sub')

    # ── Two-column layout ──
    with ui.row().classes('w-full gap-4 flex-wrap').style('margin-top:16px'):

        # Left: Status breakdown
        with ui.column().classes('flex-1').style(
            f'min-width:400px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-radius:12px;padding:20px'
        ):
            ui.label('상태별 현황').style(
                f'font-size:14px;font-weight:600;color:{TEXT_PRIMARY};margin-bottom:16px'
            )

            if stats['by_status']:
                total_mt = max(stats['total_weight_mt'], 0.1)
                for status in ['AVAILABLE', 'RESERVED', 'PICKED', 'OUTBOUND', 'SOLD', 'DEPLETED', 'RETURN']:
                    data = stats['by_status'].get(status)
                    if not data:
                        continue
                    color = STATUS_COLORS.get(status, TEXT_MUTED)
                    pct = (data.get('mt', 0) / total_mt) * 100

                    with ui.row().classes('w-full items-center gap-3').style('margin-bottom:10px'):
                        # Status label
                        ui.label(status).style(
                            f'width:90px;font-size:12px;font-weight:600;color:{color}'
                        )
                        # Progress bar
                        with ui.column().classes('flex-1').style('gap:2px'):
                            with ui.row().classes('w-full').style(
                                f'height:20px;background:{BG_SECONDARY};border-radius:4px;overflow:hidden'
                            ):
                                ui.html(
                                    f'<div style="width:{max(pct, 1.5):.1f}%;height:100%;'
                                    f'background:{color}44;border-radius:3px;'
                                    f'transition:width 0.5s ease"></div>'
                                )
                        # Count + Weight
                        with ui.column().classes('gap-0').style('width:100px;text-align:right'):
                            ui.label(f'{data.get("count", 0)} LOT').style(
                                f'font-size:12px;font-weight:600;color:{TEXT_PRIMARY}'
                            )
                            ui.label(f'{data.get("mt", 0):.1f} MT').style(
                                f'font-size:11px;color:{TEXT_MUTED}'
                            )
            else:
                with ui.column().classes('sqm-empty'):
                    ui.label('📊').style('font-size:28px;opacity:0.4')
                    ui.label('상태 데이터 없음').style(f'color:{TEXT_MUTED};font-size:13px')

        # Right: Product breakdown + Recent movements
        with ui.column().classes('flex-1 gap-4').style('min-width:350px'):

            # Product table
            with ui.column().style(
                f'background:{BG_CARD};border:1px solid {BORDER};'
                f'border-radius:12px;padding:20px'
            ):
                ui.label('제품별 현황').style(
                    f'font-size:14px;font-weight:600;color:{TEXT_PRIMARY};margin-bottom:12px'
                )
                if stats['by_product']:
                    prod_cols = [
                        {'name': 'product', 'label': '제품', 'field': 'product', 'align': 'left', 'sortable': True},
                        {'name': 'cnt', 'label': 'LOT수', 'field': 'cnt', 'align': 'center', 'sortable': True},
                        {'name': 'mt', 'label': '중량(MT)', 'field': 'mt', 'align': 'right', 'sortable': True},
                    ]
                    prod_rows = [
                        {'product': p.get('product', '-') or '-',
                         'cnt': p.get('cnt', 0),
                         'mt': f"{float(p.get('mt', 0)):.1f}"}
                        for p in stats['by_product']
                    ]
                    ui.table(
                        columns=prod_cols, rows=prod_rows, row_key='product',
                        pagination=False,
                    ).classes('w-full')
                else:
                    ui.label('데이터 없음').style(f'color:{TEXT_MUTED};font-size:13px')

            # Recent movements
            with ui.column().style(
                f'background:{BG_CARD};border:1px solid {BORDER};'
                f'border-radius:12px;padding:20px'
            ):
                ui.label('최근 30일 이동').style(
                    f'font-size:14px;font-weight:600;color:{TEXT_PRIMARY};margin-bottom:12px'
                )
                mvmt_colors = {
                    'INBOUND': COLOR_AVAILABLE,
                    'OUTBOUND': '#f87171',
                    'RETURN': '#fbbf24',
                    'RETURN_TO_AVAILABLE': COLOR_RESERVED,
                    'PICKING': COLOR_PICKED,
                    'CANCEL': '#9ca3af',
                    'RELOCATION': '#818cf8',
                }
                if stats['recent_movements']:
                    for m in stats['recent_movements']:
                        mt = m.get('movement_type', '-')
                        cnt = m.get('cnt', 0)
                        mc = mvmt_colors.get(mt, TEXT_MUTED)
                        with ui.row().classes('w-full items-center justify-between').style(
                            f'padding:6px 0;border-bottom:1px solid {BORDER}22'
                        ):
                            with ui.row().classes('items-center gap-2'):
                                ui.html(
                                    f'<div style="width:8px;height:8px;border-radius:50%;background:{mc}"></div>'
                                )
                                ui.label(mt).style(f'font-size:13px;font-weight:600;color:{mc}')
                            ui.label(f'{cnt}건').style(f'font-size:13px;color:{TEXT_PRIMARY};font-weight:500')
                else:
                    ui.label('데이터 없음').style(f'color:{TEXT_MUTED};font-size:13px')
