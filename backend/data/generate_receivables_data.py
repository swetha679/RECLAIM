"""
Generates synthetic overdue B2B invoices with customer payment history, so
the grace-period/tone-adaptive workflow has realistic variety: long-term
good-standing customers who are briefly late vs. genuinely chronic
non-payers vs. customers actively disputing the invoice.
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(21)

CUSTOMER_PROFILES = [
    # (label, on_time_payment_rate, weight)
    ("excellent", 0.97, 0.35),
    ("good", 0.85, 0.35),
    ("poor", 0.45, 0.20),
    ("chronic_non_payer", 0.15, 0.10),
]


def _pick_profile():
    r = random.random()
    cumulative = 0
    for label, rate, weight in CUSTOMER_PROFILES:
        cumulative += weight
        if r <= cumulative:
            return label, rate
    return CUSTOMER_PROFILES[-1][0], CUSTOMER_PROFILES[-1][1]


def generate(n: int = 40):
    rows = []
    for i in range(n):
        profile_label, on_time_rate = _pick_profile()
        days_overdue = random.randint(1, 95)
        amount = round(random.uniform(15000, 400000), 2)
        reminder_count = random.randint(0, 4)
        is_disputed = random.random() < (0.15 if profile_label != "chronic_non_payer" else 0.05)

        due_date = (datetime.now() - timedelta(days=days_overdue)).isoformat()

        rows.append(
            {
                "invoice_id": f"inv_{uuid.uuid4().hex[:8]}",
                "customer_id": f"cust_{i % 25}",
                "customer_profile": profile_label,
                "on_time_payment_rate": on_time_rate,
                "amount_inr": amount,
                "days_overdue": days_overdue,
                "due_date": due_date,
                "reminder_count": reminder_count,
                "is_disputed": is_disputed,
            }
        )
    return rows


def main():
    rows = generate()
    out_path = __file__.replace("generate_receivables_data.py", "receivables.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic overdue invoices to {out_path}")


if __name__ == "__main__":
    main()
