"""GUI tabs module
v5.5.3 P8: SearchTab, AdvancedTabs, PivotTab 제거 (죽은 코드)
v7.3.2: ScanTabMixin 추가
"""

from .allocation_tab import AllocationTabMixin
from .cargo_overview_tab import CargoOverviewTabMixin
from .dashboard_tab import DashboardTabMixin
from .inventory_tab import InventoryTabMixin
from .log_tab import LogTabMixin
from .outbound_scheduled_tab import OutboundScheduledTabMixin
from .picked_tab import PickedTabMixin
from .scan_tab import ScanTabMixin
from .sold_tab import SoldTabMixin
from .summary_tab import SummaryTabMixin
from .tonbag_tab import TonbagTabMixin

__all__ = [
    'AllocationTabMixin',
    'CargoOverviewTabMixin',
    'DashboardTabMixin',
    'InventoryTabMixin',
    'OutboundScheduledTabMixin',
    'PickedTabMixin',
    'ScanTabMixin',
    'SoldTabMixin',
    'TonbagTabMixin',
    'LogTabMixin',
    'SummaryTabMixin',
]
