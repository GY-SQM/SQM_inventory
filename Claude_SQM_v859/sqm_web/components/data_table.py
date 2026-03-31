# -*- coding: utf-8 -*-
"""
SQM Web — Data Table Component
================================
Reusable table component with status badges, search, and pagination.
"""

from typing import List, Dict, Callable, Optional
from nicegui import ui
from .status_badge import status_badge_html


def sqm_table(
    columns: List[Dict],
    rows: List[Dict],
    row_key: str = 'id',
    title: str = '',
    on_row_click: Optional[Callable] = None,
    pagination: int = 20,
    search_value: str = '',
):
    """Create a styled data table with optional search & status badge rendering.

    columns: list of {name, label, field, sortable, align}
    rows: list of row dicts
    """
    table = ui.table(
        columns=columns,
        rows=rows,
        row_key=row_key,
        pagination=pagination,
        title=title,
    ).classes('w-full').style('font-size:13px')

    # Add status column slot for badge rendering
    for col in columns:
        if col.get('name') == 'status':
            table.add_slot(
                f'body-cell-status',
                '''
                <q-td :props="props">
                    <span v-html="props.value"></span>
                </q-td>
                '''
            )
            break

    if on_row_click:
        table.on('row-click', on_row_click)

    return table


def format_rows_with_badges(rows: List[Dict], status_field: str = 'status') -> List[Dict]:
    """Pre-process rows to replace status text with badge HTML."""
    processed = []
    for row in rows:
        r = dict(row)
        if status_field in r and r[status_field]:
            r[status_field] = status_badge_html(r[status_field])
        processed.append(r)
    return processed


def weight_fmt(kg) -> str:
    """Format weight: kg → display string."""
    try:
        v = float(kg or 0)
        if v >= 1000:
            return f"{v/1000:.1f} MT"
        return f"{v:.0f} kg"
    except (ValueError, TypeError):
        return str(kg or '-')
