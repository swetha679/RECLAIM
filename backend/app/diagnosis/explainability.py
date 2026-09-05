"""
Explainability layer. Uses SHAP TreeExplainer against the trained
RandomForest to find which features contributed most to the predicted
cause, then renders those into a plain-language explanation string.

Falls back to a simple rule-based explanation if SHAP isn't available or
fails for any reason (keeps the demo resilient).
"""

import numpy as np
import shap

from app.diagnosis.cause_taxonomy import CAUSES
from app.diagnosis.feature_extraction import FEATURE_COLUMNS, features_to_dataframe

FEATURE_LABELS = {
    "amount_inr": "transaction amount",
    "is_international_num": "international card",
    "three_ds_attempted_num": "3DS/OTP step was attempted",
    "wallet_offered_num": "wallet payment method offered",
    "device_mobile_num": "customer on mobile",
    "small_amount_num": "unusually small amount",
    "generic_decline_num": "generic 'technical error' code",
    "risk_decline_num": "risk-engine decline code",
    "fraud_decline_num": "fraud-suspected decline code",
    "infra_decline_num": "bank/infra decline code",
    "funds_decline_num": "insufficient-funds decline code",
    "same_test_address_num": "address reused across multiple orders",
}


class Explainer:
    def __init__(self, classifier):
        self.classifier = classifier
        self._shap_explainer = None

    def _ensure_shap(self):
        if self._shap_explainer is None:
            self._shap_explainer = shap.TreeExplainer(self.classifier.model)
        return self._shap_explainer

    def explain(self, txn: dict, prediction: dict) -> dict:
        cause = prediction["cause"]
        confidence = prediction["confidence"]
        features = prediction["features"]

        top_signals = self._top_contributing_features(features, cause)
        taxonomy = CAUSES.get(cause, {})
        description = taxonomy.get("description", "")
        label = taxonomy.get("label", cause)

        signal_phrases = [FEATURE_LABELS.get(f, f) for f in top_signals]
        signal_text = ", ".join(signal_phrases) if signal_phrases else "the overall transaction pattern"

        explanation = (
            f"This payment likely failed due to: {label}. {description} "
            f"Confidence: {int(confidence * 100)}%, based on: {signal_text}."
        )

        return {
            "cause": cause,
            "cause_label": label,
            "confidence": confidence,
            "explanation": explanation,
            "top_signals": top_signals,
        }

    def _top_contributing_features(self, features: dict, cause: str, top_n: int = 3) -> list:
        try:
            X = features_to_dataframe([features])
            explainer = self._ensure_shap()
            shap_values = explainer.shap_values(X)

            classes = list(self.classifier.model.classes_)
            if cause not in classes:
                return self._fallback_signals(features)
            class_idx = classes.index(cause)

            # shap_values shape can vary by version: list[class] of (n, n_features)
            # or array (n, n_features, n_classes). Handle both.
            if isinstance(shap_values, list):
                values = shap_values[class_idx][0]
            else:
                values = shap_values[0, :, class_idx]

            contributions = list(zip(FEATURE_COLUMNS, values))
            contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            top = [f for f, v in contributions[:top_n] if abs(v) > 1e-6]
            return top if top else self._fallback_signals(features)
        except Exception:
            return self._fallback_signals(features)

    @staticmethod
    def _fallback_signals(features: dict) -> list:
        # Simple rule-based fallback: return the features that are "on" / notable
        active = []
        if features.get("is_international_num"):
            active.append("is_international_num")
        if features.get("three_ds_attempted_num"):
            active.append("three_ds_attempted_num")
        if not features.get("wallet_offered_num"):
            active.append("wallet_offered_num")
        if features.get("fraud_decline_num"):
            active.append("fraud_decline_num")
        if features.get("same_test_address_num"):
            active.append("same_test_address_num")
        return active[:3]
