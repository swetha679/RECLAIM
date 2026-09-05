import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.receivables.message_generator import generate_reminder_message
from app.receivables.grace_period_workflow import classify_receivable


def _invoice(**overrides):
    inv = {
        "invoice_id": "inv_1",
        "customer_id": "cust_1",
        "customer_profile": "good",
        "on_time_payment_rate": 0.95,
        "amount_inr": 25000,
        "days_overdue": 5,
        "reminder_count": 0,
        "is_disputed": False,
    }
    inv.update(overrides)
    return inv


def test_falls_back_to_template_without_api_key():
    # In this test environment no ANTHROPIC_API_KEY is configured, so this
    # must deterministically use the template path, not fail or hang on
    # a network call.
    invoice = _invoice()
    classification = classify_receivable(invoice)
    result = generate_reminder_message(invoice, classification)
    assert result["source"] == "template"
    assert invoice["invoice_id"] in result["message"]


def test_message_generation_never_called_for_disputed():
    # Guard at the call-site level (pipeline.py only calls this for
    # action == "send_reminder"), reconfirmed here: a disputed invoice's
    # classification action is never "send_reminder".
    invoice = _invoice(is_disputed=True)
    classification = classify_receivable(invoice)
    assert classification["action"] != "send_reminder"


def test_fallback_message_is_non_empty_for_every_tone():
    for rate in [0.95, 0.8, 0.5, 0.1]:
        invoice = _invoice(on_time_payment_rate=rate)
        classification = classify_receivable(invoice)
        if classification["action"] == "send_reminder":
            result = generate_reminder_message(invoice, classification)
            assert result["message"]


def test_llm_factory_returns_none_with_no_keys_configured():
    # In this test environment neither ANTHROPIC_API_KEY nor GEMINI_API_KEY
    # is set, so the factory must return None (meaning: use the template),
    # never raise.
    from app.receivables.llm_factory import get_llm_provider

    assert get_llm_provider() is None


def test_message_generator_is_provider_agnostic():
    # message_generator.py must not IMPORT any specific provider SDK
    # directly — it should only depend on llm_factory. (Mentioning provider
    # names in comments/docstrings is fine and expected.)
    import ast
    import app.receivables.message_generator as mg
    import inspect

    tree = ast.parse(inspect.getsource(mg))
    imported_modules = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    ] + [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]

    joined = " ".join(m for m in imported_modules if m)
    assert "anthropic" not in joined.lower()
    assert "generativeai" not in joined.lower()
