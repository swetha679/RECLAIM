"""
Full routing pipeline: detect hourly degradation, decide a bounded traffic-
shift action, simulate/measure the post-routing outcome, and log everything
through the same audit trail.
"""

import uuid

from app.routing.degradation_detector import (
    detect_degradation,
    decide_routing_action,
    simulate_post_routing_success_rate,
)
from app.audit import audit_logger


def run_routing_analysis(hourly_rows: list) -> dict:
    batch_id = f"routing_{uuid.uuid4().hex[:8]}"
    findings = detect_degradation(hourly_rows)

    results = []
    total_additional_recovered = 0

    for finding in findings:
        routing_decision = decide_routing_action(finding)
        outcome = simulate_post_routing_success_rate(finding, routing_decision)
        total_additional_recovered += outcome["additional_transactions_recovered"]

        entry = {
            "transaction_id": f"hour_{finding['hour']}",
            "source_type": "routing_degradation",
            "amount_inr": 0,  # this module operates on transaction COUNTS, not amounts
            "diagnosed_cause": f"peak_hour_degradation_{finding['severity']}",
            "confidence": 1.0,  # deterministic threshold detection
            "top_signals": ["success_rate_below_threshold", "primary_rail"],
            "explanation": (
                f"Hour {finding['hour']}:00 saw success rate drop to "
                f"{finding['success_rate']*100:.1f}% on {finding['primary_rail']} "
                f"— consistent with peak-hour bank server degradation rather "
                f"than isolated customer-side failures."
            ),
            "recommendation": routing_decision["reason"],
            "action_taken": "routed",
            "action_reason": routing_decision["reason"],
            "api_mode": "simulated_smart_routing",
            "outcome": (
                f"success_rate {finding['success_rate']*100:.1f}% -> "
                f"{outcome['post_routing_success_rate']*100:.1f}% "
                f"(+{outcome['additional_transactions_recovered']} transactions)"
            ),
            "escalated": False,
            "batch_id": batch_id,
        }
        audit_logger.log_entry(entry)
        results.append({**entry, "raw_finding": finding, "routing_decision": routing_decision, "measured_outcome": outcome})

    summary = {
        "batch_id": batch_id,
        "source_type": "routing_degradation",
        "hours_analyzed": len(hourly_rows),
        "degraded_hours_found": len(findings),
        "total_additional_transactions_recovered": total_additional_recovered,
    }

    return {"summary": summary, "results": results}
