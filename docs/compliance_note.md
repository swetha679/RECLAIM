# Compliance Note

This system is built to be safe to run and demo without any real financial or
customer-safety risk.

## What it does
- Reads transaction **metadata only** (amount, currency, issuer country, 3DS
  status, device, decline code, timestamp). No card numbers, CVVs, or other
  PCI-scope data are ever handled or stored.
- Uses **Razorpay TEST MODE** credentials only. If no API key is configured,
  it falls back to a seeded simulation that mimics test-mode responses so the
  full pipeline still runs end-to-end.
- Generates **payment links only** — it never charges, refunds, or moves real
  money.
- All "customer contact" in this demo is logged internally, not sent to any
  real email/phone/WhatsApp number.

## What it does NOT do
- Does not use production/live Razorpay credentials.
- Does not auto-message real customers.
- Does not retry indefinitely — hard caps enforced by `stopping_rules.py`.
- Does not attempt to retry transactions flagged as fraud/bot patterns.
- Does not claim "recovered revenue" beyond what the logged, test-mode API
  responses actually show.

## Stopping rules enforced in code
- Max retries per transaction: configurable, default 2
- Time-box: no retries attempted beyond N days from original failure
- Amount cap: transactions above a configurable threshold are flagged for
  manual approval rather than auto-retried
- Fraud exclusion: any transaction matching fraud/bot heuristics is routed
  directly to escalation, never retried
