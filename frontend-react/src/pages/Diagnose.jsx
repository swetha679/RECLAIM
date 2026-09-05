import { useState } from "react";
import { Card, ErrorBox, Loading, Badge } from "../components/Common.jsx";
import { api } from "../api.js";

// Field names/types match app/models.py TransactionIn exactly.
const DEFAULT_TXN = {
  transaction_id: "txn_manual_001",
  timestamp: new Date().toISOString(),
  amount_inr: 4500,
  is_international: false,
  issuer_country: "IN",
  card_network: "visa",
  device: "mobile",
  three_ds_attempted: true,
  wallet_offered: false,
  decline_code: "insufficient_funds",
  customer_email: "test@example.com",
  customer_address: "Bengaluru, IN",
};

export default function Diagnose() {
  const [txn, setTxn] = useState(DEFAULT_TXN);
  const [result, setResult] = useState(null);
  const [webhookResult, setWebhookResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [webhookLoading, setWebhookLoading] = useState(false);
  const [error, setError] = useState(null);
  const [webhookError, setWebhookError] = useState(null);

  function update(key, value) {
    setTxn((t) => ({ ...t, [key]: value }));
  }

  async function loadSample() {
    try {
      const sample = await api.getSampleTransaction();
      setTxn((t) => ({ ...t, ...sample }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.diagnose({
        ...txn,
        amount_inr: Number(txn.amount_inr),
      });
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitAsWebhook() {
    setWebhookLoading(true);
    setWebhookError(null);
    setWebhookResult(null);
    try {
      const data = await api.simulateWebhook({
        ...txn,
        amount_inr: Number(txn.amount_inr),
      });
      setWebhookResult(data.entry);
    } catch (e) {
      setWebhookError(e.message);
    } finally {
      setWebhookLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>Diagnose (Ad-hoc)</h1>
      <p className="subtitle">Run the classifier alone, or simulate the full live-webhook pipeline end to end.</p>

      <div className="grid-2">
        <Card title="Transaction">
          <button type="button" className="btn btn-outline" style={{ marginBottom: 14 }} onClick={loadSample}>
            🎲 Load random sample from real dataset
          </button>
          <form onSubmit={submit} className="form">
            <label>Transaction ID<input value={txn.transaction_id} onChange={(e) => update("transaction_id", e.target.value)} /></label>
            <label>Amount (INR)<input type="number" value={txn.amount_inr} onChange={(e) => update("amount_inr", e.target.value)} /></label>
            <label>Decline code<input value={txn.decline_code} onChange={(e) => update("decline_code", e.target.value)} /></label>
            <label>Card network<input value={txn.card_network} onChange={(e) => update("card_network", e.target.value)} /></label>
            <label>Device<input value={txn.device} onChange={(e) => update("device", e.target.value)} /></label>
            <label>Issuer country<input value={txn.issuer_country} onChange={(e) => update("issuer_country", e.target.value)} /></label>
            <label className="checkbox">
              <input type="checkbox" checked={txn.is_international} onChange={(e) => update("is_international", e.target.checked)} />
              International
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={txn.three_ds_attempted} onChange={(e) => update("three_ds_attempted", e.target.checked)} />
              3DS attempted
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={txn.wallet_offered} onChange={(e) => update("wallet_offered", e.target.checked)} />
              Wallet offered
            </label>
            <div className="btn-row">
              <button className="btn" type="submit" disabled={loading}>
                {loading ? "Diagnosing..." : "Diagnose only"}
              </button>
              <button
                type="button"
                className="btn btn-outline"
                disabled={webhookLoading}
                onClick={submitAsWebhook}
              >
                {webhookLoading ? "Processing..." : "Simulate as live webhook →"}
              </button>
            </div>
          </form>
        </Card>

        <Card title="Diagnosis-only result">
          <ErrorBox message={error} />
          {loading && <Loading />}
          {result && (
            <div className="diagnose-result">
              <div className="result-cause">{result.cause_label}</div>
              <div className="result-confidence">{Math.round(result.confidence * 100)}% confidence</div>
              <p>{result.explanation}</p>
              <div className="result-signals">
                {result.top_signals?.map((s) => (
                  <span key={s} className="signal-chip">{s}</span>
                ))}
              </div>
              <p className="recommendation">→ {result.recommendation}</p>
            </div>
          )}
          {!result && !loading && !error && <p className="empty-state">Runs the classifier only — no execution, no logging, no audit trail entry.</p>}
        </Card>
      </div>

      <Card title="Live webhook result — full pipeline (detect → diagnose → decide → execute → log)">
        <p className="subtitle" style={{ marginBottom: 12 }}>
          Sends this same transaction to <code>POST /api/webhooks/payment-failed</code> —
          the same endpoint Razorpay would call in production. Unlike "Diagnose only," this
          runs the fraud check, stopping rules, execution, and writes a real row to the audit trail.
        </p>
        <ErrorBox message={webhookError} />
        {webhookLoading && <Loading label="Running full pipeline..." />}
        {webhookResult && (
          <div className="kv-grid">
            <div className="kv-item"><span className="kv-key">Cause</span><span className="kv-val">{webhookResult.diagnosed_cause}</span></div>
            <div className="kv-item"><span className="kv-key">Confidence</span><span className="kv-val">{Math.round((webhookResult.confidence || 0) * 100)}%</span></div>
            <div className="kv-item"><span className="kv-key">Action taken</span><span className="kv-val">{webhookResult.action_taken}</span></div>
            <div className="kv-item"><span className="kv-key">Outcome</span><span className="kv-val"><Badge value={webhookResult.outcome} /></span></div>
            <div className="kv-item"><span className="kv-key">API mode</span><span className="kv-val">{webhookResult.api_mode || "—"}</span></div>
            <div className="kv-item"><span className="kv-key">Escalated</span><span className="kv-val">{webhookResult.escalated ? "Yes" : "No"}</span></div>
            <div className="kv-item"><span className="kv-key">Batch ID</span><span className="kv-val">{webhookResult.batch_id}</span></div>
          </div>
        )}
        {!webhookResult && !webhookLoading && !webhookError && (
          <p className="empty-state">This is your only visible trigger for the real-time path — check the Audit Trail page afterward to see this exact entry logged.</p>
        )}
      </Card>
    </div>
  );
}
