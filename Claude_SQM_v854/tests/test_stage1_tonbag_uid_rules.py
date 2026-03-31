from engine_modules.tonbag_patch_rules import normalize_tonbag_no, build_tonbag_uid

def test_normal_tonbag_no():
    assert normalize_tonbag_no(1) == "001"
    assert normalize_tonbag_no("10") == "010"

def test_sample_tonbag_no():
    assert normalize_tonbag_no(0, is_sample=True) == "S00"

def test_uid_build():
    assert build_tonbag_uid("1125072147", "001") == "1125072147-001"
    assert build_tonbag_uid("1125072147", "S00", is_sample=True) == "1125072147-S00"
