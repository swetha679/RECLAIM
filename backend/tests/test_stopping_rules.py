import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rules.stopping_rules import check_stopping_rules
from app.config import settings


def _base_txn(**overrides):
    txn = {
        "transaction_id": "t1",
        "amount_inr": 1000,
        "timestamp": datetime.now().isoformat(),
    }
    txn.update(overrides)
    return txn


def test_blocks_non_recoverable_cause():
    result = check_stopping_rules(_base_txn(), retry_count=0, cause="fraud_bot", recoverable=False)
    assert result["allowed"] is False


def test_allows_recoverable_within_limits():
    result = check_stopping_rules(_base_txn(), retry_count=0, cause="3ds_mismatch", recoverable=True)
    assert result["allowed"] is True


def test_blocks_after_max_retries():
    result = check_stopping_rules(
        _base_txn(), retry_count=settings.MAX_RETRIES_PER_TRANSACTION, cause="3ds_mismatch", recoverable=True
    )
    assert result["allowed"] is False
    assert "Max retries" in result["reason"]


def test_blocks_above_amount_cap():
    txn = _base_txn(amount_inr=settings.AMOUNT_CAP_INR + 1)
    result = check_stopping_rules(txn, retry_count=0, cause="3ds_mismatch", recoverable=True)
    assert result["allowed"] is False
    assert "exceeds" in result["reason"]


def test_blocks_outside_time_box():
    old_ts = (datetime.now() - timedelta(days=settings.TIME_BOX_DAYS + 5)).isoformat()
    txn = _base_txn(timestamp=old_ts)
    result = check_stopping_rules(txn, retry_count=0, cause="3ds_mismatch", recoverable=True)
    assert result["allowed"] is False
    assert "time-box" in result["reason"]
