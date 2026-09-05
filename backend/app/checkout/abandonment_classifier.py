"""
Rule-based checkout-abandonment classifier. Kept rule-based (not ML) since
the signal set is small and the rules are directly interpretable — an
honest choice given limited session-level features, consistent with how
this system treats receivables (also rule-based) versus payment failures
(where a trained classifier + SHAP genuinely earns its complexity).
"""


def classify_abandonment(session: dict) -> dict:
    dwell = int(session["dwell_seconds"])
    cart_value = float(session["cart_value_inr"])
    wallet_shown = bool(session["wallet_shown"]) if not isinstance(session["wallet_shown"], str) else session["wallet_shown"].lower() == "true"
    device = session["device"]

    if dwell > 100 and cart_value > 7000:
        cause = "price_hesitation"
        explanation = (
            f"Customer spent {dwell}s on checkout with a high cart value "
            f"(₹{cart_value:,.0f}) — pattern consistent with price hesitation "
            f"rather than a technical or UX blocker."
        )
        recommendation = "Send a cart-recovery link, optionally with a small time-limited discount."

    elif not wallet_shown and device == "mobile":
        cause = "payment_method_missing"
        explanation = (
            "Mobile session with no wallet payment method (Apple Pay/Google "
            "Pay) shown — likely friction from having to manually enter card "
            "details on mobile."
        )
        recommendation = "Enable wallet checkout for mobile sessions; send a cart-recovery link with wallet option highlighted."

    elif dwell < 30 and cart_value < 6000:
        cause = "distraction_dropoff"
        explanation = (
            f"Very short session ({dwell}s) with a modest cart value — "
            f"likely a casual browse/distraction rather than a blocked "
            f"purchase intent."
        )
        recommendation = "Low-priority: a single gentle reminder link is appropriate, no urgency."

    else:
        cause = "currency_confusion"
        explanation = (
            "Session pattern doesn't clearly fit price hesitation or "
            "distraction — possible localization/currency friction for the "
            "visitor."
        )
        recommendation = "Review whether checkout is showing the right currency/locale for this visitor segment."

    return {"cause": cause, "explanation": explanation, "recommendation": recommendation}
