"""
Hard-enforced stopping rules for the execution/retry layer. These are checked
before every single retry attempt — nothing bypasses them.
"""

from datetime import datetime, timedelta

from app.config import settings


def check_stopping_rules(txn: dict, retry_count: int, cause: str, recoverable: bool) -> dict:
    """
    Returns {"allowed": bool, "reason": str} — whether a retry is permitted
    right now for this transaction.
    """
    if not recoverable:
        return {"allowed": False, "reason": "Cause is not recoverable (e.g. fraud/unclear)."}

    if retry_count >= settings.MAX_RETRIES_PER_TRANSACTION:
        return {
            "allowed": False,
            "reason": f"Max retries ({settings.MAX_RETRIES_PER_TRANSACTION}) reached.",
        }

    amount = float(txn.get("amount_inr", 0))
    if amount > settings.AMOUNT_CAP_INR:
        return {
            "allowed": False,
            "reason": f"Amount ₹{amount} exceeds auto-retry cap of ₹{settings.AMOUNT_CAP_INR}; needs manual approval.",
        }

    try:
        txn_time = datetime.fromisoformat(txn.get("timestamp"))
        if datetime.now() - txn_time > timedelta(days=settings.TIME_BOX_DAYS):
            return {
                "allowed": False,
                "reason": f"Transaction older than time-box of {settings.TIME_BOX_DAYS} days.",
            }
    except (ValueError, TypeError):
        pass  # if timestamp can't be parsed, don't block on this rule

    return {"allowed": True, "reason": "Within all stopping rule limits."}
