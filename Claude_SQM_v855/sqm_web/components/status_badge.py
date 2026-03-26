# -*- coding: utf-8 -*-
"""
SQM Web — Status Badge Component
==================================
Pill-style status badges with colored dots.
"""

from nicegui import ui
from .theme import BADGE_BG, BADGE_TEXT, BADGE_DOT


STATUS_LABELS = {
    'AVAILABLE': 'AVAILABLE',
    'RESERVED': 'RESERVED',
    'PICKED': 'PICKED',
    'OUTBOUND': 'OUTBOUND',
    'SOLD': 'OUTBOUND',
    'SHIPPED': 'SHIPPED',
    'CONFIRMED': 'CONFIRMED',
    'RETURN': 'RETURN',
    'DEPLETED': 'DEPLETED',
    'PARTIAL': 'PARTIAL',
}


def status_badge(status: str):
    """Render a pill-style status badge with colored dot."""
    s = (status or 'UNKNOWN').upper().strip()
    bg = BADGE_BG.get(s, '#1f2937')
    text_color = BADGE_TEXT.get(s, '#9ca3af')
    dot_color = BADGE_DOT.get(s, '#9ca3af')
    label = STATUS_LABELS.get(s, s)

    ui.html(
        f'<span class="sqm-badge" style="background:{bg};color:{text_color};">'
        f'<span class="sqm-badge-dot" style="background:{dot_color};"></span>'
        f'{label}</span>'
    )


def status_badge_html(status: str) -> str:
    """Return HTML string for a status badge (for use in table slots)."""
    s = (status or 'UNKNOWN').upper().strip()
    bg = BADGE_BG.get(s, '#1f2937')
    text_color = BADGE_TEXT.get(s, '#9ca3af')
    dot_color = BADGE_DOT.get(s, '#9ca3af')
    label = STATUS_LABELS.get(s, s)

    return (
        f'<span class="sqm-badge" style="background:{bg};color:{text_color};">'
        f'<span class="sqm-badge-dot" style="background:{dot_color};"></span>'
        f'{label}</span>'
    )
