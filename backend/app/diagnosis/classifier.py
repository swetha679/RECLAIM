"""
Root-cause classifier.

Trains a small RandomForest on the synthetic labeled dataset at startup
(splitting into train/held-out test so we can honestly report precision and
recall — see metrics/evaluation.py), then exposes predict() for single
transactions used by the live pipeline.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from app.diagnosis.feature_extraction import extract_features, features_to_dataframe, FEATURE_COLUMNS
from app.diagnosis.cause_taxonomy import CAUSE_LIST


class CauseClassifier:
    def __init__(self):
        self.model: RandomForestClassifier | None = None
        self.train_df = None
        self.test_df = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None

    def fit_from_csv(self, csv_path: str, test_size: float = 0.25, random_state: int = 42):
        raw = pd.read_csv(csv_path)
        feature_rows = [extract_features(row.to_dict()) for _, row in raw.iterrows()]
        X = features_to_dataframe(feature_rows)
        y = raw["true_cause"]

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        self.model = RandomForestClassifier(
            n_estimators=200, max_depth=6, random_state=random_state
        )
        self.model.fit(self.X_train, self.y_train)
        return self

    def predict_one(self, txn: dict) -> dict:
        """Returns predicted cause + confidence for a single raw transaction dict."""
        features = extract_features(txn)
        X = features_to_dataframe([features])
        proba = self.model.predict_proba(X)[0]
        classes = self.model.classes_
        best_idx = proba.argmax()
        cause = classes[best_idx]
        confidence = float(proba[best_idx])
        return {
            "cause": cause,
            "confidence": round(confidence, 3),
            "all_probabilities": {c: round(float(p), 3) for c, p in zip(classes, proba)},
            "features": features,
        }


# Singleton instance, trained once at app startup
classifier = CauseClassifier()
