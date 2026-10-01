"""Assemble the full showcase snapshot (single JSON document) consumed by the dashboard and `GET /v1/showcase`."""

from __future__ import annotations

from datetime import date
from typing import Any

import duckdb
import yaml

from emblem.ai import index, tools
from emblem.architecture import platform, sor
from emblem.catalog import audit, lineage
from emblem.contracts import DATA_DIR, load_contracts
from emblem.governance import vendor
from emblem.ops import incidents, monitor
from emblem.plan import plan
from emblem.quality.checks import CheckResult, summarise
from emblem.reporting import semantic_model
from emblem.security import audit as audit_log
from emblem.security import rbac, retention

LAYERS = [
    ("Sources", "BC, HubSpot, BigCommerce, Optimizely, Ad platforms, MES"),
    ("Bronze", "Raw, append-only, idempotent, quarantined"),
    ("Silver", "Typed from contracts, deduped, entity-resolved"),
    ("Gold", "Governed models, marts, forecast, AI index"),
    ("Serve", "Power BI semantic model, governed API, agent tools"),
]


def traceability() -> list[dict[str, str]]:
    raw = yaml.safe_load((DATA_DIR / "catalog" / "jd_traceability.yaml").read_text())["items"]
    return [{"section": s, "requirement": r, "evidence": e, "demo": d} for s, r, e, d in raw]


def _latest(con: duckdb.DuckDBPyConnection, table: str, order: str) -> str:
    return con.execute(f"SELECT run_id FROM meta.{table} ORDER BY {order} DESC LIMIT 1").fetchone()[0]  # type: ignore[index,no-any-return]


def build_snapshot(
    con: duckdb.DuckDBPyConnection, as_of: date, verified: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    rid = _latest(con, "dq_results", "checked_at")
    cols = [
        "check_id",
        "dataset",
        "dimension",
        "severity",
        "domain",
        "passed",
        "observed",
        "threshold",
        "detail",
    ]
    dq = [
        CheckResult(
            *[
                r[0],
                r[1],
                r[2],
                r[3],
                _dom(r[0]),
                bool(r[4]),
                r[5] if r[5] is not None else float("nan"),
                r[6],
                r[7],
            ]
        )
        for r in con.execute(
            "SELECT check_id, dataset, dimension, severity, passed, observed, threshold, detail FROM meta.dq_results WHERE run_id=? ORDER BY check_id",
            [rid],
        ).fetchall()
    ]
    dqs = summarise(dq)
    dqs["results"] = [{k: getattr(r, k) for k in cols} for r in dq]
    for r in dqs["results"]:
        if r["observed"] != r["observed"]:
            r["observed"] = None
    recon_rows = con.execute(
        "SELECT measure, system_a, value_a, system_b, value_b, delta, delta_pct, tolerance_pct, status, root_cause FROM meta.recon_results WHERE run_id=?",
        [_latest(con, "recon_results", "checked_at")],
    ).fetchall()
    recon = [
        dict(
            zip(
                [
                    "measure",
                    "system_a",
                    "value_a",
                    "system_b",
                    "value_b",
                    "delta",
                    "delta_pct",
                    "tolerance_pct",
                    "status",
                    "root_cause",
                ],
                r,
                strict=True,
            )
        )
        for r in recon_rows
    ]
    inv = audit.load_inventory()
    fnd = audit.findings(inv)
    graph = lineage.build()
    model = semantic_model.build(con)
    sample_before = con.execute(
        "SELECT contact_key, email, first_name, phone FROM gold.dim_contact LIMIT 3"
    ).fetchall()
    masked, mcols = rbac.apply_policy(
        "data_engineer",
        "dim_contact",
        [dict(zip(["contact_key", "email", "first_name", "phone"], r, strict=True)) for r in sample_before],
    )
    snap: dict[str, Any] = {
        "as_of": as_of.isoformat(),
        "audit": {
            "findings": fnd,
            "baseline": audit.baseline(inv, dqs["score"]),
            "flow_map": audit.flow_map(inv),
            "inventory": inv,
            "by_category": _count(fnd, "category"),
            "by_severity": _count(fnd, "severity"),
        },
        "sor": {"matrix": sor.matrix_rows(), "conflicts": sor.conflicting_writers(inv["integrations"])},
        "architecture": {
            "layers": [{"name": n, "desc": d} for n, d in LAYERS],
            "platform": platform.recommendation(),
        },
        "pipeline": {
            "runs": [
                dict(zip(["task", "status", "rows_out", "secs"], r, strict=True))
                for r in con.execute(
                    "SELECT task, status, rows_out, round(date_diff('millisecond', started_at, finished_at)/1000.0, 2) FROM meta.pipeline_runs ORDER BY started_at"
                ).fetchall()
            ],
            "ingest": [
                dict(
                    zip(
                        ["batch", "dataset", "received", "inserted", "duplicate", "quarantined"],
                        r,
                        strict=True,
                    )
                )
                for r in con.execute(
                    "SELECT split_part(batch_id,'-',1), dataset, sum(rows_received), sum(rows_inserted), sum(rows_duplicate), sum(rows_quarantined) FROM meta.ingest_log GROUP BY 1,2 ORDER BY 1,2"
                ).fetchall()
            ],
            "schema_changes": [
                dict(zip(["dataset", "type", "detail", "severity"], r, strict=True))
                for r in con.execute(
                    "SELECT dataset, change_type, detail, severity FROM meta.schema_changes ORDER BY 1"
                ).fetchall()
            ],
            "health": monitor.health(con),
            "contracts": len(load_contracts()),
        },
        "quality": dqs,
        "recon": recon,
        "incidents": incidents.list_incidents(con),
        "governance": {
            "roles": [
                {"role": k, "max_class": v["max_class"], "datasets": v["datasets"], "unmask": v["unmask"]}
                for k, v in rbac.policies()["roles"].items()
            ],
            "masking_demo": {
                "as": "data_engineer",
                "masked_columns": mcols,
                "before": [list(r) for r in sample_before],
                "after": masked,
            },
            "audit_chain": audit_log.verify_chain(con),
            "retention_dry_run": retention.enforce(con, as_of),
        },
        "ai": {
            "tools": tools.tool_specs(),
            "usage": tools.usage_summary(con),
            "demo_search": index.search(con, "which patch products are visible on the web store", 3),
            "documents": con.execute("SELECT count(*) FROM gold.ai_documents WHERE approved").fetchone()[0],  # type: ignore[index]
        },
        "lineage": {
            "nodes": len(graph["nodes"]),
            "edges": len(graph["edges"]),
            "view": [
                {"from": a, "to": b}
                for a, b in lineage.collapsed_edges(graph, ("source", "gold", "consumer"))
            ],
            "nodes_view": [n for n in graph["nodes"] if n["layer"] in ("source", "gold", "consumer")],
        },
        "semantic": {
            "tables": [
                {
                    "name": t["name"],
                    "measures": [m["name"] for m in t["measures"]],
                    "columns": len(t["columns"]),
                }
                for t in model["model"]["tables"]
            ],
            "relationships": len(model["model"]["relationships"]),
            "roles": [r["name"] for r in model["model"]["roles"]],
            "valid": not semantic_model.validate(model),
        },
        "vendors": vendor.evaluate(),
        "plan": {
            "phases": plan.load()["phases"],
            "roadmap": plan.roadmap(),
            "budget": plan.budget(),
            "verification": verified or [],
        },
        "traceability": traceability(),
    }
    return snap


def _count(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for i in items:
        out[i[key]] = out.get(i[key], 0) + 1
    return out


def _dom(check_id: str) -> str:
    from emblem.quality.checks import load_checks

    return next((c["domain"] for c in load_checks() if c["id"] == check_id), "pipeline")
