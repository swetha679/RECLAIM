"""
Converts a raw transaction dict into a numeric feature vector the classifier
can consume. Kept deliberately simple and explicit so every feature is easy
to explain back to a merchant.
"""

import pandas as pd

FEATURE_COLUMNS = [
    "amount_inr",
    "is_international_num",
    "three_ds_attempted_num",
    "wallet_offered_num",
    "device_mobile_num",
    "small_amount_num",
    "generic_decline_num",
    "risk_decline_num",
    "fraud_decline_num",
    "infra_decline_num",
    "funds_decline_num",
    "same_test_address_num",
]


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return bool(v)


def extract_features(txn: dict) -> dict:
    decline_code = str(txn.get("decline_code", "")).lower()
    address = str(txn.get("customer_address", ""))

    return {
        "amount_inr": float(txn.get("amount_inr", 0)),
        "is_international_num": int(_to_bool(txn.get("is_international"))),
        "three_ds_attempted_num": int(_to_bool(txn.get("three_ds_attempted"))),
        "wallet_offered_num": int(_to_bool(txn.get("wallet_offered"))),
        "device_mobile_num": int(str(txn.get("device", "")).lower() == "mobile"),
        "small_amount_num": int(float(txn.get("amount_inr", 0)) < 400),
        "generic_decline_num": int(decline_code == "technical_error"),
        "risk_decline_num": int(decline_code == "risk_declined"),
        "fraud_decline_num": int(decline_code == "fraud_suspected"),
        "infra_decline_num": int(decline_code == "bank_server_down"),
        "funds_decline_num": int(decline_code == "insufficient_funds"),
        "same_test_address_num": int("test ave" in address.lower()),
    }


def features_to_dataframe(feature_dicts: list) -> pd.DataFrame:
    df = pd.DataFrame(feature_dicts)
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    return df[FEATURE_COLUMNS]
