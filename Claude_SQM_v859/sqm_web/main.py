# -*- coding: utf-8 -*-
"""
SQM Web — Main Entry Point
============================
NiceGUI web application for SQM v8.1.5
Run: python sqm_web/main.py
Open: http://localhost:8080
"""

import os
import sys
import logging
from pathlib import Path

# Fix cp949 encoding issue on Windows (emoji in engine logs)
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONUTF8', '1')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

# Add project root to path
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from nicegui import ui, app

# Import theme
from sqm_web.components.theme import GLOBAL_CSS

# Import page builders
from sqm_web.pages.inventory_page import inventory_page
from sqm_web.pages.allocation_page import allocation_page
from sqm_web.pages.picking_page import picking_page
from sqm_web.pages.outbound_page import outbound_page
from sqm_web.pages.return_page import return_page
from sqm_web.pages.dashboard_page import dashboard_page
from sqm_web.pages.logs_page import logs_page

# Import sidebar
from sqm_web.components.sidebar import create_sidebar

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('sqm_web')


# ═══════════════════════════════════════════════════════
# Inject global CSS
# ═══════════════════════════════════════════════════════
app.add_static_files('/static', str(Path(__file__).parent / 'static'), follow_symlink=True)


def _page_layout(active_path: str):
    """Common page layout wrapper: dark mode + sidebar + content area."""
    ui.dark_mode().enable()
    ui.add_css(GLOBAL_CSS)

    # Full-screen row: sidebar + content
    layout = ui.row().classes('w-full no-wrap').style(
        'min-height:100vh;background:#0f1117;'
    )
    return layout


# ═══════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════

@ui.page('/')
async def page_inventory():
    with _page_layout('/'):
        create_sidebar('/')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await inventory_page()


@ui.page('/allocation')
async def page_allocation():
    with _page_layout('/allocation'):
        create_sidebar('/allocation')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await allocation_page()


@ui.page('/picking')
async def page_picking():
    with _page_layout('/picking'):
        create_sidebar('/picking')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await picking_page()


@ui.page('/outbound')
async def page_outbound():
    with _page_layout('/outbound'):
        create_sidebar('/outbound')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await outbound_page()


@ui.page('/return')
async def page_return():
    with _page_layout('/return'):
        create_sidebar('/return')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await return_page()


@ui.page('/dashboard')
async def page_dashboard():
    with _page_layout('/dashboard'):
        create_sidebar('/dashboard')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await dashboard_page()


@ui.page('/logs')
async def page_logs():
    with _page_layout('/logs'):
        create_sidebar('/logs')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            await logs_page()


@ui.page('/settings')
async def page_settings():
    with _page_layout('/settings'):
        create_sidebar('/settings')
        with ui.column().classes('flex-1 overflow-auto').style('padding:24px;max-height:100vh'):
            ui.label('설정').classes('sqm-section-title')
            with ui.card().classes('sqm-card'):
                ui.label('SQM v8.1.5 — NiceGUI Web Interface').style('color:#e2e8f0')
                ui.label('광양 탄산리튬 창고관리 시스템').style('color:#6b7280;font-size:13px')
                ui.separator().style('background:#2d3148')
                with ui.row().classes('gap-4'):
                    ui.label('DB:').style('color:#6b7280;font-size:13px')
                    from config import DB_PATH
                    ui.label(str(DB_PATH)).style('color:#e2e8f0;font-size:13px;font-family:monospace')


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

if __name__ in {'__main__', '__mp_main__'}:
    logger.info("Starting SQM Web v8.1.5...")

    # Try ports 8080, 8081, 8082, 8090
    import socket

    def _port_available(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except OSError:
            return False

    port = 8080
    for p in [8080, 8081, 8082, 8090]:
        if _port_available(p):
            port = p
            break

    logger.info(f"SQM Web starting on port {port}")
    ui.run(
        title='SQM v8.1.5 — 재고관리',
        port=port,
        reload=False,
        dark=True,
        favicon='⚡',
        show=True,
    )
