"""
"Money deducted, order not placed" detector.

Matches the bank-debit feed against the checkout-cart feed using a
cron/polling-style reconciliation pass (run this on a schedule against real
feeds in production; here it runs once per batch call).

A debit with no matching FULFILLED cart is a "phantom payment" — the bank
took the money, but the merchant's order system never got (or acted on) the
success webhook, usually because of a gateway degradation causing a webhook
timeout. This is a pure detection + bounded-recovery problem, no ML
classifier needed — it's a deterministic reconciliation, which is the
correct (and more honest) tool for this specific problem.
"""


def reconcile(debits: list, carts: list) -> list:
    """
    Returns a list of phantom-payment findings: debits that have no matching
    fulfilled cart. Each finding includes enough context to drive a bounded
    recovery action (auto-fulfill the order, or refund if fulfillment isn't
    possible).
    """
    carts_by_order = {c["order_id"]: c for c in carts}

    findings = []
    for debit in debits:
        order_id = debit["order_id"]
        cart = carts_by_order.get(order_id)

        if cart is not None and cart.get("cart_status") == "fulfilled":
            continue  # correctly matched, nothing to do

        # Phantom payment: either no cart row exists at all, or it exists
        # but is stuck in a non-fulfilled state (e.g. "pending").
        cart_status = cart.get("cart_status") if cart else "no_cart_record"

        findings.append(
            {
                "transaction_id": debit["debit_id"],
                "order_id": order_id,
                "amount_inr": debit["amount_inr"],
                "timestamp": debit["timestamp"],
                "cart_status": cart_status,
                "customer_email": cart.get("customer_email") if cart else None,
            }
        )

    return findings


def decide_recovery_action(finding: dict) -> str:
    """
    Deterministic decision on what a bounded recovery action should be:
      - if the cart still exists in a pending state -> attempt auto-fulfillment
        (the order data exists, just needs to be marked paid and processed)
      - if there's no cart record at all -> safer to refund, since we have
        no record of what was ordered, only that money was taken
    """
    if finding["cart_status"] == "pending":
        return "auto_fulfill_order"
    return "initiate_refund"
