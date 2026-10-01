"""Bronze: raw, append-only, idempotent landing. Exactly-once effect = at-least-once delivery + content-hash dedupe."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import duckdb

from emblem.contracts import Contract, load_contracts, normalise
from emblem.pipelines.retry import retry

Records = list[dict[str, Any]]


def row_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def ensure_bronze(con: duckdb.DuckDBPyConnection, c: Contract) -> None:
    con.execute(f"""CREATE TABLE IF NOT EXISTS bronze.{c.table}(_row_hash VARCHAR PRIMARY KEY, _batch_id VARCHAR,
        _ingested_at TIMESTAMP, _source_updated_at TIMESTAMP, _payload JSON)""")
    con.execute("""CREATE TABLE IF NOT EXISTS bronze.quarantine(dataset VARCHAR, batch_id VARCHAR, reason VARCHAR, payload JSON,
        quarantined_at TIMESTAMP)""")


def _parse_ts(v: Any) -> datetime | None:
    try:
        return datetime.strptime(str(v), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def ingest_dataset(
    con: duckdb.DuckDBPyConnection,
    dataset: str,
    extract: Callable[[], Records],
    batch_id: str,
    now: datetime | None = None,
    sleep: Callable[[float], None] = lambda _s: None,
) -> dict[str, Any]:
    c = load_contracts()[dataset]
    now = (now or datetime.now(UTC)).replace(tzinfo=None)
    started = datetime.now(UTC).replace(tzinfo=None)
    ensure_bronze(con, c)
    records, attempts = retry(extract, sleep=sleep)
    inserted = dup = quarantined = 0
    con.execute("BEGIN")
    try:
        before = con.execute(f"SELECT count(*) FROM bronze.{c.table}").fetchone()[0]  # type: ignore[index]
        seen_changes: set[tuple[str, str]] = set()
        for rec in records:
            n = normalise(c, rec)
            for old, new in n.renamed.items():
                seen_changes.add(("renamed_alias", f"{old}->{new}"))
            for col in n.added:
                seen_changes.add(("additive_column", col))
            if n.missing_required:
                quarantined += 1
                con.execute(
                    "INSERT INTO bronze.quarantine VALUES (?,?,?,?,?)",
                    [
                        dataset,
                        batch_id,
                        "missing_required:" + ",".join(n.missing_required),
                        json.dumps(rec),
                        now,
                    ],
                )
                continue
            ts = _parse_ts(n.payload.get(c.updated_at))
            con.execute(
                f"INSERT INTO bronze.{c.table} VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                [row_hash(n.payload), batch_id, now, ts, json.dumps(n.payload, default=str)],
            )
        after = con.execute(f"SELECT count(*) FROM bronze.{c.table}").fetchone()[0]  # type: ignore[index]
        inserted = after - before
        dup = len(records) - quarantined - inserted
        for kind, detail in sorted(seen_changes):
            sev = "info" if kind == "renamed_alias" else "warning"
            con.execute(
                "INSERT INTO meta.schema_changes VALUES (?,?,?,?,?,?)",
                [batch_id, dataset, kind, detail, sev, now],
            )
        if quarantined:
            con.execute(
                "INSERT INTO meta.schema_changes VALUES (?,?,?,?,?,?)",
                [
                    batch_id,
                    dataset,
                    "breaking_missing_required",
                    f"{quarantined} rows quarantined",
                    "critical",
                    now,
                ],
            )
        wm = max((t for t in (_parse_ts(r.get(c.updated_at)) for r in records) if t), default=None)
        if wm:
            con.execute(
                "INSERT INTO meta.watermarks VALUES (?,?) ON CONFLICT (dataset) DO UPDATE SET high_watermark = "
                "greatest(meta.watermarks.high_watermark, excluded.high_watermark)",
                [dataset, wm],
            )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        con.execute(
            "INSERT INTO meta.ingest_log VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                batch_id,
                dataset,
                len(records),
                0,
                0,
                0,
                "failed",
                attempts,
                started,
                datetime.now(UTC).replace(tzinfo=None),
            ],
        )
        raise
    stats = {
        "dataset": dataset,
        "received": len(records),
        "inserted": inserted,
        "duplicate": dup,
        "quarantined": quarantined,
        "attempts": attempts,
    }
    con.execute(
        "INSERT INTO meta.ingest_log VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            batch_id,
            dataset,
            len(records),
            inserted,
            dup,
            quarantined,
            "ok",
            attempts,
            started,
            datetime.now(UTC).replace(tzinfo=None),
        ],
    )
    return stats


def ingest_world(
    con: duckdb.DuckDBPyConnection, world: dict[str, Records], batch_id: str, now: datetime | None = None
) -> list[dict[str, Any]]:
    return [ingest_dataset(con, ds, (lambda r=rows: r), batch_id, now) for ds, rows in world.items()]  # type: ignore[misc]
