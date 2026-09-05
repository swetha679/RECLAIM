"""
Live webhook demo.

Simulates real Razorpay `payment.failed` webhook deliveries arriving one at
a time, with a random delay between each — the way they would in
production — and POSTs each one to the running backend's webhook endpoint.

Run this while the backend is running (uvicorn main:app --port 8000) and
watch the terminal output, or watch the frontend's "Live Feed" tab update
in near-real-time as each event lands.

Usage:
    python scripts/simulate_live_webhook.py
    python scripts/simulate_live_webhook.py --count 10 --min-delay 1 --max-delay 4
"""

import argparse
import random
import time
import uuid
from datetime import datetime

import requests

WEBHOOK_URL = "http://localhost:8000/api/webhooks/payment-failed"

INTL_COUNTRIES = ["US", "GB", "DE", "AU", "CA", "SG"]
CARD_NETWORKS = ["visa", "mastercard", "amex", "rupay"]


def random_event() -> dict:
    """Generates one realistic-looking live failed-payment event."""
    scenario = random.choice(
        ["3ds", "wallet", "risk", "fraud", "funds", "infra", "unclear"]
    )
    is_intl = scenario in ("3ds", "wallet", "risk")

    base = {
        "transaction_id": f"live_txn_{uuid.uuid4().hex[:10]}",
        "timestamp": datetime.now().isoformat(),
        "amount_inr": round(random.uniform(500, 30000), 2),
        "is_international": is_intl,
        "issuer_country": random.choice(INTL_COUNTRIES) if is_intl else "IN",
        "card_network": random.choice(CARD_NETWORKS),
        "device": random.choice(["mobile", "desktop"]),
        "three_ds_attempted": True,
        "wallet_offered": True,
        "decline_code": "technical_error",
        "customer_email": f"live_customer_{random.randint(1,9999)}@example.com",
        "customer_address": f"{random.randint(1,999)} Live Demo St",
    }

    if scenario == "3ds":
        base["decline_code"] = "technical_error"
    elif scenario == "wallet":
        base["wallet_offered"] = False
        base["device"] = "mobile"
    elif scenario == "risk":
        base["decline_code"] = "risk_declined"
    elif scenario == "fraud":
        base["decline_code"] = "fraud_suspected"
        base["amount_inr"] = round(random.uniform(50, 300), 2)
        base["is_international"] = False
        base["issuer_country"] = "IN"
    elif scenario == "funds":
        base["decline_code"] = "insufficient_funds"
        base["is_international"] = False
        base["issuer_country"] = "IN"
    elif scenario == "infra":
        base["decline_code"] = "bank_server_down"

    return base


def main():
    parser = argparse.ArgumentParser(description="Simulate live payment-failed webhook events.")
    parser.add_argument("--count", type=int, default=8, help="Number of events to send")
    parser.add_argument("--min-delay", type=float, default=1.5, help="Min seconds between events")
    parser.add_argument("--max-delay", type=float, default=4.0, help="Max seconds between events")
    args = parser.parse_args()

    print(f"Sending {args.count} live webhook events to {WEBHOOK_URL}")
    print("(Make sure the backend is running: uvicorn main:app --port 8000)\n")

    for i in range(args.count):
        event = random_event()
        try:
            resp = requests.post(WEBHOOK_URL, json=event, timeout=10)
            resp.raise_for_status()
            result = resp.json()["entry"]
            print(
                f"[{i+1}/{args.count}] {event['transaction_id']} "
                f"(₹{event['amount_inr']:.2f}) -> cause={result['diagnosed_cause']} "
                f"action={result['action_taken']} outcome={result['outcome']}"
            )
        except requests.exceptions.RequestException as e:
            print(f"[{i+1}/{args.count}] FAILED to send event: {e}")

        if i < args.count - 1:
            delay = random.uniform(args.min_delay, args.max_delay)
            time.sleep(delay)

    print("\nDone. Check the frontend's Live Feed tab or GET /api/audit-trail?source_type=payment_failure")


if __name__ == "__main__":
    main()
