from engine_modules.tonbag_weight_rules import calculate_tonbag_weight, build_rule_result


def test_500kg_rule():
    assert calculate_tonbag_weight(5001, 10, 1.0) == 500.0
    assert build_rule_result(5001, 10, 1.0).rule_status == 'confirmed'


def test_1000kg_rule():
    assert calculate_tonbag_weight(10001, 10, 1.0) == 1000.0
    assert build_rule_result(10001, 10, 1.0).rule_status == 'pending_confirmation'
