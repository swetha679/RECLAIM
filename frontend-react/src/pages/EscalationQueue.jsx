import { useEffect, useState } from "react";
import { Card, Table, Loading, ErrorBox } from "../components/Common.jsx";
import { api } from "../api.js";

export default function EscalationQueue() {
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getEscalations()
      .then((data) => setEscalations(data.escalations || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h1>Escalation Queue</h1>
      <p className="subtitle">
        Cases that failed the fraud gate or a hard limit — routed to human
        review instead of auto-executed. Read from{" "}
        <code>escalation_queue.json</code>, not the audit database.
      </p>

      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : (
        <Card title={`${escalations.length} pending`}>
          <Table
            columns={[
              { key: "transaction_id", label: "ID" },
              { key: "amount_inr", label: "Amount", render: (r) => `₹${Number(r.amount_inr).toLocaleString("en-IN")}` },
              { key: "cause", label: "Cause" },
              { key: "escalation_reason", label: "Reason" },
              { key: "escalated_at", label: "When" },
            ]}
            rows={escalations}
          />
        </Card>
      )}
    </div>
  );
}
