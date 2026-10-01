"""Lineage graph: source -> bronze -> silver -> gold -> consumers, derived from contracts and SQL refs (never hand-drawn)."""

from __future__ import annotations

from typing import Any

from emblem.contracts import load_contracts
from emblem.pipelines import sqlmodels
from emblem.pipelines.staging import staging_name

CONSUMERS = {  # gold asset -> downstream consumers
    "mart_revenue_monthly": ["powerbi:Revenue", "api:/v1/datasets"],
    "mart_company_360": ["powerbi:Customer360", "ai:company_summary"],
    "dim_product": ["ai:product_availability", "api:/v1/datasets"],
    "fact_inventory_snapshot": ["ai:product_availability", "powerbi:Inventory"],
    "mart_marketing_roi": ["powerbi:Marketing"],
    "fact_revenue": ["powerbi:Revenue"],
    "forecast_revenue": ["powerbi:Revenue"],
}


def build() -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    def node(i: str, layer: str, owner: str = "") -> None:
        nodes.setdefault(i, {"id": i, "layer": layer, "owner": owner})

    for c in load_contracts().values():
        src, brz, stg = f"source:{c.source}", f"bronze:{c.table}", f"silver:{staging_name(c)}"
        node(src, "source", c.owner)
        node(brz, "bronze", c.owner)
        node(stg, "silver", c.owner)
        edges += [{"from": src, "to": brz}, {"from": brz, "to": stg}]
    node("silver:xref_company", "silver", "Finance")
    for c_id in ("bc__customers", "hs__companies", "bg__customers", "opti__quotes"):
        edges.append({"from": f"silver:stg_{c_id}", "to": "silver:xref_company"})
    for m in sqlmodels.load_models().values():
        node(f"gold:{m.name}", "gold", "Data Platform")
        for r in m.refs:
            sch = sqlmodels.schema_of(r, set(sqlmodels.load_models()))
            node(f"{sch}:{r}", sch)
            edges.append({"from": f"{sch}:{r}", "to": f"gold:{m.name}"})
    node("gold:forecast_revenue", "gold", "Data Platform")
    edges.append({"from": "gold:mart_revenue_monthly", "to": "gold:forecast_revenue"})
    node("gold:ai_documents", "gold", "Data Platform")
    for up in ("gold:dim_product", "gold:mart_company_360"):
        edges.append({"from": up, "to": "gold:ai_documents"})
    CONSUMERS["ai_documents"] = ["ai:search"]
    for g, cons in CONSUMERS.items():
        for cn in cons:
            node(cn, "consumer", "Data Platform")
            edges.append({"from": f"gold:{g}", "to": cn})
    return {"nodes": list(nodes.values()), "edges": edges}


def upstream(graph: dict[str, Any], target: str) -> set[str]:
    rev: dict[str, list[str]] = {}
    for e in graph["edges"]:
        rev.setdefault(e["to"], []).append(e["from"])
    seen: set[str] = set()
    stack = [target]
    while stack:
        for p in rev.get(stack.pop(), []):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen


def collapsed_edges(graph: dict[str, Any], layers: tuple[str, ...]) -> list[tuple[str, str]]:
    """Edges between nodes of the visible layers, collapsing hidden intermediate layers."""
    keep = {n["id"] for n in graph["nodes"] if n["layer"] in layers}
    adj: dict[str, list[str]] = {}
    for e in graph["edges"]:
        adj.setdefault(e["from"], []).append(e["to"])
    seen: set[tuple[str, str]] = set()
    for s in keep:
        stack, vis = list(adj.get(s, [])), set()
        while stack:
            t = stack.pop()
            if t in vis:
                continue
            vis.add(t)
            if t in keep:
                seen.add((s, t))
            else:
                stack += adj.get(t, [])
    return sorted(seen)


def mermaid(graph: dict[str, Any], layers: tuple[str, ...] = ("source", "gold", "consumer")) -> str:
    keep = sorted(n["id"] for n in graph["nodes"] if n["layer"] in layers)
    ids = {n: f"n{i}" for i, n in enumerate(keep)}
    lines = ["flowchart LR"] + [f'  {v}["{k}"]' for k, v in ids.items()]
    return "\n".join(lines + [f"  {ids[a]} --> {ids[b]}" for a, b in collapsed_edges(graph, layers)])
