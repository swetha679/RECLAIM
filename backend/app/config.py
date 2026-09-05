import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")

    # Optional: used only for LLM-generated receivables reminder wording.
    # If blank / no key set for the chosen provider, falls back to the
    # deterministic template — see app/receivables/message_generator.py.
    # Never used for any decision (retry, escalate, dispute handling) —
    # those stay rule-based.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" | "gemini"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    MAX_RETRIES_PER_TRANSACTION: int = int(os.getenv("MAX_RETRIES_PER_TRANSACTION", 2))
    TIME_BOX_DAYS: int = int(os.getenv("TIME_BOX_DAYS", 30))
    AMOUNT_CAP_INR: float = float(os.getenv("AMOUNT_CAP_INR", 50000))
    STRUCTURAL_FAILURE_THRESHOLD: float = float(os.getenv("STRUCTURAL_FAILURE_THRESHOLD", 0.5))
    DEGRADATION_THRESHOLD: float = float(os.getenv("DEGRADATION_THRESHOLD", 0.6))

    DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "storage", "audit_log.db")
    ESCALATION_QUEUE_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "storage", "escalation_queue.json"
    )
    SYNTHETIC_DATA_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "synthetic_transactions.csv"
    )
    RECONCILIATION_DEBITS_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "bank_debits.csv"
    )
    RECONCILIATION_CARTS_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "checkout_carts.csv"
    )
    ROUTING_DATA_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "hourly_success_rate.csv"
    )
    CHECKOUT_SESSIONS_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "checkout_sessions.csv"
    )
    RECEIVABLES_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "data", "receivables.csv"
    )


settings = Settings()
