"""
FraudLens — Policy Engine Tests
"""
import pytest
from policy.rules import (
    check_rule_R1, check_rule_R2, check_rule_R3,
    check_rule_R5, check_rule_R6, get_approval_route, requires_SAR
)

def test_r1_fires_on_high_probability():
    assert check_rule_R1(0.86, 3) == True
    assert check_rule_R1(0.84, 3) == False   # below threshold
    assert check_rule_R1(0.90, 1) == False   # not enough evidence

def test_r2_fires_on_denial():
    assert check_rule_R2("denied") == True
    assert check_rule_R2("confirmed") == False
    assert check_rule_R2("no_response") == False

def test_r3_fires_on_monitoring_threshold():
    assert check_rule_R3(0.30) == True
    assert check_rule_R3(0.29) == False

def test_r5_card_testing():
    txn_seq = [{"amount": 1.0}, {"amount": 1.5}, {"amount": 2.0}, {"amount": 542.0}]
    assert check_rule_R5(txn_seq) == True
    assert check_rule_R5([{"amount": 542.0}]) == False

def test_r6_high_exposure():
    assert check_rule_R6(10_000.0) == True
    assert check_rule_R6(9_999.0) == False

def test_approval_routes():
    assert get_approval_route("ALLOW_TRANSACTION", 0) == "auto"
    assert get_approval_route("BLOCK_TRANSACTION", 100) == "L1"
    assert get_approval_route("BLOCK_ACCOUNT", 100) == "L2"
    assert get_approval_route("FILE_REPORT", 100) == "L2"

def test_sar_requirements():
    assert requires_SAR("fraud", 15_000, False, False) == True   # high exposure fraud
    assert requires_SAR("cleared", 500, False, False) == False    # cleared case
    assert requires_SAR("fraud", 500, True, True) == True         # shared device + connected fraud
