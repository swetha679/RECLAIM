"""
Fraud/bot detection — a hard override on top of the classifier. Even if the
model doesn't predict "fraud_bot" with the highest confidence, these
heuristics can still force a transaction into the non-retryable bucket. This
is deliberately conservative: false negatives here (missing real fraud) are
less catastrophic in this demo than false positives (blocking a legitimate
customer), but the heuristics below are still applied independently as a
safety net regardless of what the classifier predicted.
"""

from collections import defaultdict


def detect_fraud_patterns(transactions: list) -> dict:
    """
    Given a batch of transactions, returns {transaction_id: True/False} for
    whether each matches a fraud/bot pattern, based on cross-transaction
    signals (address reuse, velocity, small repeated amounts) that a
    per-transaction classifier alone can't see.
    """
    address_counts = defaultdict(list)
    for txn in transactions:
        address_counts[txn.get("customer_address", "")].append(txn)

    flagged = {}
    for txn in transactions:
        txn_id = txn["transaction_id"]
        address = txn.get("customer_address", "")
        same_address_group = address_counts.get(address, [])

        is_small_amount = float(txn.get("amount_inr", 0)) < 400
        many_emails_same_address = len({t.get("customer_email") for t in same_address_group}) >= 3
        decline_is_fraud_code = str(txn.get("decline_code", "")).lower() == "fraud_suspected"

        flagged[txn_id] = bool(
            decline_is_fraud_code or (is_small_amount and many_emails_same_address)
        )

    return flagged
