"""
Aggregates audit log entries into the batch-level report shown on the
dashboard: measured recovery, cause breakdown, escalation rate, and a false-
positive cost estimate (transactions we predicted recoverable but the
retry actually failed).
"""

from app.audit import audit_logger


def build_report(batch_id: str | None = None) -> dict:
    entries = audit_logger.get_all_entries(batch_id)
    if not entries:
        return {"error": "No audit entries found. Run a batch first."}

    total_amount = sum(e["amount_inr"] for e in entries)
    recovered_amount = sum(
        e["amount_inr"] for e in entries if e["outcome"] == "succeeded"
    )
    retried = [e for e in entries if e["action_taken"] == "retried"]
    failed_retries = [e for e in retried if e["outcome"] == "failed"]
    escalated = [e for e in entries if e["escalated"]]

    false_positive_cost = sum(e["amount_inr"] for e in failed_retries)

    cause_breakdown = {}
    for e in entries:
        c = e["diagnosed_cause"]
        cause_breakdown[c] = cause_breakdown.get(c, 0) + 1

    return {
        "total_transactions": len(entries),
        "total_failed_amount_inr": round(total_amount, 2),
        "total_recovered_inr": round(recovered_amount, 2),
        "recovery_rate_pct": round(100 * recovered_amount / total_amount, 2) if total_amount else 0.0,
        "retried_count": len(retried),
        "retry_success_count": len(retried) - len(failed_retries),
        "retry_failed_count": len(failed_retries),
        "escalated_count": len(escalated),
        "escalation_rate_pct": round(100 * len(escalated) / len(entries), 2) if entries else 0.0,
        "false_positive_cost_inr": round(false_positive_cost, 2),
        "cause_breakdown": cause_breakdown,
    }
