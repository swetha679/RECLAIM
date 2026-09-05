"""
Generates a synthetic batch of failed payment transactions with ground-truth
root causes baked in (used later to evaluate the classifier's precision and
recall against a held-out set).

Cause categories, grounded in real merchant-reported failure patterns:
  - 3ds_mismatch     : international card, 3DS forced, issuer doesn't expect it
  - wallet_absent     : international, no Apple Pay / Google Pay offered
  - issuer_risk       : issuer country flagged as high risk
  - fraud_bot         : bot/fraud pattern (same address, different emails, high velocity)
  - insufficient_funds: genuine domestic decline
  - infra_error       : bank/gateway infra issue
  - unclear           : ambiguous, no dominant signal
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

INTL_COUNTRIES = ["US", "GB", "DE", "AU", "CA", "SG"]
DOMESTIC_COUNTRY = "IN"
CARD_NETWORKS = ["visa", "mastercard", "amex", "rupay"]
DEVICES = ["mobile", "desktop"]

CAUSES = [
    "3ds_mismatch",
    "wallet_absent",
    "issuer_risk",
    "fraud_bot",
    "insufficient_funds",
    "infra_error",
    "unclear",
]


def random_amount(intl: bool) -> float:
    return round(random.uniform(500, 15000) if not intl else random.uniform(800, 45000), 2)


def gen_transaction(idx: int, cause: str) -> dict:
    txn_id = f"txn_{uuid.uuid4().hex[:10]}"
    # Deliberately kept well under settings.TIME_BOX_DAYS (30): if this used
    # 0-29 days, transactions would start crossing the time-box cap within a
    # day of generation, making everything escalate for no diagnostic
    # reason. 0-15 gives real buffer, so the dataset stays valid for ~2
    # weeks after generation without needing a re-run.
    ts = (datetime.now() - timedelta(days=random.randint(0, 15),
                                      hours=random.randint(0, 23))).isoformat()

    is_international = cause in ("3ds_mismatch", "wallet_absent", "issuer_risk")
    issuer_country = random.choice(INTL_COUNTRIES) if is_international else DOMESTIC_COUNTRY
    device = random.choice(DEVICES)
    card_network = random.choice(CARD_NETWORKS)
    amount = random_amount(is_international)

    # Defaults
    three_ds_attempted = True
    wallet_offered = True
    decline_code = "technical_error"
    customer_email = f"user{idx}@example.com"
    customer_address = f"{random.randint(1,999)} Main St, City{idx % 15}"

    if cause == "3ds_mismatch":
        three_ds_attempted = True
        wallet_offered = random.choice([True, False])
        decline_code = "technical_error"

    elif cause == "wallet_absent":
        three_ds_attempted = random.choice([True, False])
        wallet_offered = False
        device = "mobile"
        decline_code = "technical_error"

    elif cause == "issuer_risk":
        three_ds_attempted = random.choice([True, False])
        wallet_offered = random.choice([True, False])
        decline_code = "risk_declined"

    elif cause == "fraud_bot":
        is_international = random.choice([True, False])
        issuer_country = random.choice(INTL_COUNTRIES + [DOMESTIC_COUNTRY])
        amount = round(random.uniform(50, 300), 2)  # small repeated test amounts
        customer_address = "42 Test Ave, City0"  # same address reused
        customer_email = f"bot{idx}_{random.randint(1,999)}@mailinator.com"
        decline_code = "fraud_suspected"
        three_ds_attempted = False
        wallet_offered = True

    elif cause == "insufficient_funds":
        is_international = False
        issuer_country = DOMESTIC_COUNTRY
        decline_code = "insufficient_funds"
        three_ds_attempted = True
        wallet_offered = True

    elif cause == "infra_error":
        decline_code = "bank_server_down"
        three_ds_attempted = random.choice([True, False])
        wallet_offered = random.choice([True, False])

    elif cause == "unclear":
        decline_code = "technical_error"
        three_ds_attempted = random.choice([True, False])
        wallet_offered = random.choice([True, False])
        is_international = random.choice([True, False])
        issuer_country = random.choice(INTL_COUNTRIES + [DOMESTIC_COUNTRY])

    return {
        "transaction_id": txn_id,
        "timestamp": ts,
        "amount_inr": amount,
        "is_international": is_international,
        "issuer_country": issuer_country,
        "card_network": card_network,
        "device": device,
        "three_ds_attempted": three_ds_attempted,
        "wallet_offered": wallet_offered,
        "decline_code": decline_code,
        "customer_email": customer_email,
        "customer_address": customer_address,
        "true_cause": cause,  # ground truth, used only for evaluation, never fed to classifier at inference time
    }


def generate(n_per_cause: int = 9) -> list:
    rows = []
    idx = 0
    for cause in CAUSES:
        for _ in range(n_per_cause):
            rows.append(gen_transaction(idx, cause))
            idx += 1
    random.shuffle(rows)
    return rows


def main():
    rows = generate(n_per_cause=9)  # 7 causes x 9 = 63 transactions
    out_path = __file__.replace("generate_synthetic_data.py", "synthetic_transactions.csv")
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic transactions to {out_path}")


if __name__ == "__main__":
    main()
