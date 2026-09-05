from typing import Optional
from pydantic import BaseModel


class TransactionIn(BaseModel):
    transaction_id: str
    timestamp: str
    amount_inr: float
    is_international: bool
    issuer_country: str
    card_network: str
    device: str
    three_ds_attempted: bool
    wallet_offered: bool
    decline_code: str
    customer_email: str
    customer_address: str


class DiagnoseResponse(BaseModel):
    transaction_id: str
    cause: str
    cause_label: str
    confidence: float
    explanation: str
    recommendation: str
    top_signals: list[str]


class BatchRunRequest(BaseModel):
    use_synthetic_data: bool = True
    transactions: Optional[list[TransactionIn]] = None
