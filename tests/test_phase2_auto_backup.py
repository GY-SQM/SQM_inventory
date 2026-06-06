"""
Phase 2-1 스모크 테스트 — 자동 DB 백업
"""
import os, sys, shutil, sqlite3, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_fake_db(path: str):
    """테스트용 최소 SQLite DB 생성."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE inventory (id INTEGER PRIMARY KEY, lot_no TEXT)")
    con.execute("INSERT INTO inventory VALUES (1, 'TEST-LOT-001')")
    con.commit()
    con.close()


def test_auto_backup_creates_file(monkeypatch, tmp_path):
    """auto_backup() 호출 시 backup 파일이 생성되어야 한다."""
    db_file = str(tmp_path / "sqm_inventory.db")
    _make_fake_db(db_file)
    backup_dir = str(tmp_path / "backup")

    # actions 모듈의 경로 함수 패치
    import backend.api.actions as act
    monkeypatch.setattr(act, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(act, "_db_path", lambda: db_file)

    result = act.auto_backup("test_op")

    assert result != "", "백업 경로가 비어있음"
    assert os.path.exists(result), f"백업 파일 없음: {result}"
    assert "sqm_auto_" in os.path.basename(result)
    assert "test_op" in os.path.basename(result)


def test_auto_backup_content_is_valid(monkeypatch, tmp_path):
    """백업 파일이 유효한 SQLite DB여야 한다."""
    db_file = str(tmp_path / "sqm_inventory.db")
    _make_fake_db(db_file)

    import backend.api.actions as act
    monkeypatch.setattr(act, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(act, "_db_path", lambda: db_file)

    result = act.auto_backup("content_test")

    # 백업 파일에서 데이터 읽기
    con = sqlite3.connect(result)
    rows = con.execute("SELECT lot_no FROM inventory").fetchall()
    con.close()
    assert rows == [("TEST-LOT-001",)], "백업 내용이 원본과 다름"


def test_auto_backup_does_not_crash_on_missing_db(monkeypatch, tmp_path):
    """DB 파일이 없어도 예외 없이 빈 문자열 반환해야 한다."""
    import backend.api.actions as act
    monkeypatch.setattr(act, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(act, "_db_path", lambda: str(tmp_path / "nonexistent.db"))

    result = act.auto_backup("no_db")
    assert result == "", "DB 없을 때 빈 문자열이어야 함"


def test_auto_backup_limits_file_count(monkeypatch, tmp_path):
    """자동 백업이 50개 초과 시 오래된 파일을 삭제해야 한다."""
    db_file = str(tmp_path / "sqm_inventory.db")
    _make_fake_db(db_file)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    # 50개 더미 자동 백업 파일 생성
    import time
    for i in range(50):
        f = backup_dir / f"sqm_auto_old_{i:03d}_20260101_000000.db"
        f.write_bytes(b"dummy")
        # 생성 시간에 차이를 주기 위해 mtime 조작
        os.utime(str(f), (i, i))

    import backend.api.actions as act
    monkeypatch.setattr(act, "_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(act, "_db_path", lambda: db_file)

    act.auto_backup("limit_test")

    auto_files = [f for f in os.listdir(str(backup_dir))
                  if f.startswith("sqm_auto_") and f.endswith(".db")]
    assert len(auto_files) <= 50, f"자동 백업 50개 초과: {len(auto_files)}개"


def test_max_backups_is_30():
    """MAX_BACKUPS 상수가 30 이상이어야 한다 (Phase 2-1 변경)."""
    import backend.api.actions as act
    assert act.MAX_BACKUPS >= 30, f"MAX_BACKUPS가 너무 작음: {act.MAX_BACKUPS}"


def test_auto_backup_function_exists():
    """auto_backup 함수가 actions 모듈에 존재해야 한다."""
    import backend.api.actions as act
    assert callable(getattr(act, "auto_backup", None)), \
        "auto_backup 함수가 actions.py에 없음"


def test_inbound_has_auto_backup_call():
    """inbound.py에 auto_backup 호출이 있어야 한다."""
    path = os.path.join(os.path.dirname(__file__), "..", "backend", "api", "inbound.py")
    with open(path, encoding="utf-8", errors="ignore") as f:
        code = f.read()
    assert "auto_backup" in code, "inbound.py에 auto_backup 호출 없음"


def test_outbound_has_auto_backup_call():
    """outbound_api.py에 auto_backup 호출이 있어야 한다."""
    path = os.path.join(os.path.dirname(__file__), "..", "backend", "api", "outbound_api.py")
    with open(path, encoding="utf-8", errors="ignore") as f:
        code = f.read()
    assert "auto_backup" in code, "outbound_api.py에 auto_backup 호출 없음"
