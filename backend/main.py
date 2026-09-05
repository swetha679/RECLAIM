from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import time

from app.config import settings
from app.diagnosis.classifier import classifier
from app.audit import audit_logger
from app.routes import diagnose, batch_run, audit, report, extended_modules, webhook

app = FastAPI(
    title="Payment Degradation Explainability & Bounded Recovery Agent",
    description=(
        "Diagnoses why payments failed in plain language, executes a bounded "
        "test-mode recovery action where safe, and reports measured results "
        "with a full audit trail."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # relaxed for hackathon demo; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    _ensure_fresh_synthetic_data()
    audit_logger.init_db()
    classifier.fit_from_csv(settings.SYNTHETIC_DATA_PATH)
    print("Classifier trained. Backend ready.")


# stopping_rules.py's TIME_BOX_DAYS=30 blocks retries on anything older than
# 30 days. The generator creates transactions 0-15 days old at the moment
# it's run, so the file itself goes stale ~15 days after generation. Rather
# than relying on whoever clones this repo to remember to run the generator
# manually (see data/generate_synthetic_data.py), regenerate automatically
# here if the file is missing or older than a safe threshold — so any judge
# running this for the first time always gets fresh, non-expiring data with
# zero manual steps.
_MAX_DATA_AGE_DAYS = 5


def _ensure_fresh_synthetic_data():
    path = settings.SYNTHETIC_DATA_PATH
    needs_regen = True
    if os.path.exists(path):
        age_days = (time.time() - os.path.getmtime(path)) / 86400
        needs_regen = age_days > _MAX_DATA_AGE_DAYS

    if needs_regen:
        from data.generate_synthetic_data import main as regenerate_transactions

        regenerate_transactions()
        print(f"Synthetic data was missing or older than {_MAX_DATA_AGE_DAYS} days — regenerated.")


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Payment Degradation Agent backend is running.",
        "docs": "/docs",
    }


app.include_router(diagnose.router, prefix="/api", tags=["diagnose"])
app.include_router(batch_run.router, prefix="/api", tags=["batch"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(report.router, prefix="/api", tags=["report"])
app.include_router(extended_modules.router, prefix="/api", tags=["extended"])
app.include_router(webhook.router, prefix="/api", tags=["webhook"])
