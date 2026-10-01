"""Data contracts: load, validate, diff (schema governance) and normalise raw payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).parent / "data"
VALID_TYPES = {"VARCHAR", "DOUBLE", "INTEGER", "DATE", "TIMESTAMP", "BOOLEAN"}
CLASSES = ("public", "internal", "confidential", "pii", "restricted")


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    required: bool = False
    cls: str = "internal"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Contract:
    id: str
    source: str
    owner: str
    pk: str
    updated_at: str
    freshness_hours: int
    retention_days: int
    columns: tuple[Column, ...] = field(default_factory=tuple)

    @property
    def table(self) -> str:
        return self.id.replace(".", "__")

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Column:
        return next(c for c in self.columns if c.name == name)


@lru_cache(maxsize=1)
def load_contracts(path: Path | None = None) -> dict[str, Contract]:
    raw = yaml.safe_load((path or DATA_DIR / "contracts" / "contracts.yaml").read_text())
    out: dict[str, Contract] = {}
    for d in raw["datasets"]:
        cols = tuple(
            Column(
                n,
                v["type"],
                v.get("required", False),
                v.get("class", "internal"),
                tuple(v.get("aliases", [])),
            )
            for n, v in d["columns"].items()
        )
        out[d["id"]] = Contract(
            d["id"],
            d["source"],
            d["owner"],
            d["pk"],
            d["updated_at"],
            d["freshness_hours"],
            d["retention_days"],
            cols,
        )
    validate_contracts(out)
    return out


def validate_contracts(contracts: dict[str, Contract]) -> None:
    for c in contracts.values():
        names = c.column_names
        if c.pk not in names or c.updated_at not in names:
            raise ValueError(f"{c.id}: pk/updated_at must be declared columns")
        if len(set(names)) != len(names):
            raise ValueError(f"{c.id}: duplicate column names")
        for col in c.columns:
            if col.type not in VALID_TYPES or col.cls not in CLASSES:
                raise ValueError(f"{c.id}.{col.name}: invalid type or classification")
        if not c.column(c.pk).required:
            raise ValueError(f"{c.id}: primary key must be required")


@dataclass
class Normalised:
    payload: dict[str, Any]
    renamed: dict[str, str]
    added: list[str]
    missing_required: list[str]


def normalise(contract: Contract, record: dict[str, Any]) -> Normalised:
    """Apply aliases (known renames), flag additive drift and missing required fields."""
    payload = dict(record)
    renamed: dict[str, str] = {}
    for col in contract.columns:
        if col.name not in payload:
            for alias in col.aliases:
                if alias in payload:
                    payload[col.name] = payload.pop(alias)
                    renamed[alias] = col.name
                    break
    known = set(contract.column_names)
    added = sorted(set(payload) - known)
    missing = [c.name for c in contract.columns if c.required and payload.get(c.name) in (None, "")]
    return Normalised(payload, renamed, added, missing)


def diff_contracts(old: Contract, new: Contract) -> dict[str, list[str]]:
    """Classify a proposed schema change. Breaking = removal, type change, optional->required."""
    o = {c.name: c for c in old.columns}
    n = {c.name: c for c in new.columns}
    breaking = [f"removed:{k}" for k in o if k not in n]
    breaking += [f"type:{k}" for k in o if k in n and o[k].type != n[k].type]
    breaking += [f"now_required:{k}" for k in o if k in n and not o[k].required and n[k].required]
    breaking += [f"pk_changed:{new.id}"] if old.pk != new.pk else []
    additive = [f"added:{k}" for k in n if k not in o]
    return {"breaking": breaking, "additive": additive}
