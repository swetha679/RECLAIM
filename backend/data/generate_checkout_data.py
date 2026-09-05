"""
Generates synthetic checkout-abandonment sessions: customers who reached
checkout but never completed a payment attempt at all (distinct from
payment_failure, where an attempt was made and declined).
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(33)

CAUSES = ["price_hesitation", "payment_method_missing", "currency_confusion", "distraction_dropoff"]


def gen_session(idx: int, cause: str) -> dict:
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    ts = (datetime.now() - timedelta(hours=random.randint(1, 200))).isoformat()

    cart_value = round(random.uniform(500, 30000), 2)
    dwell_seconds = random.randint(10, 400)
    returning_visitor = random.choice([True, False])
    device = random.choice(["mobile", "desktop"])
    wallet_shown = True
    currency_shown = "INR"

    if cause == "price_hesitation":
        dwell_seconds = random.randint(120, 400)
        cart_value = round(random.uniform(8000, 30000), 2)

    elif cause == "payment_method_missing":
        wallet_shown = False
        device = "mobile"
        dwell_seconds = random.randint(20, 90)

    elif cause == "currency_confusion":
        currency_shown = "INR"
        # simulate an international visitor seeing INR unexpectedly
        dwell_seconds = random.randint(15, 60)

    elif cause == "distraction_dropoff":
        dwell_seconds = random.randint(5, 25)
        cart_value = round(random.uniform(500, 5000), 2)

    return {
        "session_id": session_id,
        "timestamp": ts,
        "cart_value_inr": cart_value,
        "dwell_seconds": dwell_seconds,
        "returning_visitor": returning_visitor,
        "device": device,
        "wallet_shown": wallet_shown,
        "currency_shown": currency_shown,
        "customer_email": f"cart{idx}@example.com",
        "true_cause": cause,
    }


def generate(n_per_cause: int = 10) -> list:
    rows = []
    idx = 0
    for cause in CAUSES:
        for _ in range(n_per_cause):
            rows.append(gen_session(idx, cause))
            idx += 1
    random.shuffle(rows)
    return rows


def main():
    rows = generate()
    out_path = __file__.replace("generate_checkout_data.py", "checkout_sessions.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic checkout-abandonment sessions to {out_path}")


if __name__ == "__main__":
    main()
