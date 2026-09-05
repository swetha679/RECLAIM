"""
Honest evaluation of the classifier against the held-out test set carved out
at training time (see classifier.fit_from_csv). This is a real accuracy
measurement, separate from the batch-level recovery projection.
"""

from sklearn.metrics import classification_report, precision_recall_fscore_support


def evaluate_classifier(classifier) -> dict:
    if classifier.model is None or classifier.X_test is None:
        return {"error": "Classifier not trained yet."}

    y_pred = classifier.model.predict(classifier.X_test)
    y_true = classifier.y_test

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    report = classification_report(y_true, y_pred, zero_division=0, output_dict=True)

    return {
        "overall": {
            "precision": round(float(precision), 3),
            "recall": round(float(recall), 3),
            "f1": round(float(f1), 3),
            "test_set_size": len(y_true),
        },
        "per_cause": {
            cause: {
                "precision": round(vals["precision"], 3),
                "recall": round(vals["recall"], 3),
                "f1": round(vals["f1-score"], 3),
                "support": vals["support"],
            }
            for cause, vals in report.items()
            if cause not in ("accuracy", "macro avg", "weighted avg")
        },
    }
