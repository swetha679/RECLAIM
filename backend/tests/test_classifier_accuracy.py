import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.diagnosis.classifier import CauseClassifier
from app.metrics.evaluation import evaluate_classifier
from app.config import settings


def test_classifier_trains_and_predicts():
    clf = CauseClassifier()
    clf.fit_from_csv(settings.SYNTHETIC_DATA_PATH)
    assert clf.model is not None

    sample_txn = {
        "transaction_id": "test_1",
        "amount_inr": 20000,
        "is_international": True,
        "issuer_country": "US",
        "card_network": "visa",
        "device": "mobile",
        "three_ds_attempted": True,
        "wallet_offered": False,
        "decline_code": "technical_error",
        "customer_email": "test@example.com",
        "customer_address": "1 Test St",
    }
    prediction = clf.predict_one(sample_txn)
    assert prediction["cause"] in clf.model.classes_
    assert 0.0 <= prediction["confidence"] <= 1.0


def test_classifier_reasonable_accuracy():
    clf = CauseClassifier()
    clf.fit_from_csv(settings.SYNTHETIC_DATA_PATH)
    result = evaluate_classifier(clf)
    # On a small synthetic dataset we don't expect perfection, but it should
    # be meaningfully better than random guessing across 7 classes (~0.14).
    assert result["overall"]["precision"] > 0.4
    assert result["overall"]["recall"] > 0.4
