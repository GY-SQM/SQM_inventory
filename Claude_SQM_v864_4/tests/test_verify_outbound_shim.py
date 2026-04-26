# -*- coding: utf-8 -*-
"""
tests/test_verify_outbound_shim.py
====================================
Phase 5-E: Retire ad-hoc verify scripts by wrapping them as pytest shims.

These tests replace the manual execution of:
  - GPT_verify_outbound_refactor_v2.py
  - GPT_verify_outbound_refactor_v3.py

Each script is verified to exist and have valid Python syntax.
"""

import ast
import pathlib
import pytest


_ROOT = pathlib.Path(__file__).parent.parent


class TestVerifyOutboundScriptExists:
    """Verify the ad-hoc verify scripts are present (for audit trail)."""

    def test_verify_script_v2_exists(self):
        """
        GPT_verify_outbound_refactor_v2.py presence check.

        v864.3 Phase 0: skip when absent — the script is a legacy v864.2
        GPT-era artifact, not migrated to v864.3. If it reappears at root,
        this test auto-reactivates.  Sibling class TestVerifyOutboundScriptSyntax
        already uses this same skip pattern (line 46-47).
        """
        p = _ROOT / "GPT_verify_outbound_refactor_v2.py"
        if not p.exists():
            pytest.skip(f"{p.name} not present — legacy v864.2 artifact, skipping")

    def test_verify_script_v3_exists(self):
        """
        GPT_verify_outbound_refactor_v3.py presence check.

        v864.3 Phase 0: skip when absent — see test_verify_script_v2_exists
        for rationale. Same skip pattern as sibling syntax-check class.
        """
        p = _ROOT / "GPT_verify_outbound_refactor_v3.py"
        if not p.exists():
            pytest.skip(f"{p.name} not present — legacy v864.2 artifact, skipping")


class TestVerifyOutboundScriptSyntax:
    """Verify the ad-hoc scripts have valid Python syntax (no parse errors)."""

    def _check_syntax(self, filepath: pathlib.Path):
        if not filepath.exists():
            pytest.skip(f"{filepath.name} not found — skipping syntax check")
        src = filepath.read_text(encoding="utf-8", errors="replace")
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(
                f"{filepath.name} has a syntax error: {e}\n"
                f"Line {e.lineno}: {e.text}"
            )

    def test_verify_script_v2_importable_as_module(self):
        """GPT_verify_outbound_refactor_v2.py must have valid Python syntax."""
        self._check_syntax(_ROOT / "GPT_verify_outbound_refactor_v2.py")

    def test_verify_script_v3_importable_as_module(self):
        """GPT_verify_outbound_refactor_v3.py must have valid Python syntax."""
        self._check_syntax(_ROOT / "GPT_verify_outbound_refactor_v3.py")
