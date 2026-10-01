"""Governed retrieval index: only approved, non-PII business knowledge is embedded. Retrieval carries citations."""

from __future__ import annotations

from typing import Any

import duckdb
import yaml

from emblem.ai.embeddings import embed
from emblem.contracts import DATA_DIR

APPROVED_CLASSES = {"public", "internal"}


def build_documents(con: duckdb.DuckDBPyConnection) -> int:
    docs: list[tuple[str, str, str, str, str]] = []
    for sku, desc, fam, price, web in con.execute(
        "SELECT sku, description, family, list_price, web_published FROM gold.dim_product"
    ).fetchall():
        docs.append(
            (
                f"product:{sku}",
                "product",
                f"{sku} {desc}",
                f"Product {sku}: {desc}, family {fam}, list price ${price:.2f}, {'visible' if web else 'hidden'} on the web store.",
                "internal",
            )
        )
    for name, stage, rev, orders in con.execute(
        "SELECT company_name, lifecycle_stage, revenue_usd, orders FROM gold.mart_company_360"
    ).fetchall():
        docs.append(
            (
                f"company:{name}",
                "company",
                name,
                f"Company {name}: lifecycle {stage or 'unknown'}, {orders} orders, revenue ${rev:,.0f}.",
                "internal",
            )
        )
    for t in yaml.safe_load((DATA_DIR / "catalog" / "glossary.yaml").read_text())["terms"]:
        docs.append(
            (
                f"glossary:{t['term']}",
                "glossary",
                t["term"],
                f"{t['term']} (owner {t['owner']}): {t['definition']}",
                "public",
            )
        )
    con.execute(
        "CREATE OR REPLACE TABLE gold.ai_documents(doc_id VARCHAR, kind VARCHAR, title VARCHAR, text VARCHAR, classification VARCHAR, "
        "approved BOOLEAN, embedding FLOAT[])"
    )
    for d in docs:
        con.execute(
            "INSERT INTO gold.ai_documents VALUES (?,?,?,?,?,?,?)",
            [*d, d[4] in APPROVED_CLASSES, embed(d[3])],
        )
    return len(docs)


def search(con: duckdb.DuckDBPyConnection, query: str, k: int = 5) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT doc_id, kind, title, text, list_cosine_similarity(embedding, ?::FLOAT[]) AS score FROM gold.ai_documents "
        "WHERE approved ORDER BY score DESC LIMIT ?",
        [embed(query), k],
    ).fetchall()
    return [
        {
            "doc_id": r[0],
            "kind": r[1],
            "title": r[2],
            "text": r[3],
            "score": round(float(r[4]), 4),
            "citation": f"gold.ai_documents/{r[0]}",
        }
        for r in rows
    ]
