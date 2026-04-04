"""B08 Stage-Gate: query_mixin canonical query helpers smoke test.

Verifies:
1. py_compile passes on query_mixin.py
2. Key canonical query methods exist on QueryMixin
"""
import py_compile
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUERY_MIXIN_PATH = ROOT / "engine_modules" / "inventory_modular" / "query_mixin.py"


def test_query_mixin_compiles():
    """query_mixin.py must pass py_compile without errors."""
    py_compile.compile(str(QUERY_MIXIN_PATH), doraise=True)


def test_canonical_methods_exist():
    """All canonical query helper methods must exist on QueryMixin."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("query_mixin", str(QUERY_MIXIN_PATH))
    mod = importlib.util.module_from_spec(spec)
    # Provide stub for import dependency
    import sys
    if "engine_modules.constants" not in sys.modules:
        import types
        stub = types.ModuleType("engine_modules.constants")
        stub.STATUS_AVAILABLE = "AVAILABLE"
        stub.STATUS_RESERVED = "RESERVED"
        sys.modules["engine_modules.constants"] = stub
    spec.loader.exec_module(mod)
    cls = mod.QueryMixin

    # Phase-3 existing helpers
    phase3_methods = [
        "count_tonbags",
        "count_tonbags_by_status",
        "get_inventory_map",
        "get_tonbag_map",
        "get_inventory_row",
        "inventory_lot_exists",
    ]

    # B08 new canonical helpers
    b08_methods = [
        "count_alloc_plans",
        "get_alloc_reserved_lots",
        "get_tonbag_by_uid",
    ]

    all_methods = phase3_methods + b08_methods
    missing = [m for m in all_methods if not hasattr(cls, m)]
    assert not missing, f"Missing canonical methods on QueryMixin: {missing}"


def test_b08_method_signatures():
    """B08 helpers must accept expected parameters."""
    import importlib.util, inspect, sys, types
    if "engine_modules.constants" not in sys.modules:
        stub = types.ModuleType("engine_modules.constants")
        stub.STATUS_AVAILABLE = "AVAILABLE"
        stub.STATUS_RESERVED = "RESERVED"
        sys.modules["engine_modules.constants"] = stub
    spec = importlib.util.spec_from_file_location("query_mixin", str(QUERY_MIXIN_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = mod.QueryMixin

    # count_alloc_plans(self, status, lot_no, tonbag_id_null)
    sig = inspect.signature(cls.count_alloc_plans)
    params = list(sig.parameters.keys())
    assert "status" in params
    assert "lot_no" in params
    assert "tonbag_id_null" in params

    # get_alloc_reserved_lots(self)
    sig2 = inspect.signature(cls.get_alloc_reserved_lots)
    assert len(sig2.parameters) == 1  # only self

    # get_tonbag_by_uid(self, uid)
    sig3 = inspect.signature(cls.get_tonbag_by_uid)
    assert "uid" in list(sig3.parameters.keys())
