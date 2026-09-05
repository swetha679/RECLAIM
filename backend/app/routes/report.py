from typing import Optional
from fastapi import APIRouter

from app.metrics.batch_report import build_report
from app.metrics.evaluation import evaluate_classifier
from app.diagnosis.classifier import classifier
from app.escalation.escalation_manager import get_escalations

router = APIRouter()


@router.get("/report")
def get_report(batch_id: Optional[str] = None):
    return build_report(batch_id)


@router.get("/evaluate")
def get_evaluation():
    return evaluate_classifier(classifier)


@router.get("/escalations")
def get_escalation_queue():
    return {"escalations": get_escalations()}
