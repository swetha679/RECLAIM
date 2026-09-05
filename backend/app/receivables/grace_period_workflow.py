"""
Grace-period, tone-adaptive receivables workflow.

Directly targets the failure mode: "We spammed a client for an overdue
invoice and they quit" — caused by rigid, non-contextual automated billing
that sends the same aggressive reminder to a 3-year customer who's 2 days
late as it does to a genuine chronic non-payer.

This is deliberately rule-based, not ML — receivables decisions are legal/
relationship-sensitive, and a transparent, auditable rule set is more
appropriate (and more honest given limited data) than an opaque model here.
"""

from app.diagnosis.cause_taxonomy import CAUSES  # not used directly, kept for import consistency


def classify_receivable(invoice: dict) -> dict:
    """
    Classifies WHY an invoice is overdue and what grace period / tone is
    appropriate, based on customer history — not a flat "overdue = escalate"
    rule.
    """
    profile = invoice["customer_profile"]
    days_overdue = int(invoice["days_overdue"])
    reminder_count = int(invoice["reminder_count"])
    # invoice["is_disputed"] comes from CSV as the string "True"/"False",
    # not a real bool — bool("False") is True in Python, so a naive bool()
    # cast here would have marked every invoice as disputed. Handle both
    # real bools (already-parsed data) and CSV strings correctly.
    raw_disputed = invoice["is_disputed"]
    is_disputed = raw_disputed if isinstance(raw_disputed, bool) else str(raw_disputed).strip().lower() == "true"
    on_time_rate = float(invoice["on_time_payment_rate"])

    if is_disputed:
        return {
            "cause": "disputed",
            "grace_period_days": None,
            "tone": "none",
            "action": "escalate_to_account_manager",
            "explanation": (
                "This invoice is flagged as disputed by the customer. "
                "Automated reminders should never be sent on a disputed "
                "invoice — this needs a human account manager to resolve "
                "the dispute first."
            ),
        }

    if on_time_rate >= 0.9:
        # Excellent-standing customer — most likely a genuine, brief oversight
        grace = 14 if days_overdue < 14 else 7
        tone = "friendly_reminder"
        action = "send_reminder" if reminder_count < 2 else "escalate_to_account_manager"
        explanation = (
            f"This customer has a strong on-time payment history "
            f"({on_time_rate*100:.0f}%). This is very likely a brief, "
            f"genuine oversight rather than an ability-to-pay issue. "
            f"Recommend a friendly, low-pressure reminder with a "
            f"{grace}-day grace period before any escalation."
        )

    elif on_time_rate >= 0.7:
        grace = 7
        tone = "standard_reminder"
        action = "send_reminder" if reminder_count < 3 else "escalate_to_account_manager"
        explanation = (
            f"This customer has a generally reliable but not perfect "
            f"payment history ({on_time_rate*100:.0f}% on-time). A "
            f"standard, professional reminder is appropriate, with "
            f"escalation only after repeated reminders go unanswered."
        )

    elif on_time_rate >= 0.3:
        grace = 3
        tone = "firm_reminder"
        action = "send_reminder" if reminder_count < 2 else "escalate_to_collections"
        explanation = (
            f"This customer has a weak payment history "
            f"({on_time_rate*100:.0f}% on-time). A firmer reminder tone is "
            f"appropriate sooner, but this should still escalate to a human "
            f"collections process rather than continuing automated "
            f"reminders indefinitely."
        )

    else:
        grace = 0
        tone = "final_notice"
        action = "escalate_to_collections"
        explanation = (
            f"This customer has a chronic non-payment pattern "
            f"({on_time_rate*100:.0f}% on-time). Continuing automated "
            f"reminders is unlikely to help and risks damaging the "
            f"relationship further — recommend an immediate handoff to a "
            f"human collections process rather than more automated contact."
        )

    return {
        "cause": "genuine_delay" if on_time_rate >= 0.7 else "at_risk_payer",
        "grace_period_days": grace,
        "tone": tone,
        "action": action,
        "explanation": explanation,
    }


TONE_MESSAGE_TEMPLATES = {
    "friendly_reminder": (
        "Hi {customer_id}, just a friendly note that invoice {invoice_id} "
        "for ₹{amount} is a few days past due — no rush, just flagging it "
        "in case it slipped through. Let us know if you need anything from "
        "our side to process it."
    ),
    "standard_reminder": (
        "Hello {customer_id}, invoice {invoice_id} for ₹{amount} is now "
        "past due. Please arrange payment at your earliest convenience, or "
        "reach out if there's anything blocking it on your end."
    ),
    "firm_reminder": (
        "Hello {customer_id}, invoice {invoice_id} for ₹{amount} remains "
        "unpaid and is significantly overdue. Please settle this promptly "
        "to avoid further action."
    ),
    "final_notice": (
        "This is a final automated notice for invoice {invoice_id} "
        "(₹{amount}). This account will be handed to our collections team."
    ),
}


def render_message(invoice: dict, classification: dict) -> str:
    template = TONE_MESSAGE_TEMPLATES.get(classification["tone"])
    if not template:
        return ""
    return template.format(
        customer_id=invoice["customer_id"],
        invoice_id=invoice["invoice_id"],
        amount=f"{float(invoice['amount_inr']):,.2f}",
    )
