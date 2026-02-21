# -*- coding: utf-8 -*-
"""GUI tabs module
v5.5.3 P8: SearchTab, AdvancedTabs, PivotTab 제거 (죽은 코드)
"""

from .dashboard_tab import DashboardTabMixin
from .inventory_tab import InventoryTabMixin
from .outbound_scheduled_tab import OutboundScheduledTabMixin
from .tonbag_tab import TonbagTabMixin
from .log_tab import LogTabMixin
from .summary_tab import SummaryTabMixin

__all__ = [
    'DashboardTabMixin',
    'InventoryTabMixin',
    'OutboundScheduledTabMixin',
    'TonbagTabMixin',
    'LogTabMixin',
    'SummaryTabMixin',
]
