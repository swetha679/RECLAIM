"""
Simulates what a real Razorpay `payment.failed` webhook receiver would look
like: one event arrives, gets processed immediately end-to-end (diagnose ->
rules -> execute/escalate -> audit log), and the logged result is returned
right away. No batch, no manual "Run" click — this is the real-time path.

In production this endpoint would be registered as your actual Razorpay
webhook URL and would additionally verify the webhook signature (see
Razorpay's webhook docs) before trusting the payload. That verification
step is intentionally left as a TODO here since it requires a live webhook
secret this project doesn't have.
"""

from fastapi import APIRouter, HTTPException

from app.models import TransactionIn
from app.pipeline import process_single_event
from app.diagnosis.classifier import classifier

router = APIRouter()


@router.post("/webhooks/payment-failed")
def payment_failed_webhook(txn: TransactionIn):
    """
    Accepts a single failed-transaction event (shaped like what a
    Razorpay `payment.failed` webhook payload would map onto) and processes
    it immediately, the same way a live production webhook handler would.
    """
    if classifier.model is None:
        raise HTTPException(status_code=503, detail="Classifier not trained yet.")

    entry = process_single_event(txn.model_dump())
    return {"status": "processed", "entry": entry}
