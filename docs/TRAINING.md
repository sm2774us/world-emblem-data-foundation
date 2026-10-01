# Training: how teams collect, define, share and use data

45-minute session per department, repeated each quarter; slides are generated from this file and the glossary.

1. **One definition, one owner.** Walk the glossary (`uv run emblem docs`): Revenue, Order, Active customer, Inventory on hand, Yield, ROAS. Owners confirm or amend by PR.
2. **Enter it once, at the source.** The system-of-record matrix says where each fact is created. Fix errors there; reports and spreadsheets do not get patched.
3. **What the checks catch.** Show last week's incidents for the department with the fix-at-source action and the 15-minute fix.
4. **How to ask for data.** Request through the intake template (owner, decision, domain, freshness, access). Self-serve through the Power BI semantic model or API; no direct database access.
5. **Using AI safely.** Agents call allow-listed tools; no PII; every call is logged and reviewed monthly (`GET /v1/ai/usage`).
6. **Hands-on (15 min).** Find a disputed number, trace it with `GET /v1/lineage/{asset}`, identify the owning team.
