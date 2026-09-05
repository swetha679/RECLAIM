# Bar Mapping

## Track scope
> *"Build an agent that detects revenue at risk, determines the right
> intervention, and executes a bounded recovery workflow: from payment
> failures and checkout abandonment to overdue receivables."*

> *"Don't just identify the problem. Show measured money recovered across a
> batch, with compliant escalation, stopping rules, and an audit trail."*

## Coverage by revenue-loss type

The track names three revenue-loss modes explicitly, plus two specific
example failure patterns ("money deducted, order not placed" and peak-hour
bank degradation / smart routing). This build covers all five, each as its
own module, all sharing one execution/escalation/audit engine:

| Revenue-loss type | Module | Diagnosis approach |
|---|---|---|
| Payment failures | `app/diagnosis/` + `app/pipeline.py` | Trained RandomForest classifier + SHAP explainability |
| Checkout abandonment | `app/checkout/` | Rule-based classifier (dwell time, cart value, wallet availability) |
| "Money deducted, order not placed" | `app/reconciliation/` | Deterministic cron/polling-style reconciliation between bank-debit feed and checkout-cart feed |
| Peak-hour bank degradation | `app/routing/` | Hourly success-rate threshold detection + bounded traffic-shift decision |
| Overdue receivables | `app/receivables/` | Rule-based grace-period + tone-adaptive workflow keyed to customer payment history |

## How each bar clause is satisfied, per module

### "Don't just identify the problem"
Every module's pipeline (`*/pipeline.py`) always continues past diagnosis
into a rule check and an action/escalation decision — diagnosis alone is
never the end state anywhere in the system.

### "Determines the right intervention"
- Payment failures: cause-specific playbook (`diagnosis/playbook.py`)
- Checkout abandonment: cause-specific recovery link vs. low-priority nudge
- Phantom payments: auto-fulfill vs. refund, decided deterministically by
  whether a pending cart record exists (`reconciliation/phantom_payment_detector.py`)
- Routing: bounded traffic-shift percentage scaled to degradation severity
  (`routing/degradation_detector.py`)
- Receivables: grace period length + message tone selected per customer's
  on-time payment rate — not a single rigid rule for every customer
  (`receivables/grace_period_workflow.py`), directly targeting the "we
  spammed a client and they quit" failure mode

### "Measured money recovered across a batch"
Every module logs a real, executed (test-mode/simulated) outcome per item
and aggregates it into `total_recovered_inr` in its summary — not a
projected estimate. `metrics/batch_report.py` also computes false-positive
cost for the payment-failure module.

### "Compliant escalation"
Every module routes unresolved, high-risk, or out-of-policy cases to
`escalation/escalation_manager.py` with the diagnosis attached. Notably:
receivables never auto-contacts disputed invoices (routes straight to a
human account manager); reconciliation refunds rather than guesses when no
order record exists at all. See `docs/compliance_note.md` for what every
module is explicitly prohibited from doing.

### "Stopping rules"
- Payment failures & checkout abandonment: `rules/stopping_rules.py` — max
  retries, amount cap, time-box, fraud exclusion, all enforced in code
- Receivables: hard cap of 3 auto-reminders (`receivables/pipeline.py`,
  `MAX_AUTO_REMINDERS`), independent of the tone/grace-period logic
- Reconciliation & routing: bounded by construction — reconciliation never
  retries a payment (money already moved, only order-status/refund actions
  apply), routing only ever shifts a percentage of traffic, never disables
  a rail outright

### "Audit trail"
One shared `audit_log` table (`audit/audit_logger.py`) across all five
modules, tagged by `source_type`, queryable via `GET /api/audit-trail`
(filterable by module and/or batch). Every row captures: diagnosed cause,
confidence, signals used, action taken, API result, outcome, timestamp.

## Live (real-time) path for payment failures

`app/routes/webhook.py` exposes `POST /api/webhooks/payment-failed`, which
processes ONE transaction immediately through the same diagnose -> rules ->
execute/escalate -> audit-log logic as the batch path
(`app/pipeline.py:process_single_event`), simulating what a real Razorpay
`payment.failed` webhook delivery would trigger in production. This proves
the pipeline is event-driven-capable, not just batch-file-driven.

`backend/scripts/simulate_live_webhook.py` sends realistic events to this
endpoint one at a time with randomized delays, and the frontend's "Live
Feed" tab polls the audit trail every 2 seconds to show them arriving in
near-real-time — demonstrating the intended production shape (webhook for
payment failures, cron/polling for the other four modules, as described
below) without requiring a live Razorpay merchant account.

Known, documented limitation: the batch-level fraud heuristic that looks
for cross-transaction patterns (e.g. the same address reused across many
orders) cannot apply to a single isolated live event — only the
single-transaction signal (explicit fraud decline code) is checked in the
live path. This is called out directly in `process_single_event`'s
docstring rather than left as a silent gap.

## Honesty notes (worth saying out loud in the pitch)
- Only the payment-failure module uses a trained ML classifier with SHAP
  explainability — the other four are deliberately rule-based/deterministic,
  because their signal sets are smaller and the decisions are more
  relationship- or compliance-sensitive (receivables, refunds) where a
  transparent, auditable rule is more appropriate than an opaque model.
  This is a considered design choice, not uniform depth for its own sake.
- `metrics/evaluation.py` (precision/recall against held-out ground truth)
  only applies to the payment-failure classifier, since it's the only
  module making a probabilistic prediction rather than a deterministic
  rule-based decision.
