# Revenue Recovery Agent

Detects revenue at risk across five modes — payment failures, checkout
abandonment, "money deducted but no order placed" (phantom payments),
peak-hour bank/gateway degradation, and overdue receivables — diagnoses the
cause in plain language, executes a bounded recovery action, and logs
everything to a shared, queryable audit trail.

## Problem

Revenue loss rarely happens in one clean step. A payment degrades, a
checkout gets abandoned, a webhook times out mid-payment, peak-hour traffic
overwhelms a bank rail, or an invoice goes overdue. Merchants typically see
only the symptom ("payment failed", "cart success rate dropped", "invoice
overdue") with no diagnosis of the actual cause and no bounded, auditable
way to act on it.

## What this agent does, per module

1. **Payment failures** — classifies the true root cause of a failed
   transaction (3DS/auth mismatch, wallet absence, issuer/country risk,
   fraud/bot pattern, insufficient funds, infra error) using a trained
   classifier with SHAP-based plain-language explanations, then executes a
   bounded test-mode retry where safe.
2. **Checkout abandonment** — diagnoses why a session dropped off before
   ever attempting payment (price hesitation, missing wallet option,
   currency/locale confusion, plain distraction) and sends a bounded
   cart-recovery link.
3. **"Money deducted, order not placed"** — reconciles the bank-debit feed
   against the checkout-cart feed (the way a cron/polling job would in
   production) to catch webhook-timeout cases where the bank took the
   money but the order was never fulfilled, then auto-fulfills or refunds.
4. **Peak-hour routing degradation** — detects hours where success rate
   craters (e.g. bank server overload) and shifts a bounded percentage of
   traffic to an alternate payment rail for that window, measuring the
   resulting recovery.
5. **Overdue receivables** — chooses a grace period and message tone based
   on each customer's actual payment history (not one rigid rule for
   everyone), hard-caps automated reminders, and never auto-contacts a
   disputed invoice — directly targeting the "we spammed a client and they
   quit" failure mode.

Every module shares the same underlying engine: fraud/risk filtering,
stopping rules (hard caps enforced in code), a compliant escalation queue,
a unified audit trail, and measured (not projected) recovery totals.

## Architecture

```
Five input sources (failed txns / checkout sessions / bank-debit+cart
feeds / hourly success-rate data / overdue invoices)
      |
      v
[Module-specific diagnosis]  <- trained classifier+SHAP (payments) or
      |                          deterministic rules (all other modules)
      v
[Fraud / risk / dispute filter]
      |
      v
[Stopping rules]  -> caps retries / amount / time / reminder count
      |
      +-- Safe & within rules -> [Bounded execution: test-mode API / internal action] -> logged outcome
      +-- Not safe / rules exceeded -> [Escalation queue]
      |
      v
[Shared audit trail]  -> every decision, every signal, every outcome, tagged by module
      |
      v
[Per-module batch report]  -> measured Rs recovered, recovery %, classifier precision/recall (payments only)
```

<img width="1096" height="1109" alt="System Architecture Pipeline Governance Flow" src="https://github.com/user-attachments/assets/a18afb66-2e53-4fd4-aa2f-812e6d877289" />



## WORKFLOW



<img width="2720" height="3200" alt="unified_workflow_bw" src="https://github.com/user-attachments/assets/6daa9b8a-bc7e-4b3c-bc9e-32c5d109032f" />



See `docs/bar_mapping.md` for how each part of this maps to the stated
hackathon bar, and `docs/compliance_note.md` for exactly what this system
does and does not do with real money/customer data.

## Quickstart

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # optional: add real Razorpay TEST keys
uvicorn main:app --reload --port 8000
```

All five synthetic datasets are already generated and included. To
regenerate any of them:
```bash
python data/generate_synthetic_data.py        # payment failures
python data/generate_checkout_data.py         # checkout abandonment
python data/generate_reconciliation_data.py   # phantom payments
python data/generate_routing_data.py          # peak-hour routing
python data/generate_receivables_data.py      # overdue receivables
```

### Frontend
No build step needed — plain HTML/JS.
```bash
cd frontend
npm install
npm run dev
python -m http.server 5500
```
Then open `http://localhost:5500` in your browser. Make sure the backend is
running on port 8000 first (CORS is already enabled for this).

### Try it
1. Open the frontend dashboard.
2. Use the tabs at the top to pick a module (Payment Failures, Checkout
   Abandonment, "Money Deducted No Order", Peak-Hour Routing, Overdue
   Receivables).
3. Click **"Run This Module"** — this runs the full pipeline for that
   module and shows measured results, cause breakdown (where applicable),
   the escalation queue, and the audit trail.
4. Click any audit-trail row to see the full plain-language explanation.

### Live webhook demo (real-time path)
The Payment Failures module also has a real-time path, separate from the
batch tool above — this simulates what actually happens in production when
Razorpay delivers a `payment.failed` webhook: one event arrives, gets
diagnosed and acted on immediately, no batch, no manual click.

1. With the backend running, open the frontend and click the **"🔴 Live
   Feed"** tab — it starts polling for new events every 2 seconds.
2. In a separate terminal:
   ```bash
   cd backend
   python scripts/simulate_live_webhook.py
   ```
   This sends realistic failed-payment events to
   `POST /api/webhooks/payment-failed` one at a time, with a random delay
   between each (like real webhook deliveries would arrive).
3. Watch each event appear in the Live Feed tab within ~2 seconds of being
   sent, already diagnosed and acted on.

You can also call the webhook directly with `curl` to send a single event —
see `backend/app/routes/webhook.py` for the payload shape.

### Run the tests
```bash
cd backend
python -m pytest tests/ -v
```

## Tech Stack 


BACKEND:


Tool	                             

FastAPI	                

Uvicorn	                

scikit-learn	          

SHAP	                  

pandas / numpy	          

Razorpay SDK	          

Anthropic SDK	          

google-generativeai	    

python-dotenv	          

Pydantic	Data validation 

SQLite	                

pytest	                

 FRONTEND:
 
Tool	                   

React 18	                 

Vite	                   

React Router	          

Recharts	                

STORAGE :

SQLite (audit_log.db) — the unified audit trail

JSON file (escalation_queue.json) — the escalation queue

CSV files — the five synthetic datasets, auto-regenerated if stale

## Video Explanation of Project

https://1drv.ms/v/c/72EE7D73FBAD63C9/IQDqCuiNIxLJS7vlP33Tg6QuAQ3qiBy_Of5UIfWXaHQ5ZJw?e=j7kkGh

https://1drv.ms/w/c/72EE7D73FBAD63C9/IQCBOWkkmwQYQpti4YKCvMxUAX_BJj5WjPLE2Lh7qR_Y6zI?e=kBmBwh


## Note


Only payment failures uses real ML — that's where we have data to predict from. Everything else is rule-based on purpose. We added an LLM in receivables purely to write reminder wording — never to decide. Letting AI make money or contact decisions would undermine the safety we're proving with tests — restraint here is the judgment.

