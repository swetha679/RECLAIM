import { Link } from "react-router-dom";
import { Card } from "../components/Common.jsx";
import { MODULES } from "../api.js";

export default function Home() {
  return (
    <div className="page">
      <h1>Revenue Recovery Agent</h1>
      <p className="subtitle">
        Detects revenue at risk, diagnoses the specific cause, and executes a
        bounded recovery action — across payment failures, checkout
        abandonment, and overdue receivables.
      </p>

      <div className="grid-3">
        <Card title="1. Run a module">
          <p>Trigger any of the 5 pipelines against its real dataset.</p>
          <Link className="btn" to="/run-batch">Go to Run Modules →</Link>
        </Card>
        <Card title="2. See the results">
          <p>Aggregated recovery, cause breakdown, and escalation rate.</p>
          <Link className="btn" to="/dashboard">Go to Dashboard →</Link>
        </Card>
        <Card title="3. Inspect every decision">
          <p>Every action across all 5 pipelines, in one unified log.</p>
          <Link className="btn" to="/audit-trail">Go to Audit Trail →</Link>
        </Card>
      </div>

      <Card title="Modules">
        <ul className="module-list">
          {MODULES.map((m) => (
            <li key={m.key}>
              <span className="module-dot" />
              {m.label}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
