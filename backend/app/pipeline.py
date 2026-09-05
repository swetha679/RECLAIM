"""
Full pipeline orchestration:

  raw transaction
      -> diagnose (classify + explain + recommend)
      -> fraud filter (batch-level override)
      -> structural check (batch-level)
      -> if recoverable & not fraud & not structural:
             stopping rules -> execute (test-mode) -> log outcome
         else:
             escalate -> log
      -> audit log every step regardless of path
"""

import uuid

from app.diagnosis.classifier import classifier
from app.diagnosis.explainability import Explainer
from app.diagnosis.playbook import get_recommendation
from app.rules.fraud_filter import detect_fraud_patterns
from app.rules.structural_detector import is_structural_failure
from app.execution.retry_engine import attempt_recovery
from app.escalation.escalation_manager import escalate
from app.audit import audit_logger
from app.audit.audit_logger import count_prior_attempts

explainer = Explainer(classifier)


def run_batch(transactions: list) -> dict:
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"

    fraud_flags = detect_fraud_patterns(transactions)

    # First pass: diagnose every transaction so we have the full cause list
    # available for the structural (concentration) check before deciding
    # per-transaction actions.
    predictions = {}
    for txn in transactions:
        prediction = classifier.predict_one(txn)
        explanation = explainer.explain(txn, prediction)
        predictions[txn["transaction_id"]] = explanation

    structural = is_structural_failure([p["cause"] for p in predictions.values()])

    results = []
    total_recovered_inr = 0.0
    total_failed_amount_inr = 0.0
    escalated_count = 0
    retried_count = 0
    succeeded_count = 0

    for txn in transactions:
        amount = float(txn.get("amount_inr", 0))
        total_failed_amount_inr += amount

        explanation = predictions[txn["transaction_id"]]
        cause = explanation["cause"]
        recommendation = get_recommendation(cause)

        is_fraud = fraud_flags.get(txn["transaction_id"], False)
        cause_for_action = "fraud_bot" if is_fraud else cause

        entry = {
            "transaction_id": txn["transaction_id"],
            "source_type": "payment_failure",
            "amount_inr": amount,
            "diagnosed_cause": cause,
            "confidence": explanation["confidence"],
            "top_signals": explanation["top_signals"],
            "explanation": explanation["explanation"],
            "recommendation": recommendation,
            "batch_id": batch_id,
        }

        # Per-transaction routing is always based on that transaction's own
        # diagnosed cause + fraud flag. The structural check above is
        # informational context surfaced in the batch summary (e.g. "68% of
        # failures share one root cause — fix the source"), it does not
        # override individual transaction handling.
        prior_attempts = count_prior_attempts(txn["transaction_id"], "payment_failure")
        entry["retry_count"] = prior_attempts
        recovery = attempt_recovery(txn, cause_for_action, is_fraud, retry_count=prior_attempts)

        if recovery["action"] == "retried":
            retried_count += 1
            outcome = recovery["outcome"]
            api_mode = recovery["api_result"].get("mode") if recovery["api_result"] else None

            if outcome == "succeeded":
                succeeded_count += 1
                total_recovered_inr += amount

            entry.update(
                {
                    "action_taken": "retried",
                    "action_reason": recovery["reason"],
                    "api_mode": api_mode,
                    "outcome": outcome,
                    "escalated": False,
                }
            )
        else:
            escalate(
                txn,
                cause,
                explanation["explanation"],
                recommendation,
                reason=recovery["reason"],
            )
            entry.update(
                {
                    "action_taken": "escalated",
                    "action_reason": recovery["reason"],
                    "api_mode": None,
                    "outcome": "escalated",
                    "escalated": True,
                }
            )
            escalated_count += 1

        audit_logger.log_entry(entry)
        results.append(entry)

    cause_breakdown = {}
    for r in results:
        c = r["diagnosed_cause"]
        cause_breakdown[c] = cause_breakdown.get(c, 0) + 1

    summary = {
        "batch_id": batch_id,
        "source_type": "payment_failure",
        "total_transactions": len(transactions),
        "total_failed_amount_inr": round(total_failed_amount_inr, 2),
        "total_recovered_inr": round(total_recovered_inr, 2),
        "recovery_rate_pct": round(
            100 * total_recovered_inr / total_failed_amount_inr, 2
        ) if total_failed_amount_inr else 0.0,
        "retried_count": retried_count,
        "succeeded_count": succeeded_count,
        "escalated_count": escalated_count,
        "cause_breakdown": cause_breakdown,
        "structural_check": structural,
    }

    return {"summary": summary, "results": results}


def process_single_event(txn: dict) -> dict:
    """
    Processes exactly ONE transaction through the same diagnose -> rules ->
    execute/escalate -> audit-log path as run_batch(), but immediately, as
    a real webhook handler would. This is what a live Razorpay
    `payment.failed` webhook delivery would trigger in production — one
    event in, one logged decision out, no waiting for a batch.

    Note: the batch-level fraud heuristics that look for cross-transaction
    patterns (e.g. same address reused across many orders) can't apply to a
    single isolated event — only the single-transaction fraud signal
    (explicit fraud decline code) is checked here. This is a known,
    documented limitation of real-time single-event processing versus
    batch reconciliation, not an oversight.
    """
    prediction = classifier.predict_one(txn)
    explanation = explainer.explain(txn, prediction)
    cause = explanation["cause"]
    recommendation = get_recommendation(cause)

    # Single-event fraud check: only the signals available on this one
    # transaction (decline code), not cross-transaction velocity/address
    # reuse, which requires a batch/window of events to detect.
    is_fraud = str(txn.get("decline_code", "")).lower() == "fraud_suspected"
    cause_for_action = "fraud_bot" if is_fraud else cause

    amount = float(txn.get("amount_inr", 0))
    event_id = f"live_{uuid.uuid4().hex[:8]}"

    entry = {
        "transaction_id": txn.get("transaction_id", event_id),
        "source_type": "payment_failure",
        "amount_inr": amount,
        "diagnosed_cause": cause,
        "confidence": explanation["confidence"],
        "top_signals": explanation["top_signals"],
        "explanation": explanation["explanation"],
        "recommendation": recommendation,
        "batch_id": "live_webhook",
    }

    prior_attempts = count_prior_attempts(txn["transaction_id"], "payment_failure")
    entry["retry_count"] = prior_attempts
    recovery = attempt_recovery(txn, cause_for_action, is_fraud, retry_count=prior_attempts)

    if recovery["action"] == "retried":
        outcome = recovery["outcome"]
        api_mode = recovery["api_result"].get("mode") if recovery["api_result"] else None
        entry.update(
            {
                "action_taken": "retried",
                "action_reason": recovery["reason"],
                "api_mode": api_mode,
                "outcome": outcome,
                "escalated": False,
            }
        )
    else:
        escalate(txn, cause, explanation["explanation"], recommendation, reason=recovery["reason"])
        entry.update(
            {
                "action_taken": "escalated",
                "action_reason": recovery["reason"],
                "api_mode": None,
                "outcome": "escalated",
                "escalated": True,
            }
        )

    audit_logger.log_entry(entry)
    return entry
