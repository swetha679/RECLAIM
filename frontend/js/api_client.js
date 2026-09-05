const API_BASE_URL = "http://localhost:8000/api";

const ApiClient = {
  async runBatch() {
    const res = await fetch(`${API_BASE_URL}/batch-run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ use_synthetic_data: true }),
    });
    if (!res.ok) throw new Error(`batch-run failed: ${res.status}`);
    return res.json();
  },

  async runReconciliation() {
    const res = await fetch(`${API_BASE_URL}/reconciliation-run`, { method: "POST" });
    if (!res.ok) throw new Error(`reconciliation-run failed: ${res.status}`);
    return res.json();
  },

  async runRouting() {
    const res = await fetch(`${API_BASE_URL}/routing-run`, { method: "POST" });
    if (!res.ok) throw new Error(`routing-run failed: ${res.status}`);
    return res.json();
  },

  async runReceivables() {
    const res = await fetch(`${API_BASE_URL}/receivables-run`, { method: "POST" });
    if (!res.ok) throw new Error(`receivables-run failed: ${res.status}`);
    return res.json();
  },

  async runCheckout() {
    const res = await fetch(`${API_BASE_URL}/checkout-run`, { method: "POST" });
    if (!res.ok) throw new Error(`checkout-run failed: ${res.status}`);
    return res.json();
  },

  async getReport(batchId) {
    const url = batchId
      ? `${API_BASE_URL}/report?batch_id=${batchId}`
      : `${API_BASE_URL}/report`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`report failed: ${res.status}`);
    return res.json();
  },

  async getEvaluation() {
    const res = await fetch(`${API_BASE_URL}/evaluate`);
    if (!res.ok) throw new Error(`evaluate failed: ${res.status}`);
    return res.json();
  },

  async getAuditTrail(batchId, sourceType) {
    const params = new URLSearchParams();
    if (batchId) params.set("batch_id", batchId);
    if (sourceType) params.set("source_type", sourceType);
    const qs = params.toString();
    const res = await fetch(`${API_BASE_URL}/audit-trail${qs ? "?" + qs : ""}`);
    if (!res.ok) throw new Error(`audit-trail failed: ${res.status}`);
    return res.json();
  },

  async getEscalations() {
    const res = await fetch(`${API_BASE_URL}/escalations`);
    if (!res.ok) throw new Error(`escalations failed: ${res.status}`);
    return res.json();
  },
};
