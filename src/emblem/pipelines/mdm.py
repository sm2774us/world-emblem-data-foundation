"""Master data management: deterministic + fuzzy entity resolution for companies across systems."""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any

import duckdb

SUFFIXES = {"inc", "llc", "corp", "co", "ltd", "company", "corporation", "incorporated"}
FREE_MAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"}
FUZZY_THRESHOLD = 0.92


def normalise_name(name: str | None) -> str:
    tokens = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
    return " ".join(t for t in tokens if t not in SUFFIXES)


def email_domain(email: str | None, domain: str | None = None) -> str | None:
    d = domain or (email.split("@")[-1] if email and "@" in email else None)
    d = d.lower().strip() if d else None
    return None if not d or d in FREE_MAIL else d


class _UF:
    def __init__(self) -> None:
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)  # deterministic root => stable company_key


def candidates(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    q = {
        "bc": "SELECT 'bc', no, name, split_part(email,'@',2) FROM silver.stg_bc__customers",
        "hs": "SELECT 'hs', id, name, domain FROM silver.stg_hs__companies",
        "bg": "SELECT 'bg', id, company, split_part(email,'@',2) FROM silver.stg_bg__customers",
        "opti": "SELECT 'opti', id, company_name, split_part(contact_email,'@',2) FROM silver.stg_opti__quotes",
    }
    out: list[dict[str, Any]] = []
    for sql in q.values():
        for src, sid, name, dom in con.execute(sql).fetchall():
            out.append(
                {
                    "source": src,
                    "source_id": str(sid),
                    "name": name,
                    "norm": normalise_name(name),
                    "domain": email_domain(None, dom),
                }
            )
    return out


def resolve(con: duckdb.DuckDBPyConnection) -> dict[str, float | int]:
    recs = candidates(con)
    uf = _UF()
    key = lambda r: f"{r['source']}:{r['source_id']}"  # noqa: E731
    by_name: dict[str, list[dict[str, Any]]] = {}
    by_dom: dict[str, list[dict[str, Any]]] = {}
    for r in recs:
        uf.find(key(r))
        if r["norm"]:
            by_name.setdefault(r["norm"], []).append(r)
        if r["domain"]:
            by_dom.setdefault(r["domain"], []).append(r)
    rule: dict[str, tuple[str, float]] = {}
    for rule_name, conf, groups in (("exact_name", 1.0, by_name), ("shared_domain", 0.95, by_dom)):
        for grp in groups.values():
            for r in grp[1:]:
                uf.union(key(grp[0]), key(r))
            if len(grp) > 1:
                for r in grp:
                    rule.setdefault(key(r), (rule_name, conf))
    # multi-key blocking (prefix AND suffix) so a dropped leading letter ("mridian") cannot hide a match
    blocks: dict[str, list[dict[str, Any]]] = {}
    for r in recs:
        if r["norm"]:
            blocks.setdefault("p:" + r["norm"][:3], []).append(r)
            blocks.setdefault("s:" + r["norm"][-3:], []).append(r)
    seen: set[tuple[str, str]] = set()
    for grp in blocks.values():
        for i, a in enumerate(grp):
            for b in grp[i + 1 :]:
                pair = (min(key(a), key(b)), max(key(a), key(b)))
                if pair in seen or uf.find(key(a)) == uf.find(key(b)):
                    continue
                seen.add(pair)
                ratio = SequenceMatcher(None, a["norm"], b["norm"]).ratio()
                if ratio >= FUZZY_THRESHOLD:
                    uf.union(key(a), key(b))
                    rule.setdefault(key(a), ("fuzzy_name", round(ratio, 3)))
                    rule.setdefault(key(b), ("fuzzy_name", round(ratio, 3)))
    rows = []
    for r in recs:
        root = uf.find(key(r))
        ck = "co_" + hashlib.sha1(root.encode()).hexdigest()[:12]  # noqa: S324 - identifier, not security
        rname, conf = rule.get(key(r), ("singleton", 1.0))
        rows.append((r["source"], r["source_id"], ck, rname, conf, r["norm"]))
    con.execute(
        "CREATE OR REPLACE TABLE silver.xref_company(source VARCHAR, source_id VARCHAR, company_key VARCHAR, match_rule VARCHAR, "
        "confidence DOUBLE, norm_name VARCHAR)"
    )
    con.executemany("INSERT INTO silver.xref_company VALUES (?,?,?,?,?,?)", rows)
    clusters = len({r[2] for r in rows})
    return {
        "records": len(rows),
        "companies": clusters,
        "dedupe_ratio": round(1 - clusters / max(len(rows), 1), 4),
    }
