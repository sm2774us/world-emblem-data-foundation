import pytest

from emblem.ai import embeddings, index, tools
from emblem.ops import incidents
from emblem.plan import plan
from emblem.quality.checks import CheckResult
from emblem.quality.reconcile import Recon
from emblem.security import rbac


def test_embeddings_deterministic_normalised_and_similar():
    a, b, c = (
        embeddings.embed("embroidered patch pricing"),
        embeddings.embed("embroidered patch pricing"),
        embeddings.embed("quarterly tax filing"),
    )
    dot = lambda x, y: sum(p * q for p, q in zip(x, y, strict=True))  # noqa: E731
    assert (
        a == b
        and abs(dot(a, a) - 1) < 1e-9
        and dot(a, embeddings.embed("patch embroidered price")) > dot(a, c)
    )


def test_search_is_governed_no_pii(demo_con):
    hits = index.search(demo_con, "Sum of posted sales invoices in Business Central converted to USD", 3)
    assert hits[0]["doc_id"] == "glossary:Revenue" and hits[0]["citation"].startswith("gold.ai_documents/")
    assert demo_con.execute("SELECT count(*) FROM gold.ai_documents WHERE text LIKE '%@%'").fetchone()[0] == 0
    assert demo_con.execute("SELECT count(*) FROM gold.ai_documents WHERE NOT approved").fetchone()[0] == 0


def test_agent_tools_allowlist_rbac_and_usage_log(demo_con):
    ok = tools.call(demo_con, "agent-x", "ai_agent", "product_availability", "WE-1003")
    assert ok["rows"] and ok["masked_columns"] == []
    with pytest.raises(rbac.AccessDenied):
        tools.call(demo_con, "agent-x", "ai_agent", "order_status", "SO200001")
    with pytest.raises(KeyError):
        tools.call(demo_con, "agent-x", "ai_agent", "drop_tables", "x")
    s = tools.usage_summary(demo_con, max_denied=1)
    assert any(u["denied"] for u in s["usage"]) and s["flags"]
    assert {t["name"] for t in tools.tool_specs()} == set(tools.TOOLS)


def _chk(cid, passed, sev="error", domain="order"):
    return CheckResult(
        cid, "ds", "accuracy", sev, domain, passed, 1.0, 0.0, "d", "fix it at source", "bad-values"
    )


def test_severity_matrix_and_ladder():
    assert incidents.severity("critical", "marketing") == 1 and incidents.severity("warning", "order") == 2
    assert incidents.severity("warning", "marketing") == 3 and incidents.severity("error", "order") == 2
    assert [s for _, s in incidents.LADDER[1]][-1] == "CTO" and len(incidents.LADDER[3]) == 2


def test_incidents_idempotent_route_owner_and_autoresolve(fresh_con):
    r = Recon("revenue", "a", 100.0, "b", 80.0, 0.5, "cause", "revenue", "Finance")
    incidents.open_incidents(fresh_con, [_chk("c1", False)], [r])
    incidents.open_incidents(fresh_con, [_chk("c1", False)], [r])
    rows = incidents.list_incidents(fresh_con, "open")
    assert (
        len(rows) == 2
        and {x["owner"] for x in rows} == {"Finance"}
        and all(x["escalation"] and x["source_fix_action"] for x in rows)
    )
    assert any(x["severity"] == "SEV1" for x in rows)
    incidents.open_incidents(
        fresh_con,
        [_chk("c1", True)],
        [Recon("revenue", "a", 100.0, "b", 100.0, 0.5, "", "revenue", "Finance")],
    )
    assert (
        incidents.list_incidents(fresh_con, "open") == []
        and len(incidents.list_incidents(fresh_con, "resolved")) == 2
    )


def test_plan_structure_and_verifiers_cover_every_milestone():
    ms = plan.milestones()
    assert len(ms) == 14 and {m["phase"] for m in ms} == {"P1", "P2", "P3"}
    assert all(
        m["verify"] in plan.VERIFIERS and len(m["steps"]) >= 2 and m["changes"] and m["exit_criteria"]
        for m in ms
    )
    assert [p["days"] for p in plan.load()["phases"]] == ["1-30", "31-60", "61-90"]


def test_roadmap_ranking_budget_and_rendered_doc_in_sync():
    r = plan.roadmap()
    assert r == sorted(r, key=lambda x: (-x["priority"], x["id"])) and r[0]["priority"] == max(
        x["priority"] for x in r
    )
    b = plan.budget()
    assert b["total_low"] == 175000 and b["total_high"] == 305000
    doc = (plan.REPO_ROOT / "docs" / "90-DAY-PLAN.md").read_text()
    assert doc.strip() == plan.render_markdown().strip(), "run: uv run emblem docs"


def test_every_milestone_verifies_against_the_live_platform(demo_con):
    res = plan.verify(plan.Ctx(demo_con))
    failed = [r for r in res if not r["ok"]]
    assert not failed, failed
