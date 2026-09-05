import { useEffect, useState } from "react";
import { Card, StatCard, Loading, ErrorBox } from "../components/Common.jsx";
import { api } from "../api.js";

export default function Dashboard() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getReport()
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading report..." />;

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p className="subtitle">Aggregated across every audit log entry — run a module first if this looks empty.</p>
      <ErrorBox message={error} />

      {report?.error && <p className="empty-state">{report.error}</p>}

      {report && !report.error && (
        <>
          <div className="grid-4">
            <StatCard label="Total Transactions" value={report.total_transactions} />
            <StatCard label="Recovery Rate" value={`${report.recovery_rate_pct}%`} />
            <StatCard label="Escalation Rate" value={`${report.escalation_rate_pct}%`} />
            <StatCard
              label="False-Positive Cost"
              value={`₹${report.false_positive_cost_inr?.toLocaleString("en-IN")}`}
              sub="Retried but failed"
            />
          </div>

          <div className="grid-2">
            <Card title="Amounts">
              <div className="kv-grid">
                <div className="kv-item">
                  <span className="kv-key">Total at risk</span>
                  <span className="kv-val">₹{report.total_failed_amount_inr?.toLocaleString("en-IN")}</span>
                </div>
                <div className="kv-item">
                  <span className="kv-key">Recovered</span>
                  <span className="kv-val">₹{report.total_recovered_inr?.toLocaleString("en-IN")}</span>
                </div>
              </div>
            </Card>
            <Card title="Retries">
              <div className="kv-grid">
                <div className="kv-item"><span className="kv-key">Retried</span><span className="kv-val">{report.retried_count}</span></div>
                <div className="kv-item"><span className="kv-key">Succeeded</span><span className="kv-val">{report.retry_success_count}</span></div>
                <div className="kv-item"><span className="kv-key">Failed</span><span className="kv-val">{report.retry_failed_count}</span></div>
                <div className="kv-item"><span className="kv-key">Escalated</span><span className="kv-val">{report.escalated_count}</span></div>
              </div>
            </Card>
          </div>

          <Card title="Cause Breakdown">
            <div className="bar-list">
              {Object.entries(report.cause_breakdown || {}).map(([cause, count]) => (
                <div key={cause} className="bar-row">
                  <span className="bar-label">{cause}</span>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{ width: `${(count / report.total_transactions) * 100}%` }}
                    />
                  </div>
                  <span className="bar-count">{count}</span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
