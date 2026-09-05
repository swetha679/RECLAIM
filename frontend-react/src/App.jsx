import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Home from "./pages/Home.jsx";
import RunBatch from "./pages/RunBatch.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import AuditTrail from "./pages/AuditTrail.jsx";
import EscalationQueue from "./pages/EscalationQueue.jsx";
import Diagnose from "./pages/Diagnose.jsx";
import Reports from "./pages/Reports.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/run-batch" element={<RunBatch />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/audit-trail" element={<AuditTrail />} />
          <Route path="/escalations" element={<EscalationQueue />} />
          <Route path="/diagnose" element={<Diagnose />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
      </main>
    </div>
  );
}
