"""The 90-day plan as executable data: load, validate, verify against the running platform, render Markdown."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import yaml

from emblem.architecture import platform, sor
from emblem.catalog import audit, lineage
from emblem.contracts import DATA_DIR
from emblem.governance import vendor
from emblem.ops.incidents import list_incidents, runbook_exists
from emblem.ops.monitor import prometheus
from emblem.reporting import semantic_model
from emblem.security import audit as audit_log
from emblem.security import rbac, retention

REPO_ROOT = Path(__file__).resolve().parents[3]


def load() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "plan" / "plan_90_day.yaml").read_text())  # type: ignore[no-any-return]


def milestones(plan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    plan = plan or load()
    return [{**m, "phase": p["id"], "phase_name": p["name"]} for p in plan["phases"] for m in p["milestones"]]


def roadmap(plan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    items = (plan or load())["roadmap"]
    ranked = [{**i, "priority": round((i["value"] + i["risk"] + i["ai"]) / i["effort"], 2)} for i in items]
    return sorted(ranked, key=lambda r: (-r["priority"], r["id"]))


def budget(plan: dict[str, Any] | None = None) -> dict[str, Any]:
    b = (plan or load())["budget"]
    return {
        **b,
        "total_low": sum(x["low"] for x in b["lines"]),
        "total_high": sum(x["high"] for x in b["lines"]),
    }


@dataclass
class Ctx:
    con: duckdb.DuckDBPyConnection
    root: Path = REPO_ROOT
    as_of: date = date(2026, 9, 30)


Verifier = Callable[[Ctx], tuple[bool, str]]


def _tables(c: Ctx, schema: str) -> set[str]:
    return {
        r[0]
        for r in c.con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema=?", [schema]
        ).fetchall()
    }


def v_audit(c: Ctx) -> tuple[bool, str]:
    inv, f = audit.load_inventory(), audit.findings()
    ok = len(inv["systems"]) >= 6 and all(s.get("admin") for s in inv["systems"]) and len(f) >= 10
    return ok, f"{len(inv['systems'])} systems, {len(inv['integrations'])} integrations, {len(f)} findings"


def v_glossary(c: Ctx) -> tuple[bool, str]:
    import yaml as _y

    terms = _y.safe_load((DATA_DIR / "catalog" / "glossary.yaml").read_text())["terms"]
    gold = _tables(c, "gold")
    return all(t["owner"] and t["model"] in gold for t in terms), f"{len(terms)} terms owned and implemented"


def v_flows(c: Ctx) -> tuple[bool, str]:
    g = lineage.build()
    sources = {n["id"] for n in g["nodes"] if n["layer"] == "source"}
    reach = {
        s
        for s in sources
        if any(
            s in lineage.upstream(g, f"gold:{m}")
            for m in (
                "mart_revenue_monthly",
                "mart_company_360",
                "fact_order_line",
                "fact_inventory_snapshot",
                "fact_production",
                "mart_marketing_roi",
            )
        )
    }
    red = [e for e in audit.flow_map()["edges"] if e["health"] == "red"]
    return reach == sources, f"{len(reach)}/{len(sources)} sources reach gold; {len(red)} red integrations"


def v_baseline(c: Ctx) -> tuple[bool, str]:
    n = c.con.execute("SELECT count(*) FROM meta.dq_results").fetchone()[0]  # type: ignore[index]
    r = c.con.execute("SELECT count(*) FROM meta.recon_results").fetchone()[0]  # type: ignore[index]
    return n >= 20 and r >= 5, f"{n} check results, {r} reconciliations persisted"


def v_sor(c: Ctx) -> tuple[bool, str]:
    inv = audit.load_inventory()
    errs = sor.validate(inv["systems"], inv["integrations"])
    return (
        not errs,
        f"{len(sor.load_sor())} domains valid; {len(sor.conflicting_writers(inv['integrations']))} conflicting writers flagged",
    )


def v_entities(c: Ctx) -> tuple[bool, str]:
    need = {
        "dim_company",
        "dim_contact",
        "dim_product",
        "dim_location",
        "fact_order_line",
        "fact_revenue",
        "fact_inventory_snapshot",
        "fact_production",
    }
    have = need & _tables(c, "gold")
    dup = c.con.execute("SELECT count(*) - count(DISTINCT company_key) FROM gold.dim_company").fetchone()[0]  # type: ignore[index]
    return have == need and dup == 0, f"{len(have)}/8 entities; company_key duplicates={dup}"


def v_arch(c: Ctx) -> tuple[bool, str]:
    rec = platform.recommendation()
    top_share = max(rec["sensitivity"]["win_share"].values())
    return (
        (c.root / "docs" / "ARCHITECTURE.md").exists() and rec["winner"]["score"] > 0,
        f"recommended {rec['winner']['label']} ({rec['winner']['score']}); wins {top_share:.0%} of weight perturbations",
    )


def v_gov(c: Ctx) -> tuple[bool, str]:
    rows = [{"email": "a@b.com", "first_name": "A"}]
    masked_rows, cols = rbac.apply_policy("sales_rep", "dim_contact", rows)
    denied = False
    try:
        rbac.apply_policy("marketing_analyst", "dim_contact", rows)
    except rbac.AccessDenied:
        denied = True
    audit_log.record(c.con, "plan-verify", "admin", "verify", "governance")
    chain = audit_log.verify_chain(c.con)
    ret = retention.enforce(c.con, c.as_of)
    return (
        denied and chain["valid"] and ret["applied"] is False and masked_rows is not None and cols == [],
        f"RBAC deny ok; audit chain {chain['entries']} entries valid; retention dry-run ok",
    )


def v_roadmap(c: Ctx) -> tuple[bool, str]:
    r = roadmap()
    return len(r) >= 5 and r[0]["priority"] >= r[-1]["priority"], f"top: {r[0]['id']} {r[0]['name']}"


def v_pipeline(c: Ctx) -> tuple[bool, str]:
    from emblem.pipelines.bronze import ingest_dataset
    from emblem.sources.synthetic import NOW_ANCHOR, generate

    rows = generate(batch=1)["bc.items"]
    again = ingest_dataset(c.con, "bc.items", lambda: rows, "verify-replay", NOW_ANCHOR)
    n = c.con.execute("SELECT count(*) FROM gold.mart_revenue_monthly").fetchone()[0]  # type: ignore[index]
    g = lineage.build()
    return again["inserted"] == 0 and n > 0 and "source:business_central" in lineage.upstream(
        g, "gold:mart_revenue_monthly"
    ), f"replay inserted {again['inserted']} rows (idempotent); {n} governed revenue months"


def v_obs(c: Ctx) -> tuple[bool, str]:
    inc = list_incidents(c.con, "open")
    ok = bool(inc) and all(
        i["owner"] and i["escalation"] and runbook_exists(i["runbook"], c.root) for i in inc
    )
    return ok and "emblem_runs_total" in prometheus(
        c.con
    ), f"{len(inc)} open incidents, all with owner, runbook and escalation"


def v_ai(c: Ctx) -> tuple[bool, str]:
    from emblem.ai import index, tools

    n = c.con.execute("SELECT count(*) FROM gold.ai_documents WHERE approved").fetchone()[0]  # type: ignore[index]
    hit = index.search(c.con, "embroidered patch pricing", 1)
    denied = False
    try:
        tools.call(c.con, "verify-agent", "ai_agent", "order_status", "SO200001")
    except rbac.AccessDenied:
        denied = True
    model = semantic_model.build(c.con)
    return (
        n > 0 and bool(hit) and denied and not semantic_model.validate(model),
        f"{n} approved docs; agent denied on restricted dataset; semantic model valid ({len(model['model']['tables'])} tables)",
    )


def v_std(c: Ctx) -> tuple[bool, str]:
    rbs = {i["runbook"] for i in list_incidents(c.con)} | {"docs/runbooks/schema-drift.md"}
    ver = vendor.evaluate()
    ok = (
        (c.root / "docs" / "ENGINEERING-STANDARDS.md").exists()
        and all(runbook_exists(r, c.root) for r in rbs)
        and any(v["blockers"] for v in ver)
    )
    return ok, f"standards + {len(rbs)} runbooks present; vendor verdicts: " + "; ".join(
        f"{v['vendor']}={v['verdict']}" for v in ver
    )


def v_budget(c: Ctx) -> tuple[bool, str]:
    b = budget()
    return b["total_high"] > b["total_low"] > 0, f"annual run cost ${b['total_low']:,} - ${b['total_high']:,}"


VERIFIERS: dict[str, Verifier] = {
    "audit_inventory": v_audit,
    "glossary_owned": v_glossary,
    "flows_mapped": v_flows,
    "baseline": v_baseline,
    "sor_valid": v_sor,
    "common_entities": v_entities,
    "target_arch": v_arch,
    "governance_ok": v_gov,
    "roadmap_ranked": v_roadmap,
    "pipeline_governed": v_pipeline,
    "observability": v_obs,
    "ai_access": v_ai,
    "standards_vendor": v_std,
    "budget_ok": v_budget,
}


def verify(ctx: Ctx) -> list[dict[str, Any]]:
    out = []
    for m in milestones():
        try:
            ok, ev = VERIFIERS[m["verify"]](ctx)
        except Exception as exc:
            ok, ev = False, f"verifier error: {exc}"
        missing = [
            a
            for a in m["artifacts"]
            if not (ctx.root / a).exists()
            and not (Path(__file__).resolve().parents[1] / a.replace("src/emblem/", "")).exists()
        ]
        out.append(
            {
                "id": m["id"],
                "phase": m["phase"],
                "title": m["title"],
                "days": m["days"],
                "ok": ok and not missing,
                "evidence": ev,
                "missing_artifacts": missing,
            }
        )
    return out


def render_markdown(plan: dict[str, Any] | None = None) -> str:
    plan = plan or load()
    lines = [
        "# 90-Day Plan: Senior Data Engineer / Data Architect, World Emblem International",
        "",
        "> Generated from `src/emblem/data/plan/plan_90_day.yaml` by `uv run emblem plan render`. Do not edit by hand. Baselines marked *assumed* are hypotheses to confirm in Days 1-30.",
        "> Every milestone is verified by code: `uv run emblem plan verify`.",
        "",
    ]
    for p in plan["phases"]:
        lines += [f"## Days {p['days']}: {p['name']}", "", f"**Goal:** {p['goal']}", ""]
        for m in p["milestones"]:
            lines += [
                f"### {m['id']} (days {m['days']}): {m['title']}",
                "",
                f"**JD requirement:** {m['jd']}",
                "",
                "**Exact steps**",
                "",
            ]
            lines += [f"1. {s}" if i == 0 else f"{i + 1}. {s}" for i, s in enumerate(m["steps"])]
            lines += ["", "**Exact changes**", ""] + [f"- {c}" for c in m["changes"]]
            lines += [
                "",
                f"**Demonstrated by:** {', '.join(f'`{a}`' for a in m['artifacts'])}  ",
                f"**Run it:** `{m['command']}`  ",
                f"**Exit criteria:** {m['exit_criteria']}  ",
                f"**Metric:** {m['metric']['name']}: {m['metric']['baseline']} -> {m['metric']['target']}",
                "",
            ]
    lines += [
        "## Prioritised roadmap",
        "",
        "| Rank | ID | Item | Value | Risk | AI | Effort | Priority |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {n} | {r['id']} | {r['name']} | {r['value']} | {r['risk']} | {r['ai']} | {r['effort']} | {r['priority']} |"
        for n, r in enumerate(roadmap(plan), 1)
    ]
    b = budget(plan)
    lines += ["", "## Budget view (annual, USD)", "", "| Item | Low | High |", "|---|---|---|"] + [
        f"| {x['item']} | {x['low']:,} | {x['high']:,} |" for x in b["lines"]
    ]
    lines += [
        f"| **Total** | **{b['total_low']:,}** | **{b['total_high']:,}** |",
        "",
        "Assumptions: " + "; ".join(b["assumptions"]),
        "",
    ]
    return "\n".join(lines)
