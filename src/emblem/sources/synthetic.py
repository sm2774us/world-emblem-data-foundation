"""Deterministic simulators for World Emblem's systems (all data is synthetic).

One "world" is generated per (seed, scale); batches are time-window slices of it, exactly like an
incremental extract with a re-delivery overlap. Defects are PLANTED on purpose so the audit, quality
checks, reconciliation and incident flow have something real to find (see DEFECTS).
"""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta
from typing import Any

Record = dict[str, Any]
World = dict[str, list[Record]]

START = datetime(2025, 4, 1, tzinfo=UTC)
CUTOFFS = {
    1: datetime(2026, 8, 31, tzinfo=UTC),
    2: datetime(2026, 9, 20, tzinfo=UTC),
    3: datetime(2026, 9, 30, tzinfo=UTC),
}
OVERLAP = timedelta(days=2)
NOW_ANCHOR = CUTOFFS[3]

DEFECTS = {
    "duplicate_customers": "Same company exists under several names/ids across BC, HubSpot, BigCommerce, Optimizely",
    "web_orders_missing_in_erp": "BigCommerce orders that never reached Business Central (integration failure)",
    "invoice_amount_override": "Posted invoices that differ from the sum of their sales lines",
    "stale_web_inventory": "BigCommerce inventory_level out of sync with Business Central on-hand",
    "bad_values": "Negative quantities, zero prices, null emails, future-dated orders, orphan customer refs",
    "schema_drift": "BigCommerce renames total_inc_tax->total; HubSpot adds 'industry' (batch>=2)",
    "volume_drop": "BigCommerce order volume collapses ~85% in batch 3 (silent upstream outage)",
    "stale_marketing": "Ad spend feed stops 4 days before the end of batch 3 (freshness breach)",
}

WORDS_A = [
    "Acme",
    "Summit",
    "Liberty",
    "Patriot",
    "Harbor",
    "Ridgeline",
    "Eagle",
    "Cascade",
    "Ironwood",
    "Sunbelt",
    "Pioneer",
    "Beacon",
    "Granite",
    "Redwood",
    "Keystone",
    "Meridian",
    "Falcon",
    "Bayview",
    "Northstar",
    "Crescent",
]
WORDS_B = [
    "Embroidery",
    "Uniforms",
    "Athletics",
    "Scouts",
    "Fire Dept",
    "Security Services",
    "Apparel",
    "Promotions",
    "Outfitters",
    "Workwear",
    "Sports Club",
    "Rescue",
]
SUFFIX = ["Inc.", "LLC", "Corp", "Co.", "Ltd"]
FAMILIES = ["Embroidered Patch", "PVC Patch", "Woven Patch", "Chenille Letter", "Challenge Coin", "Lanyard"]
LOCATIONS = ["HOL-FL", "ATL-GA", "DAL-TX"]
CAMPAIGNS = ["brand_search", "custom_patches", "retargeting", "scout_season"]
STATES = [("Hollywood", "FL"), ("Atlanta", "GA"), ("Dallas", "TX"), ("Newark", "NJ"), ("Denver", "CO")]


def _ts(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def build_world(seed: int = 42, scale: float = 1.0) -> World:
    rnd = random.Random(seed)
    n_co = max(8, int(60 * scale))
    n_items = max(6, int(40 * scale))
    n_orders = max(30, int(400 * scale))
    w: World = {
        k: []
        for k in (
            "bc.customers",
            "bc.items",
            "bc.sales_orders",
            "bc.sales_lines",
            "bc.invoices",
            "bc.inventory",
            "hs.companies",
            "hs.contacts",
            "hs.deals",
            "bg.customers",
            "bg.products",
            "bg.orders",
            "bg.order_items",
            "opti.quotes",
            "mkt.ad_spend",
            "mes.work_orders",
        )
    }

    names = list({f"{rnd.choice(WORDS_A)} {rnd.choice(WORDS_B)}" for _ in range(n_co * 2)})[:n_co]
    rnd.shuffle(names)
    companies = []
    for i, nm in enumerate(names):
        city, st = rnd.choice(STATES)
        companies.append({"idx": i, "name": nm, "domain": f"{_slug(nm)}.com", "city": city, "state": st})
        created = START + timedelta(days=rnd.randint(0, 60))
        bc_name = f"{nm} {rnd.choice(SUFFIX)}"
        w["bc.customers"].append(
            {
                "no": f"C{10000 + i}",
                "name": bc_name,
                "email": f"ap@{_slug(nm)}.com",
                "phone": f"+1-555-01{i:02d}",
                "city": city,
                "state": st,
                "country": "US",
                "currency": "USD",
                "credit_limit": rnd.choice([5000, 10000, 25000]),
                "tax_id": f"99-{1000000 + i}",
                "modified_at": _ts(created),
            }
        )
        if i % 20 == 3:  # true duplicate customer record in the ERP
            w["bc.customers"].append(
                {
                    **w["bc.customers"][-1],
                    "no": f"C{20000 + i}",
                    "name": bc_name.rstrip("."),
                    "email": None,
                    "modified_at": _ts(created + timedelta(days=9)),
                }
            )
        if rnd.random() < 0.9:
            w["hs.companies"].append(
                {
                    "id": f"H{500 + i}",
                    "name": nm.upper() + ", " + rnd.choice(["INC", "LLC"]),
                    "domain": f"{_slug(nm)}.com",
                    "owner_email": rnd.choice(["sam@worldemblem.example", "lee@worldemblem.example", None]),
                    "lifecycle_stage": rnd.choice(["lead", "customer", "customer", "opportunity"]),
                    "country": "US",
                    "modified_at": _ts(created + timedelta(days=1)),
                }
            )
            if rnd.random() < 0.25:  # later lifecycle change => second version of the HubSpot company
                w["hs.companies"].append(
                    {
                        **w["hs.companies"][-1],
                        "lifecycle_stage": "customer",
                        "modified_at": _ts(
                            datetime(2026, 9, 5, tzinfo=UTC) + timedelta(days=rnd.randint(0, 23))
                        ),
                    }
                )
            for j in range(rnd.randint(1, 2)):
                w["hs.contacts"].append(
                    {
                        "id": f"HC{i}-{j}",
                        "email": rnd.choice([f"buyer{j}@{_slug(nm)}.com"] * 9 + [None]),
                        "first_name": rnd.choice(["Ana", "Ben", "Cy", "Dee"]),
                        "last_name": rnd.choice(["Ruiz", "Shaw", "Lopez"]),
                        "phone": f"+1-555-02{i:02d}",
                        "company_id": f"H{500 + i}",
                        "modified_at": _ts(created + timedelta(days=2)),
                    }
                )
            if rnd.random() < 0.5:
                w["hs.deals"].append(
                    {
                        "id": f"D{i}",
                        "company_id": f"H{500 + i}",
                        "amount": rnd.choice([2500, 8000, 15000, 40000]),
                        "stage": rnd.choice(["qualified", "proposal", "closedwon", "closedlost"]),
                        "close_date": (created + timedelta(days=60)).strftime("%Y-%m-%d"),
                        "modified_at": _ts(created + timedelta(days=3)),
                    }
                )
        if rnd.random() < 0.55 or i % 17 == 5:
            typo = i % 17 == 5  # misspelt company + free-mail address: only fuzzy matching can link it
            w["bg.customers"].append(
                {
                    "id": f"W{i}",
                    "email": f"{_slug(nm)}@gmail.com"
                    if typo or rnd.random() > 0.7
                    else f"orders@{_slug(nm)}.com",
                    "first_name": "Web",
                    "last_name": "Buyer",
                    "company": nm.replace("e", "", 1) if typo else nm,
                    "phone": None,
                    "modified_at": _ts(created + timedelta(days=4)),
                }
            )
        if rnd.random() < 0.2:
            w["opti.quotes"].append(
                {
                    "id": f"Q{i}",
                    "contact_email": f"quotes@{_slug(nm)}.com",
                    "company_name": nm.replace(" ", "  "),
                    "sku": f"WE-{1000 + i % n_items}",
                    "quantity": 250,
                    "quote_amount": 1250.0,
                    "status": "open",
                    "modified_at": _ts(created + timedelta(days=rnd.randint(30, 400))),
                }
            )

    items = []
    for i in range(n_items):
        fam = FAMILIES[i % len(FAMILIES)]
        price = round(rnd.uniform(1.2, 9.5), 2)
        items.append({"no": f"WE-{1000 + i}", "price": price})
        w["bc.items"].append(
            {
                "no": f"WE-{1000 + i}",
                "description": f"{fam} style {i}",
                "family": fam,
                "unit_price": price,
                "unit_cost": round(price * 0.55, 2),
                "uom": "EA",
                "modified_at": _ts(START),
            }
        )
        w["bg.products"].append(
            {
                "id": f"P{i}",
                "sku": f"WE-{1000 + i}",
                "name": f"Custom {fam} #{i}",
                "price": price,
                "inventory_level": 0,
                "is_visible": i % 9 != 0,
                "modified_at": _ts(START),
            }
        )
        for loc in LOCATIONS:
            w["bc.inventory"].append(
                {
                    "inv_id": f"{loc}:{1000 + i}",
                    "item_no": f"WE-{1000 + i}",
                    "location_code": loc,
                    "qty_on_hand": float(rnd.randint(200, 5000)),
                    "modified_at": _ts(NOW_ANCHOR - timedelta(days=1)),
                }
            )
    for prod in w["bg.products"]:
        total = sum(r["qty_on_hand"] for r in w["bc.inventory"] if r["item_no"] == prod["sku"])
        prod["inventory_level"] = total if rnd.random() > 0.12 else total + rnd.choice([-300, 150, 900])
        prod["modified_at"] = _ts(NOW_ANCHOR - timedelta(days=1))

    span = (NOW_ANCHOR - START).days
    line_no = inv_no = web_no = bg_line = wo_no = 0
    for o in range(n_orders):
        co = companies[rnd.randrange(len(companies))]
        odate = START + timedelta(days=int(rnd.betavariate(2, 1.3) * span), hours=rnd.randint(8, 17))
        if o == 7:
            odate = NOW_ANCHOR + timedelta(days=45)  # future-dated order
        no = f"SO{200000 + o}"
        cust = f"C{10000 + co['idx']}" if o != 11 and o != 12 else "C99999"  # two orphans
        web = rnd.random() < 0.45
        ext = None
        status = rnd.choices(["Shipped", "Open", "Cancelled"], [0.8, 0.14, 0.06])[0]
        if odate > NOW_ANCHOR - timedelta(days=10) and status == "Shipped":
            status = "Open"
        lines = []
        for _ in range(rnd.randint(1, 3)):
            it = rnd.choice(items)
            qty = float(rnd.choice([50, 100, 250, 500, 1000]))
            price = it["price"] if rnd.random() > 0.02 else 0.0
            if o == 5 and not lines:
                qty = -25.0
            line_no += 1
            lines.append(
                {
                    "line_id": f"L{line_no}",
                    "order_no": no,
                    "item_no": it["no"],
                    "quantity": qty,
                    "unit_price": price,
                    "line_amount": round(qty * price, 2),
                    "modified_at": _ts(odate),
                }
            )
        missing_in_erp = web and rnd.random() < 0.06
        if web:
            web_no += 1
            ext = f"BG-{3000 + web_no}"
            cid = next((c["id"] for c in w["bg.customers"] if c["company"] == co["name"]), None)
            bg_total = round(sum(line["line_amount"] for line in lines) * 1.07, 2)
            w["bg.orders"].append(
                {
                    "id": f"{3000 + web_no}",
                    "customer_id": cid,
                    "date_created": _ts(odate),
                    "status": "shipped" if status == "Shipped" else status.lower(),
                    "total_inc_tax": bg_total,
                    "currency": "USD",
                    "utm_campaign": rnd.choice(CAMPAIGNS + [None]),
                    "modified_at": _ts(odate),
                }
            )
            for line in lines:
                bg_line += 1
                w["bg.order_items"].append(
                    {
                        "id": f"BI{bg_line}",
                        "order_id": f"{3000 + web_no}",
                        "sku": line["item_no"],
                        "quantity": line["quantity"],
                        "price_inc_tax": round(line["unit_price"] * 1.07, 3),
                        "modified_at": _ts(odate),
                    }
                )
        if missing_in_erp:
            continue  # BC never receives it: the classic integration gap
        w["bc.sales_orders"].append(
            {
                "no": no,
                "customer_no": cust,
                "order_date": odate.strftime("%Y-%m-%d"),
                "status": status,
                "currency": "USD",
                "external_doc_no": ext,
                "modified_at": _ts(odate),
            }
        )
        w["bc.sales_lines"].extend(lines)
        if status == "Shipped" and o % 60 != 13:  # o%60==13: shipped but never invoiced (revenue leakage)
            inv_no += 1
            amt = round(sum(line["line_amount"] for line in lines), 2)
            if rnd.random() < 0.04:
                amt = round(amt * 0.93, 2)  # manual price override at invoicing
            ship = odate + timedelta(days=rnd.randint(2, 6))
            w["bc.invoices"].append(
                {
                    "invoice_no": f"INV{700000 + inv_no}",
                    "order_no": no,
                    "posting_date": ship.strftime("%Y-%m-%d"),
                    "amount": amt,
                    "currency": "USD",
                    "modified_at": _ts(ship),
                }
            )
        if status != "Cancelled":
            wo_no += 1
            planned = sum(line["quantity"] for line in lines if line["quantity"] > 0)
            scrap = float(int(planned * rnd.uniform(0.0, 0.08)))
            w["mes.work_orders"].append(
                {
                    "id": f"WO{wo_no}",
                    "bc_order_no": no,
                    "item_no": lines[0]["item_no"],
                    "location_code": rnd.choice(LOCATIONS),
                    "machine": rnd.choice(["EMB-01", "EMB-02", "PVC-01", "WOV-01"]),
                    "qty_planned": planned,
                    "qty_good": planned - scrap,
                    "qty_scrap": scrap,
                    "status": "done" if status == "Shipped" else "wip",
                    "started_at": _ts(odate + timedelta(days=1)),
                    "finished_at": _ts(odate + timedelta(days=2)),
                    "modified_at": _ts(odate + timedelta(days=2)),
                }
            )
        if status == "Open" and rnd.random() < 0.5:  # later status update => second version of the same key
            upd = min(odate + timedelta(days=12), NOW_ANCHOR)
            w["bc.sales_orders"].append(
                {**w["bc.sales_orders"][-1], "status": "Shipped", "modified_at": _ts(upd)}
            )
            inv_no += 1
            w["bc.invoices"].append(
                {
                    "invoice_no": f"INV{700000 + inv_no}",
                    "order_no": no,
                    "posting_date": upd.strftime("%Y-%m-%d"),
                    "amount": round(sum(line["line_amount"] for line in lines), 2),
                    "currency": "USD",
                    "modified_at": _ts(upd),
                }
            )
    for n in range(180):
        d = START + timedelta(days=span - 180 + n)
        for k, camp in enumerate(CAMPAIGNS):
            for plat in ("google_ads", "meta"):
                spend = round(rnd.uniform(20, 140) * (1 + k * 0.1), 2)
                w["mkt.ad_spend"].append(
                    {
                        "id": f"{plat}:{camp}:{d:%Y%m%d}",
                        "spend_date": d.strftime("%Y-%m-%d"),
                        "platform": plat,
                        "campaign": camp,
                        "spend": spend,
                        "clicks": int(spend * 3),
                        "impressions": int(spend * 90),
                        "modified_at": _ts(d + timedelta(days=1)),
                    }
                )
    return w


def _in_window(rec: Record, lo: datetime | None, hi: datetime) -> bool:
    ts = datetime.strptime(rec["modified_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return (lo is None or ts > lo) and ts <= hi


def generate(seed: int = 42, scale: float = 1.0, batch: int = 1, breaking_drift: bool = False) -> World:
    """Return the extract for one batch (1 = initial load, 2/3 = incremental with overlap)."""
    world = build_world(seed, scale)
    hi = CUTOFFS[batch]
    lo = None if batch == 1 else CUTOFFS[batch - 1] - OVERLAP
    rnd = random.Random(seed + batch)
    out: World = {}
    for ds, rows in world.items():
        sel = [dict(r) for r in rows if _in_window(r, lo, hi)]
        if batch == 3 and ds in ("bg.orders", "bg.order_items"):
            sel = [r for r in sel if rnd.random() < 0.15]  # silent volume collapse
        if batch == 3 and ds == "mkt.ad_spend":
            cutoff = (NOW_ANCHOR - timedelta(days=4)).strftime("%Y-%m-%d")
            sel = [r for r in sel if r["spend_date"] <= cutoff]  # feed stalled
        if batch >= 2 and ds == "bg.orders":
            for r in sel:
                r["total"] = r.pop("total_inc_tax")  # drift: known rename (contract alias)
        if batch >= 2 and ds == "hs.companies":
            for r in sel:
                r["industry"] = "apparel"  # drift: additive new field
        if breaking_drift and ds == "bc.inventory":
            for r in sel[:5]:
                r.pop("item_no", None)  # drift: breaking, required field vanished
        out[ds] = sel
    return out


def anchor_date() -> date:
    return NOW_ANCHOR.date()
