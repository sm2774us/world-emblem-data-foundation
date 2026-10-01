"""Event-driven integration: HMAC-verified webhooks -> idempotent inbox -> bronze (with dead-letter handling)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any

import duckdb

from emblem.pipelines.bronze import ingest_dataset

TOPICS = {
    ("bigcommerce", "order.created"): "bg.orders",
    ("bigcommerce", "order.updated"): "bg.orders",
    ("hubspot", "company.updated"): "hs.companies",
}
TOLERANCE_S = 300


class SignatureError(Exception):
    pass


def sign(secret: bytes, timestamp: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def verify_signature(
    secret: bytes, timestamp: str, body: bytes, signature: str, now: float | None = None
) -> None:
    try:
        age = abs((now or time.time()) - float(timestamp))
    except ValueError as exc:
        raise SignatureError("bad timestamp") from exc
    if age > TOLERANCE_S:
        raise SignatureError("stale timestamp (replay protection)")
    if not hmac.compare_digest(sign(secret, timestamp, body), signature):
        raise SignatureError("signature mismatch")


def receive(
    con: duckdb.DuckDBPyConnection, source: str, event_id: str, topic: str, body: dict[str, Any]
) -> str:
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        con.execute(
            "INSERT INTO meta.events_inbox VALUES (?,?,?,?,?,?,NULL)",
            [event_id, source, topic, json.dumps(body), now, "received"],
        )
        return "accepted"
    except duckdb.ConstraintException:
        return "duplicate"  # at-least-once delivery from the sender is expected; we absorb it


def drain(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    stats = {"processed": 0, "dead_letter": 0}
    for event_id, source, topic, payload in con.execute(
        "SELECT event_id, source, topic, payload FROM meta.events_inbox WHERE status='received' ORDER BY received_at"
    ).fetchall():
        ds = TOPICS.get((source, topic))
        status = "dead_letter"
        if ds:
            try:
                ingest_dataset(con, ds, lambda p=payload: [json.loads(p)], f"evt-{event_id}")  # type: ignore[misc]
                status = "processed"
            except Exception:
                status = "dead_letter"
        stats["processed" if status == "processed" else "dead_letter"] += 1
        con.execute(
            "UPDATE meta.events_inbox SET status=?, processed_at=? WHERE event_id=?",
            [status, datetime.now(UTC).replace(tzinfo=None), event_id],
        )
    return stats
