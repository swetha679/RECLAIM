import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Card, Loading, ErrorBox } from "../components/Common.jsx";
import { api, MODULES } from "../api.js";

const COLORS = ["#4f8cff", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#14b8a6", "#eab308"];

// One small bar chart per module, instead of one combined pie — a single
// pie mixing all 5 modules' causes had 15+ categories, some with counts as
// low as 3-4, which made labels overlap and the chart unreadable. A sorted
// bar chart per module handles "one dominant cause + several small ones"
// far better than a pie slice ever could.
function ModuleBarChart({ label, data }) {
  if (data.length === 0) {
    return (
      <Card title={label}>
        <p className="empty-state">No data yet — run this module first.</p>
      </Card>
    );
  }
  const sorted = [...data].sort((a, b) => b.value - a.value);
  return (
    <Card title={label}>
      <ResponsiveContainer width="100%" height={Math.max(140, sorted.length * 34)}>
        <BarChart data={sorted} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={140} tick={{ fill: "#93a0bf", fontSize: 12 }} />
          <Tooltip contentStyle={{ background: "#16213a", border: "1px solid #223052" }} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {sorted.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export default function Reports() {
  const [evalData, setEvalData] = useState(null);
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getEvaluation(), api.getAuditTrail()])
      .then(([ev, audit]) => {
        setEvalData(ev);
        setEntries(audit.entries || []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading reports..." />;

  // Group audit entries by module, then count causes within each module —
  // done client-side from one /api/audit-trail call rather than 5 separate
  // /api/report calls, since /api/report doesn't accept a source_type filter.
  const byModule = {};
  for (const m of MODULES) byModule[m.key] = {};
  for (const e of entries) {
    const mod = byModule[e.source_type];
    if (!mod) continue;
    mod[e.diagnosed_cause] = (mod[e.diagnosed_cause] || 0) + 1;
  }

  return (
    <div className="page">
      <h1>Reports</h1>
      <p className="subtitle">
        Classifier accuracy applies to the payment-failure module only — the
        other four modules are rule-based, so accuracy isn't a meaningful
        metric for them.
      </p>
      <ErrorBox message={error} />

      <Card title="Classifier Evaluation (Payment Failures)">
        {evalData && !evalData.error ? (
          <div className="kv-grid">
            {Object.entries(evalData).map(([k, v]) => (
              <div key={k} className="kv-item">
                <span className="kv-key">{k}</span>
                <span className="kv-val">{typeof v === "number" ? v.toFixed(3) : String(v)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">Run the payment-failure module first.</p>
        )}
      </Card>

      <h3 style={{ margin: "8px 0 4px" }}>Cause Breakdown — one chart per module</h3>
      <div className="grid-2">
        {MODULES.map((m) => (
          <ModuleBarChart
            key={m.key}
            label={m.label}
            data={Object.entries(byModule[m.key]).map(([name, value]) => ({ name, value }))}
          />
        ))}
      </div>
    </div>
  );
}
