import pandas as pd
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import BatchRunRequest
from app.pipeline import run_batch

router = APIRouter()


@router.post("/batch-run")
def batch_run(request: BatchRunRequest):
    if request.use_synthetic_data or not request.transactions:
        try:
            df = pd.read_csv(settings.SYNTHETIC_DATA_PATH)
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="Synthetic dataset not found. Run data/generate_synthetic_data.py first.",
            )
        transactions = df.to_dict(orient="records")
    else:
        transactions = [t.model_dump() for t in request.transactions]

    result = run_batch(transactions)
    return result
