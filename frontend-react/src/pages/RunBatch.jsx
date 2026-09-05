import { useState } from "react";
import { Card, Table, Badge, Loading, ErrorBox } from "../components/Common.jsx";
import { api, MODULES } from "../api.js";

export default function RunBatch() {
  const [active, setActive] = useState(MODULES[0].key);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function run(moduleKey) {
    setActive(moduleKey);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.runModule(moduleKey);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const rows = result?.results || [];

  return (
    <div className="page">
      <h1>Run Modules</h1>
      <p className="subtitle">Each module reads its own dataset server-side and runs its own diagnosis + governance pipeline.</p>

      <div className="tab-row">
        {MODULES.map((m) => (
          <button
            key={m.key}
            className={"tab" + (active === m.key ? " tab-active" : "")}
            onClick={() => run(m.key)}
            disabled={loading}
          >
            {m.label}
          </button>
        ))}
      </div>

      <ErrorBox message={error} />
      {loading && <Loading label={`Running ${MODULES.find((m) => m.key === active)?.label}...`} />}

      {result?.summary && (
        <Card title="Batch Summary">
          <div className="kv-grid">
            {Object.entries(result.summary).map(([k, v]) => {
              if (k === "cause_breakdown") {
                const breakdown = typeof v === "string" ? JSON.parse(v) : v;
                return (
                  <div key={k} className="kv-item kv-wide">
                    <span className="kv-key">{k}</span>
                    <div className="cause-chip-row">
                      {Object.entries(breakdown).map(([cause, count]) => (
                        <span key={cause} className="cause-chip">{cause}: {count}</span>
                      ))}
                    </div>
                  </div>
                );
              }
              return (
                <div key={k} className="kv-item">
                  <span className="kv-key">{k}</span>
                  <span className="kv-val">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {rows.length > 0 && (
        <Card title={`Results (${rows.length})`}>
          <Table
            columns={[
              { key: "transaction_id", label: "ID" },
              { key: "diagnosed_cause", label: "Cause" },
              { key: "confidence", label: "Confidence", render: (r) => r.confidence != null ? `${Math.round(r.confidence * 100)}%` : "—" },
              { key: "action_taken", label: "Action" },
              { key: "outcome", label: "Outcome", render: (r) => <Badge value={r.outcome} /> },
              { key: "escalated", label: "Escalated", render: (r) => (r.escalated ? "Yes" : "No") },
            ]}
            rows={rows}
          />
        </Card>
      )}
    </div>
  );
}
