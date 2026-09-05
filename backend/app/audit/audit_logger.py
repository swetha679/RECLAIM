"""
Audit trail — one row per processed transaction, capturing the full decision
path: diagnosis, confidence, signals, whether it was retried or escalated,
and the actual outcome. This is queryable directly via GET /api/audit-trail.
"""

import json
import os
import sqlite3
from datetime import datetime

from app.config import settings


def _get_conn():
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            source_type TEXT,
            amount_inr REAL,
            diagnosed_cause TEXT,
            confidence REAL,
            top_signals TEXT,
            explanation TEXT,
            recommendation TEXT,
            action_taken TEXT,
            action_reason TEXT,
            api_mode TEXT,
            outcome TEXT,
            escalated INTEGER,
            batch_id TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )
    # Backward-compatible migrations for older DBs created before these
    # columns/index existed.
    for stmt in [
        "ALTER TABLE audit_log ADD COLUMN source_type TEXT",
        "ALTER TABLE audit_log ADD COLUMN retry_count INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass

    # Idempotency: the same transaction, same module, at the same retry
    # attempt number can only be logged once. A genuinely new retry attempt
    # (higher retry_count) is a new row, not a duplicate.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_txn_dedup
        ON audit_log(transaction_id, source_type, retry_count)
        """
    )
    conn.commit()
    conn.close()


def count_prior_attempts(transaction_id: str, source_type: str) -> int:
    """How many times this transaction has already been logged for this
    module — used by pipelines to pass the real retry_count into
    stopping_rules.py instead of always hardcoding 0."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM audit_log WHERE transaction_id = ? AND source_type = ?",
        (transaction_id, source_type),
    ).fetchone()
    conn.close()
    return row["c"] if row else 0


def clear_log():
    conn = _get_conn()
    conn.execute("DELETE FROM audit_log")
    conn.commit()
    conn.close()


def log_entry(entry: dict):
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO audit_log (
                transaction_id, source_type, amount_inr, diagnosed_cause, confidence, top_signals,
                explanation, recommendation, action_taken, action_reason, api_mode,
                outcome, escalated, batch_id, retry_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("transaction_id"),
                entry.get("source_type", "payment_failure"),
                entry.get("amount_inr"),
                entry.get("diagnosed_cause"),
                entry.get("confidence"),
                json.dumps(entry.get("top_signals", [])),
                entry.get("explanation"),
                entry.get("recommendation"),
                entry.get("action_taken"),
                entry.get("action_reason"),
                entry.get("api_mode"),
                entry.get("outcome"),
                int(entry.get("escalated", False)),
                entry.get("batch_id"),
                entry.get("retry_count", 0),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # A true duplicate: same transaction_id + source_type + retry_count
        # already logged. This is idempotency working as intended, not an
        # error — don't crash the pipeline, just skip the duplicate write.
        pass
    finally:
        conn.close()


def get_all_entries(batch_id: str | None = None, source_type: str | None = None) -> list:
    conn = _get_conn()
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if batch_id:
        query += " AND batch_id = ?"
        params.append(batch_id)
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    query += " ORDER BY id ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
