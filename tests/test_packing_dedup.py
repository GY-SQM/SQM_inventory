from features.ai.gemini_parser import _make_lot_fingerprint


def test_fingerprint_normalizes_container_format():
    a = {"lot_no": "1125081447", "container_no": "FFAU-535500-6", "net_weight_kg": "5.001"}
    b = {"lot_no": "1125081447", "container_no": "ffau5355006", "net_weight_kg": "5001"}
    assert _make_lot_fingerprint(a) == _make_lot_fingerprint(b)


def test_first_page_duplicate_row_detected_by_fingerprint():
    seen = set()
    row = {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": "5001"}
    fp = _make_lot_fingerprint(row)
    assert fp not in seen
    seen.add(fp)
    assert fp in seen


def test_same_lot_different_weight_not_duplicate():
    a = {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": "5001"}
    b = {"lot_no": "1125081447", "container_no": "FFAU5355006", "net_weight_kg": "5131.25"}
    assert _make_lot_fingerprint(a) != _make_lot_fingerprint(b)


def test_empty_lot_number_still_deduplicated_by_container_weight():
    a = {"lot_no": "", "container_no": "MSCU1234567", "net_weight_kg": "5001"}
    b = {"lot_no": "", "container_no": "MSCU-1234567", "net_weight_kg": "5.001"}
    assert _make_lot_fingerprint(a) == _make_lot_fingerprint(b)
