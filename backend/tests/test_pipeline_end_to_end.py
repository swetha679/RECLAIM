import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from app.diagnosis.classifier import classifier
from app.audit import audit_logger
from app.config import settings
from app.pipeline import run_batch


def setup_module(module):
    audit_logger.init_db()
    classifier.fit_from_csv(settings.SYNTHETIC_DATA_PATH)


def test_full_batch_pipeline_runs_and_produces_valid_summary():
    df = pd.read_csv(settings.SYNTHETIC_DATA_PATH)
    transactions = df.to_dict(orient="records")

    result = run_batch(transactions)
    summary = result["summary"]

    assert summary["total_transactions"] == len(transactions)
    assert summary["total_recovered_inr"] >= 0
    assert summary["retried_count"] + summary["escalated_count"] == summary["total_transactions"]
    assert len(result["results"]) == len(transactions)

    for entry in result["results"]:
        assert entry["action_taken"] in ("retried", "escalated")
        assert entry["diagnosed_cause"] is not None
        assert entry["explanation"]
        assert entry["recommendation"]


def test_fraud_transactions_never_marked_succeeded():
    df = pd.read_csv(settings.SYNTHETIC_DATA_PATH)
    transactions = df.to_dict(orient="records")
    result = run_batch(transactions)

    for entry in result["results"]:
        if entry["diagnosed_cause"] == "fraud_bot":
            assert entry["outcome"] != "succeeded"


def test_process_single_event_returns_valid_entry():
    """
    Sanity check for the live-webhook path (process_single_event): given
    ONE transaction (not a batch), it should diagnose, act, and log exactly
    the same shape of entry as the batch path does.
    """
    from app.pipeline import process_single_event

    live_txn = {
        "transaction_id": "test_live_event_1",
        "timestamp": "2026-08-31T10:00:00",
        "amount_inr": 12000,
        "is_international": True,
        "issuer_country": "US",
        "card_network": "visa",
        "device": "mobile",
        "three_ds_attempted": True,
        "wallet_offered": False,
        "decline_code": "technical_error",
        "customer_email": "live@example.com",
        "customer_address": "1 Live St",
    }

    entry = process_single_event(live_txn)

    assert entry["transaction_id"] == "test_live_event_1"
    assert entry["batch_id"] == "live_webhook"
    assert entry["diagnosed_cause"] is not None
    assert entry["action_taken"] in ("retried", "escalated")
    assert entry["explanation"]


def test_process_single_event_fraud_decline_code_never_retried():
    from app.pipeline import process_single_event

    fraud_txn = {
        "transaction_id": "test_live_fraud_1",
        "timestamp": "2026-08-31T10:00:00",
        "amount_inr": 200,
        "is_international": False,
        "issuer_country": "IN",
        "card_network": "visa",
        "device": "mobile",
        "three_ds_attempted": False,
        "wallet_offered": True,
        "decline_code": "fraud_suspected",
        "customer_email": "fraud@example.com",
        "customer_address": "1 Fraud St",
    }

    entry = process_single_event(fraud_txn)
    assert entry["action_taken"] == "escalated"
    assert entry["outcome"] != "succeeded"
