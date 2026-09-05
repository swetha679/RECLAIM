from typing import Optional
from fastapi import APIRouter

from app.audit import audit_logger

router = APIRouter()


@router.get("/audit-trail")
def get_audit_trail(batch_id: Optional[str] = None, source_type: Optional[str] = None):
    entries = audit_logger.get_all_entries(batch_id, source_type)
    return {"count": len(entries), "entries": entries}
