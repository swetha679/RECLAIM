let currentBatchId = null;
let currentModule = "payment_failure";
let liveFeedPollInterval = null;
let liveFeedSeenIds = new Set();
let liveFeedFirstLoad = true;

const $ = (id) => document.getElementById(id);
const inr = (n) => `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

function setStatus(text) {
  $("statusText").textContent = text;
}

// ---------------------------------------------------------------------
// Module registry: each module knows how to run itself, and how to turn
// its summary object into metric cards. This keeps app.js from needing a
// separate rendering function per module for the parts that are the same
// shape (metric cards, cause chart, audit table, escalations).
// ---------------------------------------------------------------------
const MODULES = {
  payment_failure: {
    label: "Payment Failures",
    run: () => ApiClient.runBatch(),
    hasClassifierEval: true,
    causeChartTitle: "Failure Cause Breakdown",
    metrics: (s) => [
      { label: "Total Failed Amount", value: inr(s.total_failed_amount_inr) },
      { label: "Recovered (measured)", value: inr(s.total_recovered_inr), highlight: true },
      { label: "Recovery Rate", value: `${s.recovery_rate_pct}%` },
      { label: "Retried", value: s.retried_count },
      { label: "Escalated", value: s.escalated_count },
    ],
    causeBreakdown: (s) => s.cause_breakdown,
    note: (s) => (s.structural_check ? s.structural_check.note : null),
  },

  checkout_abandonment: {
    label: "Checkout Abandonment",
    run: () => ApiClient.runCheckout(),
    hasClassifierEval: false,
    causeChartTitle: "Abandonment Cause Breakdown",
    metrics: (s) => [
      { label: "Total Cart Value", value: inr(s.total_cart_value_inr) },
      { label: "Recovered (measured)", value: inr(s.total_recovered_inr), highlight: true },
      { label: "Recovery Rate", value: `${s.recovery_rate_pct}%` },
      { label: "Recovery Links Sent", value: s.recovery_links_sent },
      { label: "Escalated", value: s.escalated_count },
    ],
    causeBreakdown: (s) => s.cause_breakdown,
    note: () => null,
  },

  phantom_payment: {
    label: '"Money Deducted, No Order"',
    run: () => ApiClient.runReconciliation(),
    hasClassifierEval: false,
    causeChartTitle: null,
    metrics: (s) => [
      { label: "Debits Checked", value: s.total_debits_checked },
      { label: "Phantom Payments Found", value: s.total_phantom_payments_found },
      { label: "Phantom Amount", value: inr(s.total_phantom_amount_inr) },
      { label: "Orders Auto-Fulfilled", value: s.auto_fulfilled_count, highlight: true },
      { label: "Refunds Initiated", value: s.refunded_count },
      { label: "Escalated", value: s.escalated_count },
    ],
    causeBreakdown: () => null,
    note: () =>
      "Detected via cron/polling-style reconciliation between the bank-debit feed and the checkout-cart feed — every phantom payment means the bank confirmed the debit but the merchant's system never received the success webhook (typically a gateway degradation causing a webhook timeout).",
  },

  routing_degradation: {
    label: "Peak-Hour Routing",
    run: () => ApiClient.runRouting(),
    hasClassifierEval: false,
    causeChartTitle: null,
    metrics: (s) => [
      { label: "Hours Analyzed", value: s.hours_analyzed },
      { label: "Degraded Hours Found", value: s.degraded_hours_found },
      { label: "Additional Transactions Recovered", value: s.total_additional_transactions_recovered, highlight: true },
    ],
    causeBreakdown: () => null,
    note: () =>
      "When an hour's success rate falls below threshold, the agent shifts a bounded % of traffic to an alternate payment rail for that window only (never disabling the primary rail), then measures the resulting success-rate change.",
  },

  overdue_receivable: {
    label: "Overdue Receivables",
    run: () => ApiClient.runReceivables(),
    hasClassifierEval: false,
    causeChartTitle: null,
    metrics: (s) => [
      { label: "Total Invoices", value: s.total_invoices },
      { label: "Total Overdue Amount", value: inr(s.total_overdue_amount_inr) },
      { label: "Reminders Sent", value: s.reminders_sent, highlight: true },
      { label: "Escalated to Human", value: s.escalated_count },
      { label: "Disputed Invoices Protected", value: s.disputed_invoices_protected },
      { label: "Auto-Reminder Cap", value: s.max_auto_reminders_cap },
    ],
    causeBreakdown: () => null,
    note: (s) =>
      `Grace period and message tone are chosen per customer's payment history, not a single rigid rule for everyone. Disputed invoices are never auto-contacted — they route straight to a human account manager. Automated reminders hard-stop at ${s.max_auto_reminders_cap} regardless of tone, after which the case escalates to a human.`,
  },
};

// ---------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentModule = btn.dataset.module;
    currentBatchId = null;
    resetView();

    if (currentModule === "live_feed") {
      startLiveFeed();
    } else {
      stopLiveFeed();
    }
  });
});

function resetView() {
  $("summarySection").classList.add("hidden");
  $("escalationSection").classList.add("hidden");
  $("auditSection").classList.add("hidden");
  $("liveFeedSection").classList.add("hidden");
  $("runBatchBtn").classList.remove("hidden");
  setStatus("");
}

// ---------------------------------------------------------------------
// Live Feed: polls the audit trail for live_webhook entries every 2s and
// appends any new ones, simulating a live-updating view of events as a
// real webhook handler would produce them.
// ---------------------------------------------------------------------
function startLiveFeed() {
  $("liveFeedSection").classList.remove("hidden");
  $("runBatchBtn").classList.add("hidden");
  liveFeedSeenIds = new Set();
  liveFeedFirstLoad = true;
  $("liveFeedList").innerHTML = `<p class="hint">Waiting for live events... run <code>python scripts/simulate_live_webhook.py</code> in a terminal.</p>`;

  pollLiveFeed();
  liveFeedPollInterval = setInterval(pollLiveFeed, 2000);
}

function stopLiveFeed() {
  if (liveFeedPollInterval) {
    clearInterval(liveFeedPollInterval);
    liveFeedPollInterval = null;
  }
}

async function pollLiveFeed() {
  try {
    const data = await ApiClient.getAuditTrail("live_webhook", "payment_failure");
    const newEntries = data.entries.filter((e) => !liveFeedSeenIds.has(e.id));

    if (newEntries.length === 0) return;

    if (liveFeedFirstLoad) {
      $("liveFeedList").innerHTML = "";
      liveFeedFirstLoad = false;
    }

    newEntries.forEach((entry) => {
      liveFeedSeenIds.add(entry.id);
      const div = document.createElement("div");
      const actionClass = entry.action_taken === "escalated" ? "action-escalated" : "";
      const outcomeClass = entry.outcome === "succeeded" ? "outcome-succeeded" : "";
      div.className = `live-feed-item ${actionClass} ${outcomeClass}`;
      div.innerHTML = `
        <div class="lf-top">
          <span class="lf-txn">${entry.transaction_id}</span>
          <span>${new Date(entry.created_at).toLocaleTimeString()}</span>
        </div>
        <div class="lf-explanation">
          <strong>${inr(entry.amount_inr)}</strong> — ${entry.diagnosed_cause}
          (${Math.round(entry.confidence * 100)}% confidence) →
          <span class="badge ${actionClass ? 'badge-escalated' : 'badge-retried'}">${entry.action_taken}</span>
          — ${entry.outcome}
        </div>
      `;
      $("liveFeedList").appendChild(div);
    });
  } catch (err) {
    console.error("Live feed poll failed:", err);
  }
}

// ---------------------------------------------------------------------
// Run current module
// ---------------------------------------------------------------------
async function runCurrentModule() {
  if (currentModule === "live_feed") return; // live feed has no manual run button
  const btn = $("runBatchBtn");
  const mod = MODULES[currentModule];
  btn.disabled = true;
  setStatus(`Running ${mod.label}...`);

  try {
    const result = await mod.run();
    currentBatchId = result.summary.batch_id;

    renderSummary(mod, result.summary);
    if (mod.hasClassifierEval) {
      $("evalBox").classList.remove("hidden");
      await renderEvaluation();
    } else {
      $("evalBox").classList.add("hidden");
    }

    await renderAuditTrail(currentBatchId, currentModule);
    await renderEscalations();

    $("summarySection").classList.remove("hidden");
    $("escalationSection").classList.remove("hidden");
    $("auditSection").classList.remove("hidden");

    setStatus(`Done. Batch ${currentBatchId}.`);
  } catch (err) {
    console.error(err);
    setStatus(`Error: ${err.message}. Is the backend running on http://localhost:8000?`);
  } finally {
    btn.disabled = false;
  }
}

function renderSummary(mod, summary) {
  $("summaryTitle").textContent = `${mod.label} — Measured Results`;

  const grid = $("metricsGrid");
  grid.innerHTML = "";
  mod.metrics(summary).forEach((m) => {
    const card = document.createElement("div");
    card.className = "metric-card" + (m.highlight ? " highlight" : "");
    card.innerHTML = `
      <div class="metric-label">${m.label}</div>
      <div class="metric-value">${m.value}</div>
    `;
    grid.appendChild(card);
  });

  const breakdown = mod.causeBreakdown(summary);
  const chartBox = document.querySelector(".chart-box");
  if (breakdown) {
    chartBox.classList.remove("hidden");
    $("chartTitle").textContent = mod.causeChartTitle;
    renderCauseChart(breakdown);
  } else {
    chartBox.classList.add("hidden");
  }

  const noteText = mod.note(summary);
  const noteEl = $("structuralNote");
  if (noteText) {
    noteEl.textContent = noteText;
    noteEl.classList.remove("hidden");
  } else {
    noteEl.classList.add("hidden");
  }
}

const CAUSE_COLORS = {
  "3ds_mismatch": "#4f8cff",
  wallet_absent: "#34c77b",
  issuer_risk: "#e8a13d",
  fraud_bot: "#e85d5d",
  insufficient_funds: "#9b6fe8",
  infra_error: "#3dc7e8",
  unclear: "#8a8f99",
  price_hesitation: "#4f8cff",
  payment_method_missing: "#34c77b",
  currency_confusion: "#e8a13d",
  distraction_dropoff: "#8a8f99",
};

const CAUSE_LABELS = {
  "3ds_mismatch": "3DS / auth mismatch",
  wallet_absent: "Wallet absent",
  issuer_risk: "Issuer / country risk",
  fraud_bot: "Fraud / bot pattern",
  insufficient_funds: "Insufficient funds",
  infra_error: "Infra error",
  unclear: "Unclear",
  price_hesitation: "Price hesitation",
  payment_method_missing: "Payment method missing",
  currency_confusion: "Currency / locale confusion",
  distraction_dropoff: "Distraction drop-off",
};

function renderCauseChart(breakdown) {
  const container = $("causeChart");
  container.innerHTML = "";

  const total = Object.values(breakdown).reduce((a, b) => a + b, 0);
  if (total === 0) {
    container.textContent = "No data.";
    return;
  }

  const sorted = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);

  sorted.forEach(([cause, count]) => {
    const pct = Math.round((count / total) * 100);
    const color = CAUSE_COLORS[cause] || "#4f8cff";
    const label = CAUSE_LABELS[cause] || cause;

    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <div class="bar-row-label">
        <span class="bar-dot" style="background:${color}"></span>
        <span>${label}</span>
        <span class="bar-row-count">${count} (${pct}%)</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${pct}%; background:${color}"></div>
      </div>
    `;
    container.appendChild(row);
  });
}

async function renderEvaluation() {
  try {
    const evalData = await ApiClient.getEvaluation();
    const o = evalData.overall;
    const container = $("evalSummary");
    container.innerHTML = `
      <div class="eval-row"><span>Precision</span><strong>${o.precision}</strong></div>
      <div class="eval-row"><span>Recall</span><strong>${o.recall}</strong></div>
      <div class="eval-row"><span>F1 Score</span><strong>${o.f1}</strong></div>
      <div class="eval-row"><span>Held-out test size</span><strong>${o.test_set_size}</strong></div>
    `;
  } catch (err) {
    $("evalSummary").textContent = "Evaluation unavailable.";
  }
}

async function renderAuditTrail(batchId, sourceType) {
  const data = await ApiClient.getAuditTrail(batchId, sourceType);

  const tbody = $("auditTableBody");
  tbody.innerHTML = "";

  data.entries.forEach((entry) => {
    const tr = document.createElement("tr");
    const actionClass = entry.action_taken === "escalated" ? "badge-escalated" : "badge-retried";
    tr.innerHTML = `
      <td>${entry.transaction_id}</td>
      <td>${inr(entry.amount_inr)}</td>
      <td>${entry.diagnosed_cause}</td>
      <td>${Math.round(entry.confidence * 100)}%</td>
      <td><span class="badge ${actionClass}">${entry.action_taken}</span></td>
      <td>${entry.outcome}</td>
    `;
    tr.addEventListener("click", () => showDetail(entry));
    tbody.appendChild(tr);
  });
}

async function renderEscalations() {
  const data = await ApiClient.getEscalations();
  const container = $("escalationList");
  container.innerHTML = "";

  if (data.escalations.length === 0) {
    container.innerHTML = `<p class="hint">No escalations logged yet.</p>`;
    return;
  }

  data.escalations
    .slice()
    .reverse()
    .slice(0, 30)
    .forEach((e) => {
      const div = document.createElement("div");
      div.className = "escalation-item";
      div.innerHTML = `
        <div class="txn-id">${e.transaction_id} — ${inr(e.amount_inr)} — ${e.cause}</div>
        <div class="reason">${e.escalation_reason}: ${e.recommendation}</div>
      `;
      container.appendChild(div);
    });
}

function showDetail(entry) {
  $("modalTxnId").textContent = entry.transaction_id;
  $("modalCause").textContent = entry.diagnosed_cause;
  $("modalConfidence").textContent = `${Math.round(entry.confidence * 100)}%`;
  $("modalExplanation").textContent = entry.explanation;
  $("modalRecommendation").textContent = entry.recommendation;
  $("modalAction").textContent = entry.action_taken;
  $("modalOutcome").textContent = entry.outcome;
  $("detailModal").classList.remove("hidden");
}

$("closeModalBtn").addEventListener("click", () => {
  $("detailModal").classList.add("hidden");
});

$("detailModal").addEventListener("click", (e) => {
  if (e.target.id === "detailModal") $("detailModal").classList.add("hidden");
});

$("runBatchBtn").addEventListener("click", runCurrentModule);
