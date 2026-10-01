from emblem.architecture import platform, sor
from emblem.catalog import audit, lineage
from emblem.governance import vendor
from emblem.reporting import semantic_model


def test_sor_valid_and_detects_conflicts():
    inv = audit.load_inventory()
    assert sor.validate(inv["systems"], inv["integrations"]) == []
    assert (
        sor.authoritative("company") == "business_central"
        and sor.authoritative("company", "owner_and_lifecycle") == "hubspot"
    )
    assert {c["integration"] for c in sor.conflicting_writers(inv["integrations"])} == {"INT-06"}
    broken = [
        {**s, "domains": [d for d in s["domains"] if d != "revenue"]} if s["id"] == "business_central" else s
        for s in inv["systems"]
    ]
    assert any("does not host" in e for e in sor.validate(broken, []))


def test_platform_ranking_deterministic_and_robust():
    cfg = platform.load()
    r = platform.score(cfg)
    assert r == platform.score(cfg) and r[0]["option"] == "microsoft_fabric" and r[0]["score"] > r[1]["score"]
    cost_heavy = {k: (0.9 if k == "total_cost" else 0.02) for k in cfg["criteria"]}
    assert platform.score(cfg, cost_heavy)[0]["option"] != "databricks"
    assert platform.sensitivity(cfg)["win_share"]["microsoft_fabric"] > 0.8


def test_audit_finds_every_category():
    cats = {f["category"] for f in audit.findings()}
    assert cats == {
        "missing_ownership",
        "weak_controls",
        "security_risk",
        "manual_work",
        "fragile_integration",
        "duplicate_data",
        "reconciliation_gap",
    }
    f = audit.findings()
    assert f[0]["severity"] in ("critical", "high") and len({x["id"] for x in f}) == len(f)


def test_baseline_bounds_and_flow_map():
    b = audit.baseline(dq_score=0.5)
    assert (
        all(
            0 <= b[k] <= 100
            for k in (
                "reliability_pct",
                "security_pct",
                "documentation_pct",
                "ownership_pct",
                "automation_pct",
            )
        )
        and b["data_quality_pct"] == 50.0
    )
    health = {e["id"]: e["health"] for e in audit.flow_map()["edges"]}
    assert health["INT-03"] != "red" and health["INT-01"] == "red"


def test_lineage_upstream_and_mermaid():
    g = lineage.build()
    up = lineage.upstream(g, "gold:mart_revenue_monthly")
    assert {"source:business_central", "silver:stg_bc__invoices", "bronze:bc__invoices"} <= up
    assert "flowchart LR" in lineage.mermaid(g)
    owned = [n for n in g["nodes"] if n["layer"] == "gold"]
    assert all(n["owner"] for n in owned)


def test_vendor_blockers_and_verdicts():
    a, b = vendor.evaluate()
    assert a["blockers"] == ["secrets_in_vault", "idempotency"] and a["verdict"].startswith("REJECT")
    assert b["blockers"] == ["idempotency"] and b["total"] > a["total"] and a["actions"]


def test_semantic_model_valid_and_catches_breakage(demo_con):
    m = semantic_model.build(demo_con)
    assert semantic_model.validate(m) == [] and len(m["model"]["relationships"]) == 7
    m["model"]["relationships"][0]["toColumn"] = "nope"
    m["model"]["tables"][0]["measures"].append({"name": "bad", "expression": "SUM(fact_revenue[ghost])"})
    errs = semantic_model.validate(m)
    assert any("nope" in e for e in errs) and any("ghost" in e for e in errs)
