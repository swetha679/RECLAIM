"""
Escalation queue — anything that shouldn't be (or couldn't be) auto-retried
lands here with its diagnosis attached, so a human can act on it with full
context instead of just seeing "failed again".
"""

import json
import os
from datetime import datetime

from app.config import settings


def _load_queue() -> list:
    if not os.path.exists(settings.ESCALATION_QUEUE_PATH):
        return []
    with open(settings.ESCALATION_QUEUE_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_queue(queue: list):
    os.makedirs(os.path.dirname(settings.ESCALATION_QUEUE_PATH), exist_ok=True)
    with open(settings.ESCALATION_QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2, default=str)


def escalate(txn: dict, cause: str, explanation: str, recommendation: str, reason: str):
    queue = _load_queue()
    queue.append(
        {
            "transaction_id": txn["transaction_id"],
            "amount_inr": txn.get("amount_inr"),
            "cause": cause,
            "explanation": explanation,
            "recommendation": recommendation,
            "escalation_reason": reason,
            "escalated_at": datetime.now().isoformat(),
        }
    )
    _save_queue(queue)


def get_escalations() -> list:
    return _load_queue()


def clear_escalations():
    _save_queue([])
