"""
Checkout abandonment pipeline: diagnose why each session dropped off, send
a bounded cart-recovery link (reusing the same test-mode execution client),
capped and logged the same way as every other module.
"""

import uuid

from app.checkout.abandonment_classifier import classify_abandonment
from app.execution.gateway_factory import get_gateway
from app.rules.stopping_rules import check_stopping_rules
from app.audit import audit_logger
from app.escalation.escalation_manager import escalate

_gateway = get_gateway()  # "razorpay" today — see gateway_factory.py

CAUSE_RECOVERY_RATE = {
    "price_hesitation": "wallet_absent",  # reuse evidence-recovery-rate bucket for simulation only
    "payment_method_missing": "wallet_absent",
    "distraction_dropoff": "insufficient_funds",
    "currency_confusion": "issuer_risk",
}


def run_checkout_batch(sessions: list) -> dict:
    batch_id = f"checkout_{uuid.uuid4().hex[:8]}"

    results = []
    total_cart_value = 0.0
    total_recovered_inr = 0.0
    sent_count = 0
    escalated_count = 0

    for session in sessions:
        amount = float(session["cart_value_inr"])
        total_cart_value += amount

        classification = classify_abandonment(session)
        cause = classification["cause"]

        stopping_check = check_stopping_rules(
            {"amount_inr": amount, "timestamp": session["timestamp"]},
            retry_count=0,
            cause=cause,
            recoverable=True,
        )

        entry = {
            "transaction_id": session["session_id"],
            "source_type": "checkout_abandonment",
            "amount_inr": amount,
            "diagnosed_cause": cause,
            "confidence": 1.0,  # rule-based
            "top_signals": ["dwell_seconds", "cart_value_inr", "wallet_shown", "device"],
            "explanation": classification["explanation"],
            "recommendation": classification["recommendation"],
            "batch_id": batch_id,
        }

        if not stopping_check["allowed"]:
            escalate(
                {"transaction_id": session["session_id"], "amount_inr": amount},
                cause,
                classification["explanation"],
                classification["recommendation"],
                reason=stopping_check["reason"],
            )
            entry.update(
                {
                    "action_taken": "escalated",
                    "action_reason": stopping_check["reason"],
                    "api_mode": None,
                    "outcome": "escalated",
                    "escalated": True,
                }
            )
            escalated_count += 1
        else:
            proxy_cause = CAUSE_RECOVERY_RATE.get(cause, "insufficient_funds")
            api_result = _gateway.create_recovery_link(
                {"transaction_id": session["session_id"], "amount_inr": amount},
                cause=proxy_cause,
            )
            outcome = "succeeded" if api_result.get("succeeded") else "failed"
            if outcome == "succeeded":
                total_recovered_inr += amount

            entry.update(
                {
                    "action_taken": "recovery_link_sent",
                    "action_reason": stopping_check["reason"],
                    "api_mode": api_result.get("mode"),
                    "outcome": outcome,
                    "escalated": False,
                }
            )
            sent_count += 1

        audit_logger.log_entry(entry)
        results.append(entry)

    cause_breakdown = {}
    for r in results:
        c = r["diagnosed_cause"]
        cause_breakdown[c] = cause_breakdown.get(c, 0) + 1

    summary = {
        "batch_id": batch_id,
        "source_type": "checkout_abandonment",
        "total_sessions": len(sessions),
        "total_cart_value_inr": round(total_cart_value, 2),
        "total_recovered_inr": round(total_recovered_inr, 2),
        "recovery_rate_pct": round(100 * total_recovered_inr / total_cart_value, 2) if total_cart_value else 0.0,
        "recovery_links_sent": sent_count,
        "escalated_count": escalated_count,
        "cause_breakdown": cause_breakdown,
    }

    return {"summary": summary, "results": results}
