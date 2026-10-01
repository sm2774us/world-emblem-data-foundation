"""Automated data-quality engine: completeness, accuracy, duplication, freshness, consistency, volume, schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

import duckdb
import yaml

from emblem.contracts import DATA_DIR


@dataclass
class CheckResult:
    check_id: str
    dataset: str
    dimension: str
    severity: str
    domain: str
    passed: bool
    observed: float
    threshold: float
    detail: str
    source_fix: str = ""
    runbook: str = "pipeline-failure"


def load_checks() -> list[dict[str, Any]]:
    return yaml.safe_load((DATA_DIR / "quality" / "checks.yaml").read_text())["checks"]


def _eval(con: duckdb.DuckDBPyConnection, spec: dict[str, Any], as_of: date) -> CheckResult:
    try:
        raw = con.execute(spec["sql"].replace("{as_of}", as_of.isoformat())).fetchone()[0]  # type: ignore[index]
        observed = float(raw) if raw is not None else 0.0
        ok = observed <= spec["threshold"] if spec["op"] == "max" else observed >= spec["threshold"]
        detail = f"observed {observed:.4g} vs {spec['op']} {spec['threshold']}"
    except duckdb.Error as exc:  # a broken check must surface as a failure, never silently pass
        observed, ok, detail = float("nan"), False, f"check errored: {exc}"
    return CheckResult(
        spec["id"],
        spec["dataset"],
        spec["dimension"],
        spec["severity"],
        spec["domain"],
        ok,
        observed,
        float(spec["threshold"]),
        detail,
        spec.get("source_fix", ""),
        spec.get("runbook", "pipeline-failure"),
    )


def volume_checks(con: duckdb.DuckDBPyConnection, min_ratio: float = 0.3) -> list[CheckResult]:
    """Latest incremental batch vs the mean of earlier incremental batches (initial load excluded)."""
    out: list[CheckResult] = []
    for (ds,) in con.execute("SELECT DISTINCT dataset FROM meta.ingest_log ORDER BY 1").fetchall():
        rows = con.execute(
            "SELECT batch_id, rows_received FROM meta.ingest_log WHERE dataset=? AND status='ok' AND batch_id LIKE 'b%-%' AND batch_id NOT LIKE 'b1-%' "
            "ORDER BY started_at",
            [ds],
        ).fetchall()
        if len(rows) < 2:
            continue
        prior = [r[1] for r in rows[:-1]]
        base = sum(prior) / len(prior)
        if base < 5:
            continue
        ratio = rows[-1][1] / base
        out.append(
            CheckResult(
                f"dq_volume_{ds.replace('.', '_')}",
                ds,
                "volume",
                "critical" if ratio < min_ratio else "warning",
                "order" if "order" in ds else "pipeline",
                ratio >= min_ratio,
                round(ratio, 3),
                min_ratio,
                f"latest batch {rows[-1][1]} rows vs prior mean {base:.1f}",
                "Owning team: confirm upstream extract is complete; replay the window",
                "pipeline-failure",
            )
        )
    return out


def schema_checks(con: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    n = con.execute("SELECT count(*) FROM meta.schema_changes WHERE severity='critical'").fetchone()[0]  # type: ignore[index]
    return [
        CheckResult(
            "dq_no_breaking_schema_change",
            "all",
            "schema",
            "critical",
            "pipeline",
            n == 0,
            float(n),
            0.0,
            f"{n} breaking schema change(s) detected",
            "Source owner: restore the field or version the data contract",
            "schema-drift",
        )
    ]


def run_checks(con: duckdb.DuckDBPyConnection, as_of: date, run_id: str) -> list[CheckResult]:
    results = [_eval(con, s, as_of) for s in load_checks()] + volume_checks(con) + schema_checks(con)
    now = datetime.now(UTC).replace(tzinfo=None)
    for r in results:
        obs = None if r.observed != r.observed else r.observed
        con.execute(
            "INSERT INTO meta.dq_results VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                run_id,
                r.check_id,
                r.dataset,
                r.dimension,
                r.severity,
                r.passed,
                obs,
                r.threshold,
                r.detail,
                now,
            ],
        )
    return results


def summarise(results: list[CheckResult]) -> dict[str, Any]:
    by_dim: dict[str, list[bool]] = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r.passed)
    return {
        "total": len(results),
        "passed": sum(r.passed for r in results),
        "failed": sum(not r.passed for r in results),
        "score": round(sum(r.passed for r in results) / max(len(results), 1), 4),
        "by_dimension": {k: round(sum(v) / len(v), 3) for k, v in sorted(by_dim.items())},
        "failures": [asdict(r) for r in results if not r.passed],
    }
