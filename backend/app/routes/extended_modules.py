import pandas as pd
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.reconciliation.pipeline import run_reconciliation
from app.routing.pipeline import run_routing_analysis
from app.receivables.pipeline import run_receivables_batch
from app.checkout.pipeline import run_checkout_batch

router = APIRouter()


@router.post("/reconciliation-run")
def reconciliation_run():
    try:
        debits = pd.read_csv(settings.RECONCILIATION_DEBITS_PATH).to_dict(orient="records")
        carts = pd.read_csv(settings.RECONCILIATION_CARTS_PATH).to_dict(orient="records")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Reconciliation data not found. Run data/generate_reconciliation_data.py first.",
        )
    return run_reconciliation(debits, carts)


@router.post("/routing-run")
def routing_run():
    try:
        rows = pd.read_csv(settings.ROUTING_DATA_PATH).to_dict(orient="records")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Routing data not found. Run data/generate_routing_data.py first.",
        )
    return run_routing_analysis(rows)


@router.post("/receivables-run")
def receivables_run():
    try:
        rows = pd.read_csv(settings.RECEIVABLES_PATH).to_dict(orient="records")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Receivables data not found. Run data/generate_receivables_data.py first.",
        )
    return run_receivables_batch(rows)


@router.post("/checkout-run")
def checkout_run():
    try:
        rows = pd.read_csv(settings.CHECKOUT_SESSIONS_PATH).to_dict(orient="records")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Checkout session data not found. Run data/generate_checkout_data.py first.",
        )
    return run_checkout_batch(rows)
