"""
Maps each diagnosed cause to a specific, plain-language recommended action.
This is what turns a diagnosis into something a merchant can actually act on.
"""

PLAYBOOK = {
    "3ds_mismatch": (
        "Request non-3DS enablement for international cards from your "
        "payment service provider, or generate an alternate payment link "
        "routed without a forced 3DS challenge."
    ),
    "wallet_absent": (
        "Enable Apple Pay / Google Pay at checkout, particularly for mobile "
        "international customers."
    ),
    "issuer_risk": (
        "Flag this issuer/country pattern with your PSP for manual risk-rule "
        "review — legitimate customers may be getting blocked by a blanket "
        "rule."
    ),
    "fraud_bot": (
        "Do not retry. Report this pattern to your fraud/risk team — it "
        "matches known bot/fraud characteristics."
    ),
    "insufficient_funds": (
        "Send a payment retry link after a short delay (e.g. next payday "
        "cycle) rather than an immediate retry."
    ),
    "infra_error": (
        "Retry once infra recovers — this is not a customer-side issue."
    ),
    "unclear": (
        "Send for manual review — signals are not strong enough for an "
        "automated recommendation."
    ),
}


def get_recommendation(cause: str) -> str:
    return PLAYBOOK.get(cause, "No specific recommendation available — recommend manual review.")
