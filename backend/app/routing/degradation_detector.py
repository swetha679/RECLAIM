"""
Detects hourly success-rate degradation (e.g. "cart success rate dropped to
40% today") and decides whether to shift traffic to an alternate payment
rail. This is a threshold/anomaly-detection problem, not a per-transaction
classification problem — the AI decision here is the ROUTING decision:
given a detected degradation, is it safe and net-positive to switch rails,
and does the switch actually restore success rate (measured on the next
period)?
"""

from app.config import settings


def detect_degradation(hourly_rows: list) -> list:
    """
    Flags hours where success rate falls below a threshold, indicating
    likely rail-side degradation rather than normal transaction-level
    noise (isolated failures wouldn't move an hourly aggregate this much).
    """
    findings = []
    for row in hourly_rows:
        if row["success_rate"] < settings.DEGRADATION_THRESHOLD:
            findings.append(
                {
                    **row,
                    "is_degraded": True,
                    "severity": "critical" if row["success_rate"] < 0.5 else "moderate",
                }
            )
    return findings


def decide_routing_action(finding: dict, alternate_rail: str = "bank_rail_B") -> dict:
    """
    Simple, explainable routing rule: if a hour is flagged degraded on the
    primary rail, route a defined percentage of traffic to the alternate
    rail for that window, and measure whether success rate improves.
    Bounded: only ever shifts traffic, never disables the primary rail
    outright, and only applies to the specific degraded window.
    """
    shift_pct = 70 if finding["severity"] == "critical" else 40

    return {
        "action": "shift_traffic",
        "from_rail": finding["primary_rail"],
        "to_rail": alternate_rail,
        "shift_pct": shift_pct,
        "hour": finding["hour"],
        "reason": (
            f"Success rate {finding['success_rate']*100:.1f}% at hour "
            f"{finding['hour']} is below the {settings.DEGRADATION_THRESHOLD*100:.0f}% "
            f"threshold — routing {shift_pct}% of traffic to {alternate_rail} "
            "for this window."
        ),
    }


def simulate_post_routing_success_rate(finding: dict, routing_decision: dict) -> dict:
    """
    Simulates the measured outcome of the routing switch (in a real system
    this would be the ACTUAL success rate observed after the switch, pulled
    from the next polling interval). The alternate rail is modeled as
    performing at a normal (non-degraded) rate, since the degradation is
    specific to the primary rail during that window.
    """
    import random

    seed = hash(f"{finding['hour']}_{routing_decision['to_rail']}") % (2**32)
    rng = random.Random(seed)

    shifted_attempted = int(finding["attempted"] * routing_decision["shift_pct"] / 100)
    remaining_attempted = finding["attempted"] - shifted_attempted

    # Shifted traffic goes to a healthy rail (normal success rate)
    shifted_succeeded = int(shifted_attempted * rng.uniform(0.83, 0.91))
    # Remaining traffic stays on the degraded primary rail
    remaining_succeeded = int(remaining_attempted * finding["success_rate"])

    new_total_succeeded = shifted_succeeded + remaining_succeeded
    new_success_rate = (
        new_total_succeeded / finding["attempted"] if finding["attempted"] else 0
    )

    return {
        "hour": finding["hour"],
        "original_success_rate": finding["success_rate"],
        "post_routing_success_rate": round(new_success_rate, 3),
        "additional_transactions_recovered": new_total_succeeded - finding["succeeded"],
    }
