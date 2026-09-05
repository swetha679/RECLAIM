// Wired to the actual FastAPI routes in backend/app/routes/*.py — every
// endpoint here corresponds to a real route, not a reference/guessed one.
const BASE = "/api";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

function post(path, body) {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  }).then(handle);
}

function get(path, params = {}) {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ""))
  ).toString();
  return fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`).then(handle);
}

export const MODULES = [
  { key: "payment_failure", label: "Payment Failures", endpoint: "/batch-run", body: { use_synthetic_data: true } },
  { key: "checkout_abandonment", label: "Checkout Abandonment", endpoint: "/checkout-run" },
  { key: "phantom_payment", label: "Reconciliation", endpoint: "/reconciliation-run" },
  { key: "routing_degradation", label: "Routing", endpoint: "/routing-run" },
  { key: "overdue_receivable", label: "Receivables", endpoint: "/receivables-run" },
];

export const api = {
  // Ad-hoc single-transaction diagnosis — POST /api/diagnose
  diagnose: (txn) => post("/diagnose", txn),

  // GET /api/sample-transaction — a real row from the actual dataset,
  // to pre-fill the Diagnose form instead of hand-typing one every time
  getSampleTransaction: () => get("/sample-transaction"),

  // One "Run" endpoint per module — each reads its own CSV server-side,
  // no request body needed except payment-failure batch-run.
  runModule: (moduleKey) => {
    const mod = MODULES.find((m) => m.key === moduleKey);
    if (!mod) throw new Error(`Unknown module: ${moduleKey}`);
    return post(mod.endpoint, mod.body);
  },

  // Live webhook simulation — POST /api/webhooks/payment-failed
  simulateWebhook: (txn) => post("/webhooks/payment-failed", txn),

  // GET /api/audit-trail?batch_id=&source_type=
  getAuditTrail: (params = {}) => get("/audit-trail", params),

  // GET /api/report?batch_id=
  getReport: (batchId) => get("/report", { batch_id: batchId }),

  // GET /api/evaluate — classifier accuracy (payment-failure module only)
  getEvaluation: () => get("/evaluate"),

  // GET /api/escalations — reads escalation_queue.json
  getEscalations: () => get("/escalations"),
};
