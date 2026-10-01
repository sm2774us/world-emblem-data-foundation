"""Phase 1: current-state audit. Turns the system/integration inventory into scored findings and a baseline."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from emblem.architecture import sor
from emblem.contracts import DATA_DIR

SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
CRITICAL_DOMAINS = {"order", "revenue", "inventory", "company"}
WEAK_SECRETS = {"plaintext_config", "personal_token", "shared_service_account"}
DIRECT = {"direct_prod_query", "db_link"}


@lru_cache(maxsize=1)
def load_inventory() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "catalog" / "system_inventory.yaml").read_text())  # type: ignore[no-any-return]


def _f(cat: str, sev: str, subject: str, desc: str, fix: str, evidence: str = "") -> dict[str, Any]:
    return {
        "category": cat,
        "severity": sev,
        "subject": subject,
        "description": desc,
        "remediation": fix,
        "evidence": evidence,
    }


def findings(inv: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    inv = inv or load_inventory()
    out: list[dict[str, Any]] = []
    for kind in ("systems", "integrations", "jobs", "reports"):
        for x in inv[kind]:
            if not x.get("owner"):
                sev = "high" if x.get("criticality") == "critical" or kind == "integrations" else "medium"
                out.append(
                    _f(
                        "missing_ownership",
                        sev,
                        x["id"],
                        f"{kind[:-1]} '{x['name']}' has no accountable owner",
                        "D1-30: assign owner in the catalog; RACI in D31-60",
                    )
                )
    for i in inv["integrations"]:
        crit = bool(set(i["domains"]) & CRITICAL_DOMAINS)
        weak = [
            n
            for n, ok in (
                ("retries", i["retries"]),
                ("idempotency", i["idempotent"]),
                ("monitoring", i["monitored"]),
                ("documentation", i["documented"]),
            )
            if not ok
        ]
        if weak:
            out.append(
                _f(
                    "weak_controls",
                    "high" if crit and len(weak) >= 3 else "medium",
                    i["id"],
                    f"{i['name']}: missing {', '.join(weak)}",
                    "Rebuild on governed pipeline pattern (retries, idempotent upsert, alerting, runbook)",
                    f"domains={i['domains']}",
                )
            )
        if i["secret_store"] in WEAK_SECRETS:
            out.append(
                _f(
                    "security_risk",
                    "critical" if i["secret_store"] in ("plaintext_config", "personal_token") else "high",
                    i["id"],
                    f"{i['name']}: credentials held as {i['secret_store']}",
                    "Move to vault/Key Vault; rotate; scope least privilege",
                )
            )
        if i["mechanism"] in DIRECT:
            out.append(
                _f(
                    "security_risk",
                    "high",
                    i["id"],
                    f"{i['name']}: direct access to production systems",
                    "Replace with governed gold-layer access; revoke direct grants",
                )
            )
        if i["mechanism"] in ("manual_export", "csv_file_drop"):
            out.append(
                _f(
                    "manual_work",
                    "medium",
                    i["id"],
                    f"{i['name']}: {i['mechanism']} on {i['schedule']} schedule",
                    "Automate extraction; remove human step",
                )
            )
        if i["schema_coupled"] and not i["retries"] and not i["documented"]:
            out.append(
                _f(
                    "fragile_integration",
                    "high" if crit else "medium",
                    i["id"],
                    f"{i['name']}: schema-coupled, undocumented, no retry",
                    "Introduce data contract + drift detection",
                )
            )
    for r in inv["reports"]:
        if r["manual_steps"]:
            out.append(
                _f(
                    "manual_work",
                    "medium",
                    r["id"],
                    f"report '{r['name']}' relies on manual steps",
                    "Source from governed mart/semantic model",
                )
            )
    for w in sor.conflicting_writers(inv["integrations"]):
        out.append(
            _f(
                "duplicate_data",
                "high",
                w["integration"],
                f"{w['from']} writes '{w['domain']}' into its system of record {w['to']}",
                "Single-writer rule: authority -> others; field-level exceptions only",
            )
        )
    pairs: dict[tuple[str, str], list[str]] = {}
    for i in inv["integrations"]:
        pairs.setdefault(tuple(sorted((i["from"], i["to"]))), []).append(i["id"])  # type: ignore[arg-type]
    for pair, ids in pairs.items():
        if len(ids) > 1:
            out.append(
                _f(
                    "duplicate_data",
                    "medium",
                    "+".join(ids),
                    f"{pair[0]}<->{pair[1]} connected by {len(ids)} overlapping integrations",
                    "Consolidate to one governed flow per direction",
                )
            )
    by_domain: dict[str, set[str]] = {}
    for s in inv["systems"]:
        for d in s["domains"]:
            by_domain.setdefault(d, set()).add(s["id"])
    for d, systems in sorted(by_domain.items()):
        if len(systems) > 1 and d in CRITICAL_DOMAINS:
            out.append(
                _f(
                    "reconciliation_gap",
                    "high",
                    d,
                    f"'{d}' lives in {len(systems)} systems with no reconciliation job",
                    "Automated reconciliation with tolerance + incident routing",
                    ", ".join(sorted(systems)),
                )
            )
    for n, f in enumerate(sorted(out, key=lambda f: -SEV_RANK[f["severity"]]), start=1):
        f["id"] = f"F-{n:03d}"
    return sorted(out, key=lambda f: (-SEV_RANK[f["severity"]], f["id"]))


def baseline(inv: dict[str, Any] | None = None, dq_score: float | None = None) -> dict[str, Any]:
    inv = inv or load_inventory()
    ints = inv["integrations"]
    pct = lambda n, d: round(100 * n / d, 1) if d else 0.0  # noqa: E731
    owned = [x for k in ("systems", "integrations", "jobs", "reports") for x in inv[k]]
    return {
        "reliability_pct": pct(
            sum(i["retries"] + i["idempotent"] + i["monitored"] for i in ints), 3 * len(ints)
        ),
        "security_pct": pct(
            sum(i["secret_store"] not in WEAK_SECRETS and i["mechanism"] not in DIRECT for i in ints),
            len(ints),
        ),
        "documentation_pct": pct(sum(i["documented"] for i in ints), len(ints)),
        "ownership_pct": pct(sum(bool(x.get("owner")) for x in owned), len(owned)),
        "automation_pct": pct(
            sum(i["mechanism"] not in ("manual_export", "csv_file_drop") for i in ints)
            + sum(not r["manual_steps"] for r in inv["reports"]),
            len(ints) + len(inv["reports"]),
        ),
        "data_quality_pct": None if dq_score is None else round(dq_score * 100, 1),
        "counts": {
            "systems": len(inv["systems"]),
            "integrations": len(ints),
            "jobs": len(inv["jobs"]),
            "reports": len(inv["reports"]),
        },
    }


def flow_map(inv: dict[str, Any] | None = None) -> dict[str, Any]:
    inv = inv or load_inventory()
    nodes = [
        {
            "id": s["id"],
            "label": s["name"],
            "type": s["type"],
            "owner": s["owner"],
            "criticality": s["criticality"],
        }
        for s in inv["systems"]
    ]
    edges = []
    for i in inv["integrations"]:
        controls = i["retries"] + i["idempotent"] + i["monitored"] + i["documented"]
        edges.append(
            {
                "id": i["id"],
                "from": i["from"],
                "to": i["to"],
                "label": i["mechanism"],
                "domains": i["domains"],
                "health": "red" if controls <= 1 else "amber" if controls <= 2 else "green",
            }
        )
    return {"nodes": nodes, "edges": edges}
