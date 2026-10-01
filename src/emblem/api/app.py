"""Governed data service (FastAPI): RBAC + masking + audit on every read, signed webhooks, AI tools, health and metrics."""

import json
import os
import secrets
from datetime import date, datetime
from typing import Annotated, Any

import duckdb
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from emblem import db as dbmod
from emblem.ai import index, tools
from emblem.catalog import lineage
from emblem.ops import events, incidents, monitor
from emblem.plan import plan as planmod
from emblem.reporting import dashboard, showcase
from emblem.security import audit as audit_log
from emblem.security import rbac, tokens

VERSION = "1.0.0"


class DevTokenRequest(BaseModel):
    sub: str = "demo-user"
    role: str


def _jsonable(v: Any) -> Any:
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, float) and v != v:
        return None
    return v


def create_app(
    db_path: str | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
    env: dict[str, str] | None = None,
) -> FastAPI:
    cfg = dict(os.environ) | (env or {})
    prod = cfg.get("EMBLEM_ENV", "dev") == "prod"
    auth_secret, hook_secret = cfg.get("EMBLEM_AUTH_SECRET"), cfg.get("EMBLEM_WEBHOOK_SECRET")
    if prod and not (auth_secret and hook_secret):
        raise RuntimeError(
            "prod requires EMBLEM_AUTH_SECRET and EMBLEM_WEBHOOK_SECRET (refusing to start with generated secrets)"
        )
    auth_key = (auth_secret or secrets.token_hex(32)).encode()
    hook_key = (hook_secret or secrets.token_hex(32)).encode()
    root = con or dbmod.connect(db_path or cfg.get("EMBLEM_DB", "build/emblem.duckdb"))
    as_of = date.fromisoformat(cfg.get("EMBLEM_AS_OF", "2026-09-30"))
    app = FastAPI(
        title="World Emblem Data Service", version=VERSION, docs_url=None if prod else "/docs", redoc_url=None
    )
    cache: dict[str, Any] = {}

    def cur() -> duckdb.DuckDBPyConnection:
        return root.cursor()

    def principal(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        try:
            claims = tokens.verify(auth_key, authorization[7:])
        except tokens.TokenError as exc:
            raise HTTPException(401, str(exc)) from exc
        if claims["role"] not in rbac.role_names():
            raise HTTPException(403, "unknown role")
        return claims

    P = Annotated[dict[str, Any], Depends(principal)]

    def need(claims: dict[str, Any], *roles: str) -> None:
        if claims["role"] not in roles:
            raise HTTPException(403, f"role '{claims['role']}' not permitted")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": VERSION}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        cur().execute("SELECT 1")
        return {"status": "ready"}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return monitor.prometheus(cur())

    @app.post("/v1/auth/dev-token")
    def dev_token(req: DevTokenRequest) -> dict[str, str]:
        if prod:
            raise HTTPException(404, "not found")
        if req.role not in rbac.role_names():
            raise HTTPException(422, "unknown role")
        return {"token": tokens.issue(auth_key, req.sub, req.role)}

    @app.get("/v1/catalog")
    def catalog(claims: P) -> list[dict[str, Any]]:
        c = cur()
        out = []
        for (t,) in c.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='gold' AND table_name<>'ai_documents' ORDER BY 1"
        ).fetchall():
            if rbac.can_read(claims["role"], t):
                n = c.execute(f"SELECT count(*) FROM gold.{t}").fetchone()[0]  # type: ignore[index]
                cols = [
                    r[0]
                    for r in c.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema='gold' AND table_name=?",
                        [t],
                    ).fetchall()
                ]
                out.append(
                    {
                        "dataset": t,
                        "rows": n,
                        "columns": [{"name": x, "classification": rbac.column_class(t, x)} for x in cols],
                    }
                )
        return out

    @app.get("/v1/datasets/{name}")
    def dataset(name: str, claims: P, limit: Annotated[int, Query(ge=1, le=500)] = 50) -> dict[str, Any]:
        c = cur()
        allowed = {
            r[0]
            for r in c.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='gold' AND table_name<>'ai_documents'"
            ).fetchall()
        }
        if name not in allowed:
            raise HTTPException(404, "unknown dataset")
        try:
            rows_cur = c.execute(f"SELECT * FROM gold.{name} LIMIT ?", [limit])
            names = [d[0] for d in rows_cur.description]
            rows = [dict(zip(names, r, strict=True)) for r in rows_cur.fetchall()]
            rows, masked = rbac.apply_policy(claims["role"], name, rows)
        except rbac.AccessDenied as exc:
            audit_log.record(c, claims["sub"], claims["role"], "denied", name, str(exc))
            raise HTTPException(403, str(exc)) from exc
        audit_log.record(
            c, claims["sub"], claims["role"], "read", name, f"rows={len(rows)} masked={','.join(masked)}"
        )
        return {
            "dataset": name,
            "masked_columns": masked,
            "rows": [{k: _jsonable(v) for k, v in r.items()} for r in rows],
        }

    @app.get("/v1/quality")
    def quality(claims: P) -> dict[str, Any]:
        need(claims, "admin", "data_engineer", "auditor")
        snap = _snapshot(refresh=False)
        return snap["quality"]  # type: ignore[no-any-return]

    @app.get("/v1/reconciliation")
    def recon(claims: P) -> list[dict[str, Any]]:
        need(claims, "admin", "data_engineer", "finance_analyst", "auditor")
        return _snapshot(refresh=False)["recon"]  # type: ignore[no-any-return]

    @app.get("/v1/incidents")
    def incident_list(claims: P, status: str | None = None) -> list[dict[str, Any]]:
        need(claims, "admin", "data_engineer", "auditor")
        return incidents.list_incidents(cur(), status)

    @app.get("/v1/lineage/{asset}")
    def lineage_of(asset: str, claims: P) -> dict[str, Any]:
        g = lineage.build()
        if asset not in {n["id"] for n in g["nodes"]}:
            raise HTTPException(404, "unknown asset")
        return {"asset": asset, "upstream": sorted(lineage.upstream(g, asset))}

    @app.get("/v1/audit/verify")
    def audit_verify(claims: P) -> dict[str, Any]:
        need(claims, "admin", "auditor")
        return audit_log.verify_chain(cur())

    @app.get("/v1/ai/tools")
    def ai_tools(claims: P) -> list[dict[str, Any]]:
        return tools.tool_specs()

    @app.get("/v1/ai/search")
    def ai_search(
        claims: P,
        q: Annotated[str, Query(min_length=2, max_length=200)],
        k: Annotated[int, Query(ge=1, le=10)] = 5,
    ) -> list[dict[str, Any]]:
        c = cur()
        hits = index.search(c, q, k)
        audit_log.record(
            c, claims["sub"], claims["role"], "ai_search", "gold.ai_documents", f"hits={len(hits)}"
        )
        return hits

    @app.post("/v1/ai/tools/{tool}")
    def ai_call(
        tool: str, claims: P, arg: Annotated[str, Query(min_length=1, max_length=100)]
    ) -> dict[str, Any]:
        c = cur()
        try:
            return {
                k: ([{kk: _jsonable(vv) for kk, vv in r.items()} for r in v] if k == "rows" else v)
                for k, v in tools.call(c, claims["sub"], claims["role"], tool, arg).items()
            }
        except KeyError as exc:
            raise HTTPException(404, "unknown tool") from exc
        except rbac.AccessDenied as exc:
            raise HTTPException(403, str(exc)) from exc

    @app.get("/v1/ai/usage")
    def ai_usage(claims: P) -> dict[str, Any]:
        need(claims, "admin", "data_engineer", "auditor")
        return tools.usage_summary(cur())

    @app.post("/v1/webhooks/{source}")
    async def webhook(
        source: str,
        request: Request,
        x_signature: Annotated[str, Header()],
        x_timestamp: Annotated[str, Header()],
        x_event_id: Annotated[str, Header()],
        x_topic: Annotated[str, Header()],
    ) -> dict[str, str]:
        body = await request.body()
        try:
            events.verify_signature(hook_key, x_timestamp, body, x_signature)
        except events.SignatureError as exc:
            audit_log.record(cur(), source, "webhook", "rejected", x_topic, str(exc))
            raise HTTPException(401, str(exc)) from exc
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, "body must be JSON") from exc
        return {"status": events.receive(cur(), source, x_event_id, x_topic, payload)}

    @app.post("/v1/events/drain")
    def drain(claims: P) -> dict[str, int]:
        need(claims, "admin", "data_engineer")
        return events.drain(cur())

    def _snapshot(refresh: bool) -> dict[str, Any]:
        if refresh or "snap" not in cache:
            c = cur()
            if c.execute("SELECT count(*) FROM meta.dq_results").fetchone()[0] == 0:  # type: ignore[index]
                raise HTTPException(503, "no data yet: run `uv run emblem demo`")
            ver = planmod.verify(planmod.Ctx(c, as_of=as_of))
            cache["snap"] = showcase.build_snapshot(c, as_of, ver)
        return cache["snap"]  # type: ignore[no-any-return]

    @app.get("/v1/showcase")
    def showcase_json(refresh: bool = False) -> JSONResponse:
        return JSONResponse(_snapshot(refresh))  # aggregates only: contains no personal data

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        try:
            return dashboard.render(_snapshot(False))
        except HTTPException:
            return "<h1>World Emblem Data Foundation</h1><p>No data yet. Run <code>uv run emblem demo</code> then restart.</p>"

    return app
