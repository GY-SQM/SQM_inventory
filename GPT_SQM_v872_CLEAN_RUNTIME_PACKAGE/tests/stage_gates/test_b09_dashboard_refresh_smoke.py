# -*- coding: utf-8 -*-
"""
B09 Stage Gate: Dashboard Refresh Smoke Test
=============================================
Verify:
1. py_compile passes on target files (main_app, refresh_mixin, dashboard_tab)
2. refresh_mixin has core refresh methods
3. No duplicate startup dashboard refresh (B09 fix applied)
"""
import py_compile
import pathlib
import inspect
import importlib


ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestB09PyCompile:
    """py_compile passes on all three target files."""

    def test_main_app_compiles(self):
        py_compile.compile(
            str(ROOT / "gui_app_modular" / "main_app.py"), doraise=True
        )

    def test_refresh_mixin_compiles(self):
        py_compile.compile(
            str(ROOT / "gui_app_modular" / "mixins" / "refresh_mixin.py"), doraise=True
        )

    def test_dashboard_tab_compiles(self):
        py_compile.compile(
            str(ROOT / "gui_app_modular" / "tabs" / "dashboard_tab.py"), doraise=True
        )


class TestB09RefreshMixinMethods:
    """refresh_mixin contains core refresh coordination methods."""

    def _load_source(self):
        return (ROOT / "gui_app_modular" / "mixins" / "refresh_mixin.py").read_text(
            encoding="utf-8"
        )

    def test_has_refresh_main_tabs(self):
        src = self._load_source()
        assert "def _refresh_main_tabs" in src

    def test_has_deferred_refresh(self):
        src = self._load_source()
        assert "def _deferred_refresh_main_tabs" in src

    def test_has_safe_refresh(self):
        src = self._load_source()
        assert "def _safe_refresh" in src

    def test_has_refresh_bus(self):
        src = self._load_source()
        assert "def refresh_bus" in src

    def test_has_dirty_tab_system(self):
        src = self._load_source()
        assert "def _mark_tabs_dirty" in src
        assert "def _refresh_dirty_current_tab" in src


class TestB09StartupDashboardDedup:
    """Verify B09 fix: no duplicate _refresh_dashboard at startup."""

    def test_no_800ms_dashboard_refresh_at_startup(self):
        """The after(800, _refresh_dashboard_safe) line should be removed."""
        src = (ROOT / "gui_app_modular" / "main_app.py").read_text(encoding="utf-8")
        assert "self.root.after(800, _refresh_dashboard_safe)" not in src

    def test_set_dashboard_tab_still_exists(self):
        """The after(0, _set_dashboard_tab) must remain."""
        src = (ROOT / "gui_app_modular" / "main_app.py").read_text(encoding="utf-8")
        assert "_set_dashboard_tab" in src

    def test_startup_stats_no_duplicate_inventory_refresh(self):
        """_startup_stats_refresh should NOT call _refresh_inventory (B09 fix)."""
        src = (ROOT / "gui_app_modular" / "main_app.py").read_text(encoding="utf-8")
        # Find the _startup_stats_refresh method body
        idx = src.index("def _startup_stats_refresh")
        # Get next method boundary (next 'def ' at same indent)
        next_def = src.index("\n    def ", idx + 1)
        method_body = src[idx:next_def]
        # Check for actual call (not just mention in comments/docstrings)
        # The call pattern is: self._refresh_inventory()
        assert "self._refresh_inventory()" not in method_body
