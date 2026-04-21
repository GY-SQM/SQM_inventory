# -*- coding: utf-8 -*-
"""
tests/test_export_durability.py
================================
Export/report durability pattern tests for SQM Phase 5.

All tests inspect source code only — no Excel writing, no pandas required.
"""

import pathlib
import pytest


_EXPORT_MIXIN_PATH = (
    pathlib.Path(__file__).parent.parent
    / "engine_modules"
    / "inventory_modular"
    / "export_mixin.py"
)


def _src() -> str:
    return _EXPORT_MIXIN_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExportMixinImport:
    """Verify export_mixin module structure."""

    def test_export_mixin_importable(self):
        """ExportMixin class must be defined in export_mixin.py."""
        src = _src()
        assert "class ExportMixin" in src, (
            "ExportMixin class not found in export_mixin.py"
        )

    def test_export_mixin_has_export_to_excel(self):
        """ExportMixin must expose the export_to_excel method."""
        src = _src()
        assert "def export_to_excel(" in src, (
            "export_to_excel method not found in ExportMixin"
        )


class TestExcelWriterPattern:
    """Verify ExcelWriter is used as a context manager."""

    def test_excel_writer_uses_context_manager(self):
        """ExcelWriter must be used with 'with' statement (context manager)."""
        src = _src()
        # 'with pd.ExcelWriter' or 'with ExcelWriter'
        assert "with pd.ExcelWriter" in src or "with ExcelWriter" in src, (
            "ExcelWriter must be used as a context manager (with statement)"
        )

    def test_openpyxl_save_called_explicitly(self):
        """wb.save() must be called for direct openpyxl paths."""
        src = _src()
        assert "wb.save(" in src, (
            "wb.save() not found in export_mixin.py — "
            "direct openpyxl paths must explicitly save workbook"
        )


class TestExportPathHelper:
    """Verify export path uniqueness helper exists."""

    def test_export_path_helper_exists(self):
        """_unique_excel_path function must be defined in export_mixin.py."""
        src = _src()
        assert "def _unique_excel_path(" in src, (
            "_unique_excel_path helper not found in export_mixin.py"
        )

    def test_export_path_helper_handles_collision(self):
        """_unique_excel_path must append _1, _2 suffix on collision."""
        src = _src()
        # Check for numeric suffix pattern
        assert "_1" in src or "range(1" in src, (
            "_unique_excel_path must handle file name collisions with numeric suffix"
        )


class TestExportHandlesEmptyInventory:
    """Verify empty inventory case is handled."""

    def test_export_handles_empty_inventory(self):
        """Export must handle empty inventory gracefully (no crash on empty data)."""
        src = _src()
        # Check for empty DataFrame or empty list guards
        has_empty_df_check = "df.empty" in src or "DataFrame()" in src
        has_empty_list_check = "not inventory" in src or "if not df" in src
        assert has_empty_df_check or has_empty_list_check, (
            "export_mixin.py must handle empty inventory gracefully"
        )


class TestExportCodeQuality:
    """Verify export code quality — no bare print, no swallowed exceptions."""

    def test_no_bare_print_in_export_mixin(self):
        """export_mixin.py must not use bare print() calls (use logger)."""
        src = _src()
        lines = src.splitlines()
        bad_lines = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Allow print in string literals / comments
            if stripped.startswith("#"):
                continue
            if stripped.startswith("print(") and "logger" not in stripped:
                bad_lines.append((i, stripped))
        assert len(bad_lines) == 0, (
            f"Bare print() found in export_mixin.py at lines: {bad_lines[:5]}"
        )

    def test_export_mixin_no_bare_except_pass(self):
        """export_mixin.py must not swallow exceptions with bare 'except: pass'."""
        src = _src()
        # Look for patterns like: except:\n    pass   or   except Exception:\n    pass
        import re
        # Simplified check — bare except followed by pass
        bare_except = re.findall(r'except\s*:\s*\n\s*pass', src)
        except_exception_pass = re.findall(r'except\s+Exception\s*:\s*\n\s*pass', src)
        assert len(bare_except) == 0, (
            f"Bare 'except: pass' found {len(bare_except)} time(s) in export_mixin.py"
        )
        assert len(except_exception_pass) == 0, (
            f"'except Exception: pass' found {len(except_exception_pass)} time(s) "
            "in export_mixin.py — exceptions must not be silently swallowed"
        )

    def test_export_uses_output_path_parameter(self):
        """export_to_excel must accept and use output_path as a configurable parameter."""
        src = _src()
        assert "output_path" in src, (
            "export_mixin.py must use output_path for configurable report location"
        )
        # Verify it's a function parameter, not hardcoded
        idx = src.find("def export_to_excel(")
        assert idx >= 0
        sig = src[idx:idx + 100]
        assert "output_path" in sig, (
            "output_path must be a parameter of export_to_excel()"
        )
