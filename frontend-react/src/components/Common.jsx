export function Card({ title, children, right }) {
  return (
    <div className="card">
      {(title || right) && (
        <div className="card-head">
          {title && <h3>{title}</h3>}
          {right}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
}

export function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

const BADGE_COLORS = {
  succeeded: "green",
  reminder_sent: "green",
  auto_fulfilled: "green",
  routed: "green",
  failed: "red",
  escalated: "amber",
  api_error: "red",
  pending: "gray",
  refunded: "blue",
};

export function Badge({ value }) {
  const color = BADGE_COLORS[value] || "gray";
  return <span className={`badge badge-${color}`}>{value}</span>;
}

export function Loading({ label = "Loading..." }) {
  return <div className="loading">{label}</div>;
}

export function ErrorBox({ message }) {
  if (!message) return null;
  return <div className="error-box">⚠ {message}</div>;
}

export function EmptyState({ message }) {
  return <div className="empty-state">{message}</div>;
}

export function Table({ columns, rows, onRowClick }) {
  if (!rows || rows.length === 0) {
    return <EmptyState message="No data yet — run a module first." />;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id ?? row.transaction_id ?? i} onClick={() => onRowClick?.(row)} className={onRowClick ? "clickable" : ""}>
              {columns.map((c) => (
                <td key={c.key}>{c.render ? c.render(row) : row[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
