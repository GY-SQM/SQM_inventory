# -*- coding: utf-8 -*-
"""
SQM Inventory - Outbound Handlers (Thin Wrapper)
==================================================

v8.7.4 - Refactored: 2,877 lines → 5 mixins + this thin wrapper

Outbound processing: simple outbound, allocation, picking, audit, barcode scan.

Modules:
    simple_outbound_flow.py  (HA) — _sob_* methods, _on_simple_outbound, _build_simple_outbound_ui
    audit_flow.py            (HD) — _s1_* methods, _on_s1_onestop_outbound
    allocation_flow.py       (HB) — allocation UI handlers
    picking_flow.py          (HC) — picking UI handlers
    outbound_ui_helpers.py   (HE) — revert, barcode, swap report, shared helpers
"""

from .simple_outbound_flow import SimpleOutboundFlowMixin
from .audit_flow import AuditFlowMixin
from .allocation_flow import AllocationFlowMixin
from .picking_flow import PickingFlowMixin
from .outbound_ui_helpers import OutboundUIHelpersMixin


class OutboundHandlersMixin(
    SimpleOutboundFlowMixin,
    AuditFlowMixin,
    AllocationFlowMixin,
    PickingFlowMixin,
    OutboundUIHelpersMixin,
):
    """
    Outbound handlers mixin — thin wrapper combining 5 sub-mixins.

    Mixed into SQMInventoryApp class.

    Sub-mixins:
        SimpleOutboundFlowMixin  — Simple outbound UI flow (_sob_*)
        AuditFlowMixin           — Audit flow (_s1_*)
        AllocationFlowMixin      — Allocation-related UI handlers
        PickingFlowMixin         — Picking-related UI handlers
        OutboundUIHelpersMixin   — Revert, barcode, swap, shared helpers
    """
    pass
