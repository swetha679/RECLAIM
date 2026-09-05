"""
Central taxonomy of failure causes. Each cause carries:
  - a human label
  - whether it's ever safe to auto-retry
  - an evidence-based expected recovery rate IF the recommended fix is applied
    (used only for internal batch-level reporting context, not shown as a
    substitute for measured outcomes)
"""

CAUSES = {
    "3ds_mismatch": {
        "label": "3D Secure / authentication mismatch",
        "description": (
            "The transaction was routed through a 3DS/OTP verification step "
            "that the customer's issuing bank does not expect or support for "
            "this card/region, causing a technical rejection rather than a "
            "genuine decline."
        ),
        "recoverable": True,
        "evidence_recovery_rate": 0.65,
        "evidence_note": (
            "Merchants who enabled non-3DS for international cards reported "
            "success rates moving from ~75-80% to the low 90s."
        ),
    },
    "wallet_absent": {
        "label": "Missing wallet payment method",
        "description": (
            "The checkout did not offer Apple Pay / Google Pay, causing "
            "friction-driven drop-off for customers expecting a one-tap "
            "payment option, particularly on mobile."
        ),
        "recoverable": True,
        "evidence_recovery_rate": 0.5,
        "evidence_note": "Enabling wallet checkout is commonly reported to lift mobile conversion.",
    },
    "issuer_risk": {
        "label": "Issuer / country risk rule",
        "description": (
            "The transaction was blocked or challenged due to a blanket risk "
            "rule on the issuing bank or country, independent of the "
            "individual customer's legitimacy."
        ),
        "recoverable": True,
        "evidence_recovery_rate": 0.35,
        "evidence_note": "Recoverable via manual routing/risk-rule review with the PSP.",
    },
    "fraud_bot": {
        "label": "Fraud / bot pattern",
        "description": (
            "The transaction matches a fraud or automated-attack pattern "
            "(e.g. repeated small charges, reused address with different "
            "emails, abnormal velocity). This is a correct decline, not lost "
            "revenue."
        ),
        "recoverable": False,
        "evidence_recovery_rate": 0.0,
        "evidence_note": "Should never be retried.",
    },
    "insufficient_funds": {
        "label": "Insufficient funds / limit reached",
        "description": (
            "A genuine decline due to the customer's available balance or "
            "card limit at the time of the attempt."
        ),
        "recoverable": True,
        "evidence_recovery_rate": 0.2,
        "evidence_note": "Low recovery via a delayed retry/payment link.",
    },
    "infra_error": {
        "label": "Bank / gateway infrastructure issue",
        "description": (
            "The failure was caused by a temporary infrastructure issue "
            "(bank server downtime, gateway timeout) unrelated to the "
            "customer or their card."
        ),
        "recoverable": True,
        "evidence_recovery_rate": 0.55,
        "evidence_note": "Often resolves on retry once infra recovers.",
    },
    "unclear": {
        "label": "Unclear — recommend manual review",
        "description": (
            "No single cause is confidently indicated by the available "
            "signals. This case should be reviewed manually rather than "
            "auto-retried."
        ),
        "recoverable": False,
        "evidence_recovery_rate": 0.0,
        "evidence_note": "Insufficient signal for automated action.",
    },
}

CAUSE_LIST = list(CAUSES.keys())
