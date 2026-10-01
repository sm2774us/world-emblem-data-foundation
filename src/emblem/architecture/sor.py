"""System-of-record matrix: load, validate against the inventory and render."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from emblem.contracts import DATA_DIR


@lru_cache(maxsize=1)
def load_sor() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "architecture" / "system_of_record.yaml").read_text())["domains"]


def authoritative(domain: str, field: str | None = None) -> str:
    d = load_sor()[domain]
    return d["fields"].get(field, d["authority"]) if field else d["authority"]


def validate(systems: list[dict[str, Any]], integrations: list[dict[str, Any]]) -> list[str]:
    """Return violations. Rules: authority exists and hosts the domain; one owner; no non-authority writes into the authority for the domain."""
    errors: list[str] = []
    sysmap = {s["id"]: s for s in systems}
    for name, d in load_sor().items():
        auth = sysmap.get(d["authority"])
        if auth is None:
            errors.append(f"{name}: authority '{d['authority']}' is not an inventoried system")
        elif name not in auth["domains"]:
            errors.append(f"{name}: authority '{d['authority']}' does not host the domain")
        if not d.get("owner"):
            errors.append(f"{name}: no business owner")
        for f, sysid in d["fields"].items():
            if sysid not in sysmap:
                errors.append(f"{name}.{f}: unknown system '{sysid}'")
    return errors


def conflicting_writers(integrations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Integrations that push a domain INTO its authority from a non-authority (risk of overwriting golden data)."""
    sor = load_sor()
    out = []
    for i in integrations:
        for dom in i["domains"]:
            if (
                dom in sor
                and i["to"] == sor[dom]["authority"]
                and i["from"] != sor[dom]["authority"]
                and i["from"] not in sor[dom]["fields"].values()
            ):
                out.append({"integration": i["id"], "domain": dom, "from": i["from"], "to": i["to"]})
    return out


def matrix_rows() -> list[dict[str, Any]]:
    return [
        {
            "domain": k,
            "owner": v["owner"],
            "authority": v["authority"],
            "identifier": v["identifier"],
            "field_overrides": v["fields"],
        }
        for k, v in load_sor().items()
    ]
