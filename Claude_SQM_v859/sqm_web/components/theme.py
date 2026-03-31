# -*- coding: utf-8 -*-
"""
SQM Web — Theme & Design System
=================================
World-class design tokens inspired by Linear, Stripe, Vercel.
"""

# ═══════════════════════════════════════════════════════
# Color Palette (Dark Theme)
# ═══════════════════════════════════════════════════════

BG_PRIMARY = '#0f1117'
BG_SECONDARY = '#1a1d27'
BG_CARD = '#1e2235'
BG_SIDEBAR = '#12151f'
BG_HOVER = '#252a3a'
BG_TABLE_HEADER = '#161929'
BG_TABLE_ODD = '#1a1d27'
BG_TABLE_EVEN = '#1e2235'

BORDER = '#2d3148'
BORDER_ACCENT = '#4f46e5'

TEXT_PRIMARY = '#e2e8f0'
TEXT_MUTED = '#6b7280'
TEXT_LABEL = '#94a3b8'

ACCENT = '#4f46e5'
ACCENT_HOVER = '#6366f1'

# Status colors
COLOR_AVAILABLE = '#34d399'
COLOR_RESERVED = '#60a5fa'
COLOR_PICKED = '#fbbf24'
COLOR_OUTBOUND = '#9ca3af'
COLOR_RETURN = '#f87171'
COLOR_DANGER = '#ef4444'
COLOR_SUCCESS = '#10b981'

# Status badge backgrounds
BADGE_BG = {
    'AVAILABLE': '#064e3b',
    'RESERVED': '#1e3a5f',
    'PICKED': '#451a03',
    'OUTBOUND': '#1f2937',
    'SOLD': '#1f2937',
    'SHIPPED': '#1f2937',
    'CONFIRMED': '#1f2937',
    'RETURN': '#450a0a',
    'DEPLETED': '#1f1f1f',
    'PARTIAL': '#3b2f00',
}

BADGE_TEXT = {
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

BADGE_DOT = BADGE_TEXT  # Same as text color for the dot

# ═══════════════════════════════════════════════════════
# Typography
# ═══════════════════════════════════════════════════════

FONT_FAMILY = "'Pretendard', '맑은 고딕', 'Malgun Gothic', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Consolas', monospace"

FONT_SIZE_BASE = '14px'
FONT_SIZE_TABLE = '13px'
FONT_SIZE_LABEL = '12px'
FONT_SIZE_BADGE = '11px'
FONT_SIZE_TITLE = '18px'
FONT_SIZE_KPI = '22px'
FONT_SIZE_SUB = '11px'

# ═══════════════════════════════════════════════════════
# Spacing
# ═══════════════════════════════════════════════════════

SIDEBAR_WIDTH = '200px'
SIDEBAR_ICON_SIZE = '20px'
CONTENT_PADDING = '24px'
CARD_PADDING = '16px'
CARD_GAP = '12px'
TABLE_ROW_HEIGHT = '44px'
BUTTON_PADDING_V = '8px'
BUTTON_PADDING_H = '16px'
INPUT_HEIGHT = '36px'
DIALOG_MIN_WIDTH = '600px'
DIALOG_MAX_WIDTH = '900px'
BORDER_RADIUS = '12px'
BORDER_RADIUS_SM = '8px'
BORDER_RADIUS_BADGE = '20px'

# ═══════════════════════════════════════════════════════
# Global CSS
# ═══════════════════════════════════════════════════════

GLOBAL_CSS = f"""
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

:root {{
    --bg-primary: {BG_PRIMARY};
    --bg-secondary: {BG_SECONDARY};
    --bg-card: {BG_CARD};
    --bg-sidebar: {BG_SIDEBAR};
    --border: {BORDER};
    --accent: {ACCENT};
    --text-primary: {TEXT_PRIMARY};
    --text-muted: {TEXT_MUTED};
}}

body {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_BASE};
    line-height: 1.6;
    color: {TEXT_PRIMARY};
    background: {BG_PRIMARY};
    -webkit-font-smoothing: antialiased;
}}

.q-page {{
    background: {BG_PRIMARY} !important;
}}

/* Scrollbar styling */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: {BG_PRIMARY};
}}
::-webkit-scrollbar-thumb {{
    background: {BORDER};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {TEXT_MUTED};
}}

/* Table tweaks */
.q-table__container {{
    background: {BG_CARD} !important;
    border-radius: {BORDER_RADIUS_SM} !important;
    border: 1px solid {BORDER} !important;
}}

.q-table thead tr {{
    background: {BG_TABLE_HEADER} !important;
}}

.q-table thead th {{
    font-size: {FONT_SIZE_LABEL} !important;
    font-weight: 600 !important;
    color: {TEXT_LABEL} !important;
    border-bottom: 1px solid {BORDER} !important;
    padding: 10px 12px !important;
}}

.q-table tbody td {{
    font-size: {FONT_SIZE_TABLE} !important;
    color: {TEXT_PRIMARY} !important;
    padding: 10px 12px !important;
    border-bottom: 1px solid {BORDER}22 !important;
    height: {TABLE_ROW_HEIGHT} !important;
}}

.q-table tbody tr:nth-child(odd) {{
    background: {BG_TABLE_ODD} !important;
}}

.q-table tbody tr:nth-child(even) {{
    background: {BG_TABLE_EVEN} !important;
}}

.q-table tbody tr:hover {{
    background: {BG_HOVER} !important;
}}

/* Card styling */
.sqm-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {BORDER_RADIUS};
    padding: {CARD_PADDING};
    transition: border-color 0.2s ease;
}}

.sqm-card:hover {{
    border-color: {BORDER_ACCENT}44;
}}

/* KPI card */
.sqm-kpi {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: {BORDER_RADIUS};
    padding: 16px;
    min-width: 160px;
    transition: border-color 0.2s ease;
}}

.sqm-kpi:hover {{
    border-color: {BORDER_ACCENT}66;
}}

.sqm-kpi-label {{
    font-size: {FONT_SIZE_SUB};
    color: {TEXT_MUTED};
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}}

.sqm-kpi-value {{
    font-size: {FONT_SIZE_KPI};
    font-weight: 700;
    line-height: 1.2;
}}

.sqm-kpi-sub {{
    font-size: {FONT_SIZE_SUB};
    color: {TEXT_MUTED};
    margin-top: 4px;
}}

/* Status badge */
.sqm-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: {BORDER_RADIUS_BADGE};
    font-size: {FONT_SIZE_BADGE};
    font-weight: 600;
    white-space: nowrap;
}}

.sqm-badge-dot {{
    width: 5px;
    height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
}}

/* Sidebar */
.sqm-sidebar {{
    background: {BG_SIDEBAR};
    border-right: 1px solid {BORDER};
    width: {SIDEBAR_WIDTH};
    min-width: {SIDEBAR_WIDTH};
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}}

.sqm-nav-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    color: {TEXT_MUTED};
    cursor: pointer;
    transition: all 0.15s ease;
    font-size: 13px;
    font-weight: 500;
    border-left: 3px solid transparent;
    text-decoration: none;
}}

.sqm-nav-item:hover {{
    background: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

.sqm-nav-item.active {{
    background: {ACCENT}15;
    color: {TEXT_PRIMARY};
    border-left-color: {ACCENT};
}}

.sqm-nav-icon {{
    font-size: 18px;
    width: 24px;
    text-align: center;
    flex-shrink: 0;
}}

/* Section title */
.sqm-section-title {{
    font-size: {FONT_SIZE_TITLE};
    font-weight: 700;
    color: {TEXT_PRIMARY};
    margin-bottom: 12px;
}}

/* Filter bar */
.sqm-filter-bar {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}}

/* Empty state */
.sqm-empty {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    color: {TEXT_MUTED};
    text-align: center;
}}

.sqm-empty-icon {{
    font-size: 36px;
    margin-bottom: 12px;
    opacity: 0.5;
}}

/* Notification overrides */
.q-notification {{
    font-family: {FONT_FAMILY} !important;
}}
"""
