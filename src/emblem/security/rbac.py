"""Role-based access control + column masking driven by data/governance/policies.yaml."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

import yaml

from emblem.contracts import DATA_DIR


class AccessDenied(Exception):
    pass


@lru_cache(maxsize=1)
def policies() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "governance" / "policies.yaml").read_text())


def role_names() -> list[str]:
    return list(policies()["roles"])


def column_class(dataset: str, column: str) -> str:
    return policies().get("columns", {}).get(dataset, {}).get(column, "internal")


def can_read(role: str, dataset: str) -> bool:
    r = policies()["roles"].get(role)
    return bool(r) and ("*" in r["datasets"] or dataset in r["datasets"])


def mask_value(value: Any, strategy: str) -> Any:
    if value is None:
        return None
    if strategy == "hash":
        return "h_" + hashlib.sha256(str(value).encode()).hexdigest()[:10]
    if strategy == "bucket":
        return "***"
    return "[REDACTED]"


def apply_policy(
    role: str, dataset: str, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (rows with masking applied, names of masked columns). Raises AccessDenied when the role may not read the dataset."""
    if not can_read(role, dataset):
        raise AccessDenied(f"role '{role}' may not read '{dataset}'")
    pol = policies()
    r = pol["roles"][role]
    rank = pol["classification_rank"]
    masked: list[str] = []
    out = [dict(x) for x in rows]
    for col in out[0].keys() if out else []:
        cls = column_class(dataset, col)
        if cls in r["unmask"] or rank[cls] <= rank["internal"]:
            continue
        strategy = pol["masking"].get(cls, "redact")
        if rank[cls] > rank[r["max_class"]]:
            strategy = "redact"  # not even entitled to a pseudonym
        masked.append(col)
        for row in out:
            row[col] = mask_value(row[col], strategy)
    return out, masked
