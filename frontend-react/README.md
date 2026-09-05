# Revenue Recovery Agent — React Frontend

A React + Vite dashboard for the real 5-pipeline backend (payment failures,
checkout abandonment, reconciliation, routing, receivables). This replaces
the plain HTML/JS frontend in `../frontend/` with a page-based structure —
same real backend, no backend changes required.

## Run it

Backend must be running first (`cd ../backend && uvicorn main:app --reload --port 8000`).

```bash
npm install
npm run dev
```

Open http://localhost:5173 — the dev server proxies `/api/*` to
`http://localhost:8000`, so no CORS setup or manual base-URL config needed.

## Pages

- **Home** — overview + quick links
- **Run Modules** — trigger any of the 5 real pipelines (`/api/batch-run`,
  `/api/checkout-run`, `/api/reconciliation-run`, `/api/routing-run`,
  `/api/receivables-run`)
- **Dashboard** — aggregated report (`GET /api/report`)
- **Audit Trail** — every logged entry across all 5 modules, filterable by
  source type (`GET /api/audit-trail`)
- **Escalation Queue** — pending human-review cases (`GET /api/escalations`)
- **Diagnose (Ad-hoc)** — send one transaction straight to the classifier
  (`POST /api/diagnose`)
- **Reports** — classifier evaluation + cause-breakdown chart
  (`GET /api/evaluate`, `GET /api/report`)

Every endpoint above is a real route in `../backend/app/routes/` — nothing
here is mocked or points at a different backend.

## Build for production

```bash
npm run build
```

Output goes to `dist/` — serve it with any static file server, or point
`uvicorn`'s CORS config at wherever you host it.
