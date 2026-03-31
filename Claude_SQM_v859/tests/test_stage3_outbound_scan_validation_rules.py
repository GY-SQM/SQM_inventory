from core.outbound_scan_validation_patch import is_scannable_status, is_duplicate_scan


def test_scannable_status_available():
    r = is_scannable_status("AVAILABLE")
    assert r.success is True


def test_scannable_status_shipped_blocked():
    r = is_scannable_status("SHIPPED")
    assert r.success is False
    assert r.code == "STATUS_SCAN_BLOCKED"


def test_duplicate_scan_warning():
    r = is_duplicate_scan({"LOT-001"}, "LOT-001")
    assert r.success is False
    assert r.level == "WARNING"
