"""
Reminder message generation for overdue receivables.

Scope, deliberately narrow: this module ONLY generates the wording of a
reminder message. It never decides WHETHER to send one, WHEN to escalate,
or WHETHER an invoice is disputed — those decisions stay fully deterministic
in grace_period_workflow.py and pipeline.py, and are covered by tests.

Why an LLM here specifically: tone-adjusted, context-aware phrasing is a
genuine language task an LLM is good at and a fixed template is not.

Provider-agnostic by design: this file never imports Anthropic or Gemini
directly — it asks llm_factory.get_llm_provider() for whichever one is
configured (LLM_PROVIDER=anthropic|gemini in .env). Switching providers is
a config change, not a code change. If no provider is configured, or the
call fails for any reason, this falls back to the existing deterministic
template so the pipeline still runs end-to-end with no external dependency
— same pattern as execution/razorpay_client.py's live/simulated fallback.
"""

from app.receivables.grace_period_workflow import TONE_MESSAGE_TEMPLATES, render_message
from app.receivables.llm_factory import get_llm_provider


def _template_fallback(invoice: dict, classification: dict) -> str:
    """Deterministic, always-available fallback — the original template logic."""
    return render_message(invoice, classification)


def generate_reminder_message(invoice: dict, classification: dict) -> dict:
    """
    Returns {"message": str, "source": "llm" | "template"}.

    Never called for disputed invoices or escalation paths — pipeline.py
    only calls this when action == "send_reminder", which the classifier
    already guarantees excludes disputed invoices and chronic non-payers.
    """
    provider = get_llm_provider()

    if not provider or classification["tone"] not in TONE_MESSAGE_TEMPLATES:
        return {"message": _template_fallback(invoice, classification), "source": "template"}

    prompt = (
        "Write a short, professional B2B payment reminder message.\n"
        f"Customer on-time payment rate: {float(invoice['on_time_payment_rate']) * 100:.0f}%\n"
        f"Invoice amount: INR {float(invoice['amount_inr']):,.2f}\n"
        f"Days overdue: {invoice['days_overdue']}\n"
        f"Required tone: {classification['tone'].replace('_', ' ')}\n"
        "Rules: under 60 words, no threats, do not mention this message is "
        "automated, do not invent details not given above."
    )

    try:
        text = provider.generate(prompt)
        return {"message": text, "source": "llm"}
    except Exception:
        # Any provider failure (auth, network, rate limit, empty response) —
        # fall back to the deterministic template rather than blocking the
        # pipeline.
        return {"message": _template_fallback(invoice, classification), "source": "template"}
