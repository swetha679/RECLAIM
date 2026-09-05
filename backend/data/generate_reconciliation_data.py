"""
Generates two synthetic feeds that a real merchant would have separately:
  - bank_debits.csv    : money that actually left the customer's account
                         (from the bank/card network side)
  - checkout_carts.csv : orders the merchant's system believes completed
                         (from the webhook/order side)

The mismatch between these two feeds is exactly the "money deducted, order
not placed" problem: a webhook timeout during a gateway degradation means
the bank successfully debited the customer, but the merchant's system never
received (or processed) the success webhook, so the cart/order is left
"unfulfilled" even though payment genuinely happened.

Ground truth (`true_status`) is attached to debits for evaluation:
  - matched        : debit correctly matched to a fulfilled order (normal case)
  - phantom_payment : debit exists, but NO matching fulfilled order — money
                      taken, order not placed (the bug to detect)
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(7)


def generate(n_matched: int = 40, n_phantom: int = 12):
    debits = []
    carts = []

    # Normal, correctly matched cases
    for i in range(n_matched):
        order_id = f"order_{uuid.uuid4().hex[:8]}"
        amount = round(random.uniform(300, 20000), 2)
        ts = (datetime.now() - timedelta(hours=random.randint(1, 300))).isoformat()

        debits.append(
            {
                "debit_id": f"debit_{uuid.uuid4().hex[:8]}",
                "order_id": order_id,
                "amount_inr": amount,
                "timestamp": ts,
                "true_status": "matched",
            }
        )
        carts.append(
            {
                "order_id": order_id,
                "cart_status": "fulfilled",
                "amount_inr": amount,
                "timestamp": ts,
                "customer_email": f"user{i}@example.com",
            }
        )

    # Phantom payment cases: debit happened, but no fulfilled order exists
    # (simulating a webhook timeout during gateway degradation — the cart
    # stays "pending"/"abandoned" in the merchant's system forever, even
    # though the bank successfully took the money).
    for i in range(n_phantom):
        order_id = f"order_{uuid.uuid4().hex[:8]}"
        amount = round(random.uniform(300, 20000), 2)
        ts = (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat()

        debits.append(
            {
                "debit_id": f"debit_{uuid.uuid4().hex[:8]}",
                "order_id": order_id,
                "amount_inr": amount,
                "timestamp": ts,
                "true_status": "phantom_payment",
            }
        )
        # NOTE: intentionally NOT adding a corresponding fulfilled cart row,
        # OR adding one still stuck in "pending" — this is the mismatch.
        if random.random() < 0.5:
            carts.append(
                {
                    "order_id": order_id,
                    "cart_status": "pending",  # webhook never arrived
                    "amount_inr": amount,
                    "timestamp": ts,
                    "customer_email": f"phantom{i}@example.com",
                }
            )
        # else: no cart row at all — even worse case, order was never created

    random.shuffle(debits)
    return debits, carts


def main():
    debits, carts = generate()
    base = __file__.replace("generate_reconciliation_data.py", "")

    with open(base + "bank_debits.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(debits[0].keys()))
        writer.writeheader()
        writer.writerows(debits)

    with open(base + "checkout_carts.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(carts[0].keys()))
        writer.writeheader()
        writer.writerows(carts)

    print(f"Wrote {len(debits)} bank debits and {len(carts)} checkout carts.")


if __name__ == "__main__":
    main()
