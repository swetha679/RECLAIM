"""
Wrapper around Razorpay's TEST MODE Payment Links API.

If real test-mode credentials are configured (via .env), this will make a
genuine API call to Razorpay's test environment and return the real
response. If no credentials are configured, it falls back to a seeded
simulation so the full pipeline can still be demoed end-to-end without
requiring external setup.

Either way, the caller receives a real, logged result — nothing here is
retroactively invented after the fact.
"""

import random

from app.config import settings
from app.diagnosis.cause_taxonomy import CAUSES
from app.execution.gateway_interface import PaymentGateway

try:
    import razorpay
except ImportError:  # pragma: no cover
    razorpay = None


class RazorpayTestClient(PaymentGateway):
    def __init__(self):
        self.live = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and razorpay)
        if self.live:
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        else:
            self.client = None

    def create_recovery_link(self, txn: dict, cause: str) -> dict:
        """
        Attempts to create a real test-mode payment link. Falls back to a
        seeded simulated response (weighted by the cause's evidence-based
        recovery rate) if no live credentials are configured.
        """
        if self.live:
            return self._create_real_link(txn)
        return self._simulate_link_outcome(txn, cause)

    def _create_real_link(self, txn: dict) -> dict:
        try:
            link = self.client.payment_link.create(
                {
                    "amount": int(float(txn["amount_inr"]) * 100),  # paise
                    "currency": "INR",
                    "description": f"Recovery link for {txn['transaction_id']}",
                    "customer": {"email": txn.get("customer_email", "")},
                    "notify": {"sms": False, "email": False},
                    "reminder_enable": False,
                }
            )
            return {
                "mode": "live_test_api",
                "link_id": link.get("id"),
                "status": link.get("status"),
                "short_url": link.get("short_url"),
                "raw_response": link,
            }
        except Exception as e:
            return {"mode": "live_test_api_error", "error": str(e)}

    def _simulate_link_outcome(self, txn: dict, cause: str) -> dict:
        recovery_rate = CAUSES.get(cause, {}).get("evidence_recovery_rate", 0.0)
        seed = hash(txn["transaction_id"]) % (2**32)
        rng = random.Random(seed)
        succeeded = rng.random() < recovery_rate

        return {
            "mode": "simulated_test_mode",
            "link_id": f"plink_sim_{txn['transaction_id']}",
            "status": "paid" if succeeded else "failed",
            "short_url": f"https://rzp.io/i/sim_{txn['transaction_id']}",
            "succeeded": succeeded,
            "note": (
                "No live Razorpay test credentials configured — this is a "
                "seeded simulation weighted by the diagnosed cause's "
                "evidence-based recovery rate, used so the pipeline can be "
                "demoed end-to-end."
            ),
        }


razorpay_client = RazorpayTestClient()
