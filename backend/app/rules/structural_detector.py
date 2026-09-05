"""
Detects when a batch's failure pattern looks structural / account-level
rather than a set of independently fixable transaction-level issues.

Note: this pipeline only ever receives already-failed transactions (a batch
of failures to diagnose), so "failure rate of the batch" is always 100% and
not a meaningful signal on its own. Instead, this looks for concentration
signals WITHIN the failed batch that suggest a single systemic cause rather
than many independent transaction-level issues — e.g. an overwhelming
majority of failures sharing the exact same root cause, which often points
to one underlying account/config issue rather than 63 separate problems.

This is reported as informational context on the batch summary. It does not
block individual transactions from being diagnosed and retried/escalated on
their own merits — a merchant should still see a per-transaction breakdown
even when a dominant systemic pattern exists.
"""

from collections import Counter

from app.config import settings


def is_structural_failure(causes: list) -> dict:
    """
    `causes` is the list of diagnosed causes for every transaction in the
    batch. Flags "structural" if one single cause dominates far beyond what
    you'd expect from independent, unrelated transaction-level issues.
    """
    if not causes:
        return {"is_structural": False, "dominant_cause": None, "concentration": 0.0}

    counts = Counter(causes)
    dominant_cause, dominant_count = counts.most_common(1)[0]
    concentration = dominant_count / len(causes)

    is_structural = concentration >= settings.STRUCTURAL_FAILURE_THRESHOLD

    return {
        "is_structural": is_structural,
        "dominant_cause": dominant_cause,
        "concentration": round(concentration, 3),
        "threshold": settings.STRUCTURAL_FAILURE_THRESHOLD,
        "note": (
            f"{int(concentration * 100)}% of failures share the same root "
            f"cause ('{dominant_cause}') — this concentration suggests a "
            "single systemic/config issue rather than many independent "
            "transaction-level problems. Recommend prioritizing a fix at "
            "the source (e.g. PSP configuration) over per-transaction "
            "retries."
            if is_structural
            else "No single cause dominates the batch — failures look like "
            "independent, transaction-level issues suitable for individual "
            "diagnosis and retry."
        ),
    }
