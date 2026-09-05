import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/diagnose", label: "Diagnose (Ad-hoc)" },
  { to: "/run-batch", label: "Run Modules" },
  { to: "/audit-trail", label: "Audit Trail" },
  { to: "/escalations", label: "Escalation Queue" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/reports", label: "Reports" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-dot" />
        Revenue Recovery Agent
      </div>
      <nav>
        {LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">5 pipelines · 1 audit trail</div>
    </aside>
  );
}
