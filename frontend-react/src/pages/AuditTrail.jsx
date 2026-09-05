import { useEffect, useState } from "react";
import { Card, Table, Badge, Loading, ErrorBox } from "../components/Common.jsx";
import { api, MODULES } from "../api.js";

export default function AuditTrail() {
  const [entries, setEntries] = useState([]);
  const [sourceType, setSourceType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  function load(filter) {
    setLoading(true);
    setError(null);
    api
      .getAuditTrail(filter ? { source_type: filter } : {})
      .then((data) => setEntries(data.entries || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => load(""), []);

  return (
    <div className="page">
      <h1>Audit Trail</h1>
      <p className="subtitle">Every action from all 5 pipelines, in one unified log.</p>

      <div className="tab-row">
        <button className={"tab" + (sourceType === "" ? " tab-active" : "")} onClick={() => { setSourceType(""); load(""); }}>
          All
        </button>
        {MODULES.map((m) => (
          <button
            key={m.key}
            className={"tab" + (sourceType === m.key ? " tab-active" : "")}
            onClick={() => { setSourceType(m.key); load(m.key); }}
          >
            {m.label}
          </button>
        ))}
      </div>

      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : (
        <Card title={`${entries.length} entries`}>
          <Table
            columns={[
              { key: "transaction_id", label: "ID" },
              { key: "source_type", label: "Module" },
              { key: "diagnosed_cause", label: "Cause" },
              { key: "action_taken", label: "Action" },
              { key: "api_mode", label: "Mode" },
              { key: "outcome", label: "Outcome", render: (r) => <Badge value={r.outcome} /> },
              { key: "created_at", label: "When" },
            ]}
            rows={entries}
            onRowClick={setSelected}
          />
        </Card>
      )}

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{selected.transaction_id}</h3>
            <pre className="detail-json">{JSON.stringify(selected, null, 2)}</pre>
            <button className="btn" onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
