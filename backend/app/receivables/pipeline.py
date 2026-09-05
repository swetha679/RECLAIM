"""
Full receivables pipeline: classify each overdue invoice's appropriate
grace period and tone, cap automated reminders (stopping rule: never send
more than `reminder_count` allows before mandatory human escalation), and
log every decision.
"""

import uuid

from app.receivables.grace_period_workflow import classify_receivable
from app.receivables.message_generator import generate_reminder_message
from app.escalation.escalation_manager import escalate
from app.audit import audit_logger

MAX_AUTO_REMINDERS = 3  # hard stopping rule: never auto-remind beyond this, regardless of tone


def run_receivables_batch(invoices: list) -> dict:
    batch_id = f"receivables_{uuid.uuid4().hex[:8]}"

    results = []
    total_overdue_amount = 0.0
    total_recovered_estimate_inr = 0.0
    reminders_sent = 0
    escalated_count = 0
    disputed_protected_count = 0

    for invoice in invoices:
        amount = float(invoice["amount_inr"])
        total_overdue_amount += amount
        reminder_count = int(invoice["reminder_count"])

        classification = classify_receivable(invoice)
        action = classification["action"]

        # Hard stopping rule enforced in code, independent of the
        # classification logic above — never auto-remind past the cap.
        if action == "send_reminder" and reminder_count >= MAX_AUTO_REMINDERS:
            action = "escalate_to_account_manager"
            classification["explanation"] += (
                f" (Overridden: reminder cap of {MAX_AUTO_REMINDERS} reached "
                "— escalating instead of sending another automated message.)"
            )

        entry = {
            "transaction_id": invoice["invoice_id"],
            "source_type": "overdue_receivable",
            "amount_inr": amount,
            "diagnosed_cause": classification["cause"],
            "confidence": 1.0,  # rule-based, deterministic
            "top_signals": ["on_time_payment_rate", "days_overdue", "is_disputed"],
            "explanation": classification["explanation"],
            "recommendation": f"Tone: {classification['tone']}. Action: {action}.",
            "batch_id": batch_id,
        }

        if action == "send_reminder":
            generated = generate_reminder_message(invoice, classification)
            message = generated["message"]
            # api_mode records whether the LLM actually generated this message
            # or the deterministic template fallback was used (no API key
            # configured, or the LLM call failed) — kept visible in the audit
            # trail for the same reason razorpay_client.py's live/simulated
            # mode is visible: don't silently blur a real call with a fallback.
            entry.update(
                {
                    "action_taken": "reminder_sent",
                    "action_reason": f"Grace period: {classification['grace_period_days']} days. Tone: {classification['tone']}.",
                    "api_mode": f"{generated['source']}_reminder_send",
                    "outcome": "reminder_sent",
                    "escalated": False,
                    "reminder_message": message,
                }
            )
            reminders_sent += 1
            # Conservative estimate: only count as "at risk of recovery" for
            # reporting purposes, not claimed as measured money recovered —
            # a sent reminder is a logged action, not a payment.
        elif classification["cause"] == "disputed":
            escalate(
                {"transaction_id": invoice["invoice_id"], "amount_inr": amount},
                classification["cause"],
                classification["explanation"],
                "Route to account manager to resolve dispute.",
                reason="disputed_invoice_never_auto_contacted",
            )
            entry.update(
                {
                    "action_taken": "escalated",
                    "action_reason": "Disputed invoice — never auto-contacted.",
                    "api_mode": None,
                    "outcome": "escalated",
                    "escalated": True,
                }
            )
            escalated_count += 1
            disputed_protected_count += 1
        else:
            escalate(
                {"transaction_id": invoice["invoice_id"], "amount_inr": amount},
                classification["cause"],
                classification["explanation"],
                f"Route to {'collections' if action == 'escalate_to_collections' else 'account manager'}.",
                reason=action,
            )
            entry.update(
                {
                    "action_taken": "escalated",
                    "action_reason": action,
                    "api_mode": None,
                    "outcome": "escalated",
                    "escalated": True,
                }
            )
            escalated_count += 1

        audit_logger.log_entry(entry)
        results.append(entry)

    summary = {
        "batch_id": batch_id,
        "source_type": "overdue_receivable",
        "total_invoices": len(invoices),
        "total_overdue_amount_inr": round(total_overdue_amount, 2),
        "reminders_sent": reminders_sent,
        "escalated_count": escalated_count,
        "disputed_invoices_protected": disputed_protected_count,
        "max_auto_reminders_cap": MAX_AUTO_REMINDERS,
    }

    return {"summary": summary, "results": results}
