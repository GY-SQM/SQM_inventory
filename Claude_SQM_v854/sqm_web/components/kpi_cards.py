# -*- coding: utf-8 -*-
"""
SQM Web — KPI Cards Component
================================
Stripe-inspired KPI cards with status-colored values.
"""

from nicegui import ui
from .theme import (
    COLOR_AVAILABLE, COLOR_RESERVED, COLOR_PICKED,
    COLOR_OUTBOUND, COLOR_RETURN, TEXT_PRIMARY
)

STATUS_COLORS = {
    'AVAILABLE': COLOR_AVAILABLE,
    'RESERVED': COLOR_RESERVED,
    'PICKED': COLOR_PICKED,
    'OUTBOUND': COLOR_OUTBOUND,
    'RETURN': COLOR_RETURN,
    'TOTAL': TEXT_PRIMARY,
    'DEPLETED': '#6b7280',
}


def kpi_card(label: str, value: str, sub: str = '', color: str = None):
    """Single KPI card."""
    c = color or TEXT_PRIMARY
    with ui.column().classes('sqm-kpi flex-1'):
        ui.label(label).classes('sqm-kpi-label')
        ui.label(value).classes('sqm-kpi-value').style(f'color:{c}')
        if sub:
            ui.label(sub).classes('sqm-kpi-sub')


def inventory_kpi_row(summary: dict):
    """Render a row of 5 KPI cards for inventory summary.

    summary: {status: {count, weight_mt}} from engine_bridge.get_inventory_summary()
    """
    avail = summary.get('AVAILABLE', {})
    reserved = summary.get('RESERVED', {})
    picked = summary.get('PICKED', {})
    outbound_data = {}
    for s in ('OUTBOUND', 'SOLD', 'SHIPPED', 'CONFIRMED'):
        d = summary.get(s, {})
        outbound_data['count'] = outbound_data.get('count', 0) + d.get('count', 0)
        outbound_data['weight_mt'] = outbound_data.get('weight_mt', 0) + d.get('weight_mt', 0)

    total_count = sum(v.get('count', 0) for v in summary.values())
    total_mt = sum(v.get('weight_mt', 0) for v in summary.values())

    with ui.row().classes('w-full gap-3 flex-wrap'):
        kpi_card(
            'AVAILABLE',
            f"{avail.get('count', 0)}",
            f"{avail.get('weight_mt', 0):.1f} MT",
            COLOR_AVAILABLE
        )
        kpi_card(
            'RESERVED',
            f"{reserved.get('count', 0)}",
            f"{reserved.get('weight_mt', 0):.1f} MT",
            COLOR_RESERVED
        )
        kpi_card(
            'PICKED',
            f"{picked.get('count', 0)}",
            f"{picked.get('weight_mt', 0):.1f} MT",
            COLOR_PICKED
        )
        kpi_card(
            'OUTBOUND',
            f"{outbound_data.get('count', 0)}",
            f"{outbound_data.get('weight_mt', 0):.1f} MT",
            COLOR_OUTBOUND
        )
        kpi_card(
            'TOTAL',
            f"{total_count}",
            f"{total_mt:.1f} MT",
            TEXT_PRIMARY
        )
