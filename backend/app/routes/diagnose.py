import pandas as pd
from fastapi import APIRouter, HTTPException

from app.diagnosis.classifier import classifier
from app.diagnosis.explainability import Explainer
from app.diagnosis.playbook import get_recommendation
from app.models import TransactionIn, DiagnoseResponse
from app.config import settings

router = APIRouter()
explainer = Explainer(classifier)


@router.post("/diagnose", response_model=DiagnoseResponse)
def diagnose_transaction(txn: TransactionIn):
    if classifier.model is None:
        raise HTTPException(status_code=503, detail="Classifier not trained yet.")

    txn_dict = txn.model_dump()
    prediction = classifier.predict_one(txn_dict)
    explanation = explainer.explain(txn_dict, prediction)
    recommendation = get_recommendation(explanation["cause"])

    return DiagnoseResponse(
        transaction_id=txn.transaction_id,
        cause=explanation["cause"],
        cause_label=explanation["cause_label"],
        confidence=explanation["confidence"],
        explanation=explanation["explanation"],
        recommendation=recommendation,
        top_signals=explanation["top_signals"],
    )


@router.get("/sample-transaction")
def get_sample_transaction():
    """
    Returns one real, random row from the actual dataset — pre-fills the
    manual Diagnose form so testing doesn't require inventing a transaction
    by hand every time. `true_cause` is deliberately stripped: that's the
    labeled answer used to train/evaluate the classifier, and returning it
    here would let the form "know" the answer before diagnosing it, which
    defeats the point of a genuine test case.
    """
    df = pd.read_csv(settings.SYNTHETIC_DATA_PATH)
    row = df.sample(n=1).iloc[0].to_dict()
    row.pop("true_cause", None)
    # CSV booleans come back as numpy/py bool-ish strings already handled
    # by pandas; is_international / three_ds_attempted / wallet_offered
    # are already real Python bools after pandas parses "True"/"False".
    return row
