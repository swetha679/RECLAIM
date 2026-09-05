import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rules.fraud_filter import detect_fraud_patterns


def test_flags_explicit_fraud_decline_code():
    transactions = [
        {
            "transaction_id": "t1",
            "amount_inr": 500,
            "decline_code": "fraud_suspected",
            "customer_address": "1 Main St",
            "customer_email": "a@example.com",
        }
    ]
    flags = detect_fraud_patterns(transactions)
    assert flags["t1"] is True


def test_flags_address_reuse_pattern():
    transactions = [
        {
            "transaction_id": f"t{i}",
            "amount_inr": 100,
            "decline_code": "technical_error",
            "customer_address": "42 Test Ave",
            "customer_email": f"bot{i}@mailinator.com",
        }
        for i in range(4)
    ]
    flags = detect_fraud_patterns(transactions)
    assert all(flags[t["transaction_id"]] for t in transactions)


def test_does_not_flag_normal_transaction():
    transactions = [
        {
            "transaction_id": "t1",
            "amount_inr": 5000,
            "decline_code": "technical_error",
            "customer_address": "10 Regular Rd",
            "customer_email": "real.customer@example.com",
        }
    ]
    flags = detect_fraud_patterns(transactions)
    assert flags["t1"] is False


def test_fraud_never_gets_retried_end_to_end():
    """Sanity check: a fraud-flagged transaction, when passed to
    attempt_recovery as fraud_bot cause, must never be retried."""
    from app.execution.retry_engine import attempt_recovery

    txn = {
        "transaction_id": "t_fraud",
        "amount_inr": 200,
        "timestamp": "2026-08-25T00:00:00",
    }
    result = attempt_recovery(txn, cause="fraud_bot", is_fraud=True, retry_count=0)
    assert result["action"] == "not_retried"
