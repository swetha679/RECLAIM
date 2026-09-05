"""
Orchestrates a single retry attempt: checks stopping rules, calls the
Razorpay test-mode client if allowed, and returns a structured result ready
for audit logging.
"""

from app.execution.gateway_factory import get_gateway
from app.rules.stopping_rules import check_stopping_rules
from app.diagnosis.cause_taxonomy import CAUSES

_gateway = get_gateway()  # "razorpay" today — see gateway_factory.py


def attempt_recovery(txn: dict, cause: str, is_fraud: bool, retry_count: int = 0) -> dict:
    recoverable = CAUSES.get(cause, {}).get("recoverable", False) and not is_fraud

    stopping_check = check_stopping_rules(txn, retry_count, cause, recoverable)

    if not stopping_check["allowed"]:
        return {
            "action": "not_retried",
            "reason": stopping_check["reason"],
            "api_result": None,
        }

    api_result = _gateway.create_recovery_link(txn, cause)

    outcome = "unknown"
    if api_result.get("mode") == "simulated_test_mode":
        outcome = "succeeded" if api_result.get("succeeded") else "failed"
    elif api_result.get("status") == "paid":
        outcome = "succeeded"
    elif api_result.get("mode") == "live_test_api_error":
        outcome = "api_error"
    else:
        outcome = "pending"

    return {
        "action": "retried",
        "reason": stopping_check["reason"],
        "api_result": api_result,
        "outcome": outcome,
    }
