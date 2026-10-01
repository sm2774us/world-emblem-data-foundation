"""Tiny dbt-style SQL model runner: {{ ref('x') }} resolution, DAG ordering, cycle detection, lineage source."""

from __future__ import annotations

import re
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).parent.parent / "data" / "sql"
REF_RE = re.compile(r"\{\{\s*ref\('([a-z0-9_]+)'\)\s*\}\}")
REF_TABLES = {"locations", "fx_rates"}
SILVER_EXTRA = {"xref_company"}


@dataclass(frozen=True)
class Model:
    name: str
    layer: str
    sql: str
    refs: tuple[str, ...]


def schema_of(name: str, gold_models: set[str]) -> str:
    if name in gold_models:
        return "gold"
    if name.startswith("stg_") or name in SILVER_EXTRA:
        return "silver"
    if name in REF_TABLES:
        return "ref"
    raise KeyError(f"unknown ref '{name}'")


def load_models(sql_dir: Path = SQL_DIR) -> dict[str, Model]:
    out: dict[str, Model] = {}
    for p in sorted((sql_dir / "gold").glob("*.sql")):
        text = p.read_text()
        out[p.stem] = Model(p.stem, "gold", text, tuple(dict.fromkeys(REF_RE.findall(text))))
    return out


def execution_order(models: dict[str, Model]) -> list[str]:
    graph = {m.name: {r for r in m.refs if r in models} for m in models.values()}
    try:
        return list(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise ValueError(f"cycle in SQL models: {exc.args[1]}") from exc


def render(model: Model, gold: set[str]) -> str:
    return REF_RE.sub(lambda m: f"{schema_of(m.group(1), gold)}.{m.group(1)}", model.sql)


def run_models(con: duckdb.DuckDBPyConnection, models: dict[str, Model] | None = None) -> dict[str, int]:
    models = models or load_models()
    gold = set(models)
    counts: dict[str, int] = {}
    for name in execution_order(models):
        con.execute(f"CREATE OR REPLACE TABLE gold.{name} AS {render(models[name], gold)}")
        counts[name] = con.execute(f"SELECT count(*) FROM gold.{name}").fetchone()[0]  # type: ignore[index]
    return counts
