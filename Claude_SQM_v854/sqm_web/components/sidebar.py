# -*- coding: utf-8 -*-
"""
SQM Web — Sidebar Navigation
==============================
Linear-inspired sidebar with icons and labels.
"""

from nicegui import ui


NAV_ITEMS = [
    {'icon': 'inventory_2', 'label': '재고', 'path': '/'},
    {'icon': 'assignment', 'label': '배정', 'path': '/allocation'},
    {'icon': 'local_shipping', 'label': '피킹', 'path': '/picking'},
    {'icon': 'check_circle', 'label': '출고', 'path': '/outbound'},
    {'icon': 'keyboard_return', 'label': '반품', 'path': '/return'},
    {'icon': 'bar_chart', 'label': '통계', 'path': '/dashboard'},
    {'icon': 'receipt_long', 'label': '로그', 'path': '/logs'},
]


def create_sidebar(active_path: str = '/'):
    """Create the sidebar navigation component."""
    with ui.column().classes('sqm-sidebar'):
        # Logo area
        with ui.row().classes('items-center gap-3 px-4 py-5'):
            ui.html(
                '<div style="width:36px;height:36px;border-radius:10px;'
                'background:linear-gradient(135deg,#4f46e5,#7c3aed);'
                'display:flex;align-items:center;justify-content:center;'
                'font-weight:800;font-size:14px;color:white;">SQ</div>'
            )
            with ui.column().classes('gap-0'):
                ui.label('SQM').classes('text-sm font-bold').style('color:#e2e8f0;line-height:1.2')
                ui.label('v8.1.5').classes('text-xs').style('color:#6b7280;line-height:1.2')

        ui.separator().style('background:#2d3148;margin:0 12px')

        # Navigation items
        with ui.column().classes('gap-1 px-2 py-2 flex-1'):
            for item in NAV_ITEMS:
                is_active = item['path'] == active_path
                active_cls = ' active' if is_active else ''

                with ui.link(target=item['path']).classes(f'sqm-nav-item{active_cls}').style(
                    'text-decoration:none'
                ):
                    ui.icon(item['icon']).classes('sqm-nav-icon')
                    ui.label(item['label'])

        # Bottom section
        ui.separator().style('background:#2d3148;margin:0 12px')
        with ui.column().classes('gap-1 px-2 py-3'):
            with ui.link(target='/settings').classes('sqm-nav-item').style('text-decoration:none'):
                ui.icon('settings').classes('sqm-nav-icon')
                ui.label('설정')
