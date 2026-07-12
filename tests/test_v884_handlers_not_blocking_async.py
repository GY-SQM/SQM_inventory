# -*- coding: utf-8 -*-
"""[감사] 무거운(파일파싱·엑셀·PDF·엔진쓰기) 업로드 핸들러가 'async def' 가 아님을 고정.

async def 핸들러가 내부에서 동기 블로킹 작업을 하면 FastAPI 이벤트루프를 통째로
막아 앱 전체가 얼어붙는다(사용자 증상 '단계 넘어갈 때 멈춤'). 이 핸들러들은 일반
def 로 두어 FastAPI 가 threadpool 에서 돌리게 한다. 회귀로 다시 async 가 붙는 것을 차단.
"""
import asyncio
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# (모듈경로, 함수명) — async→def 로 전환한 블로킹 핸들러들
_SYNC_HANDLERS = [
    ("backend.api.inbound", "bulk_import_excel"),
    ("backend.api.inbound", "return_inbound_excel"),
    ("backend.api.inbound", "template_from_pdf"),
    ("backend.api.inbound", "templates_from_excel"),
    ("backend.api.inbound", "inbound_invoice"),
    ("backend.api.inbound", "inbound_bl"),
    ("backend.api.inbound", "inbound_do"),
    ("backend.api.outbound_api", "picking_list_pdf"),
    ("backend.api.outbound_api", "picking_import_excel"),
    ("backend.api.outbound_api", "proof_upload"),
    ("backend.api.outbound_api", "onestop_scan_parse"),
    ("backend.api.outbound_api", "barcode_confirm_sold"),
    ("backend.api.outbound_api", "picking_sample_sold"),
    ("backend.api.allocation_api", "bulk_import_allocation"),
    ("backend.api.allocation_api", "template_upload"),
    ("backend.api.actions2", "sales_order_upload"),
    ("backend.api.tonbag_api", "location_upload"),
    ("backend.api.ai_pl_parser", "parse_pl"),
    ("backend.api.inventory_api", "scan_bulk_upload"),
    ("backend.api.outbound_picking", "parse_picking_list"),
    ("backend.api.template_ai_api", "generate_template_from_docs"),
    ("backend.api.location_map_api", "preview_location_map"),
    ("backend.api.location_map_api", "commit_location_map"),
    ("backend.api.location_map_api", "_save_upload"),
    ("backend.api.refresh_excel_api", "refresh_excel_status"),
    ("backend.api.optional", "excel_export_all"),
]


@pytest.mark.parametrize("modpath,fname", _SYNC_HANDLERS)
def test_blocking_handler_is_sync_def(modpath, fname):
    mod = importlib.import_module(modpath)
    fn = getattr(mod, fname)
    assert not asyncio.iscoroutinefunction(fn), (
        f"{modpath}.{fname} 이 async def 로 되돌아갔습니다 — 블로킹 시 이벤트루프 정지. "
        f"동기 def 로 두어 threadpool 에서 돌게 해야 합니다."
    )


def test_carrier_autodetect_stays_async_but_offloads():
    """settings.auto_detect_carrier_rules 는 await request.form() 때문에 async 유지하되
    블로킹 작업은 run_in_threadpool 로 오프로드한다(소스에 존재 확인)."""
    import inspect
    from backend.api import settings
    assert asyncio.iscoroutinefunction(settings.auto_detect_carrier_rules)
    src = inspect.getsource(settings.auto_detect_carrier_rules)
    assert "run_in_threadpool" in src, "블로킹 작업이 스레드풀로 오프로드되어야 함"
