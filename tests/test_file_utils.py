# -*- coding: utf-8 -*-
"""
P5-14: utils.file_utils 단위 테스트
====================================
smart_path_recovery, get_recent_files, safe_file_backup (임시 디렉터리 사용)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from utils.file_utils import smart_path_recovery, get_recent_files, safe_file_backup


class TestSmartPathRecovery:
    def test_empty_returns_empty(self):
        assert smart_path_recovery("") == ""

    def test_existing_path_returns_same(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            p = f.name
        try:
            assert smart_path_recovery(p) == p
        finally:
            Path(p).unlink(missing_ok=True)

    def test_nonexistent_no_crash(self):
        out = smart_path_recovery("/nonexistent/path/file.xlsx", base_dir=Path(tempfile.gettempdir()))
        assert isinstance(out, str)


class TestGetRecentFiles:
    def test_nonexistent_dir_returns_empty(self):
        out = get_recent_files(directory="/nonexistent_dir_xyz", limit=5)
        assert out == []

    def test_temp_dir_returns_list(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("x")
            out = get_recent_files(directory=d, limit=10)
        assert isinstance(out, list)
        assert len(out) >= 0

    def test_limit_respected(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):
                (Path(d) / f"f{i}.txt").write_text("x")
            out = get_recent_files(directory=d, limit=2)
        assert len(out) <= 2


class TestSafeFileBackup:
    def test_nonexistent_returns_false(self):
        ok, msg = safe_file_backup("/nonexistent/file.txt", backup_dir=tempfile.gettempdir())
        assert ok is False
        assert isinstance(msg, str)

    def test_real_file_backs_up(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test")
            src = f.name
        backup_dir = tempfile.mkdtemp()
        try:
            ok, result = safe_file_backup(src, backup_dir=backup_dir)
            assert ok is True
            assert isinstance(result, str)
            assert Path(result).exists()
        finally:
            Path(src).unlink(missing_ok=True)
            import shutil
            shutil.rmtree(backup_dir, ignore_errors=True)
