import dataclasses

import pytest

from emblem import contracts as c


def test_all_contracts_load_and_validate():
    cs = c.load_contracts()
    assert len(cs) == 16 and cs["bc.customers"].pk == "no"
    assert {x.source for x in cs.values()} == {
        "business_central",
        "hubspot",
        "bigcommerce",
        "optimizely",
        "marketing_platforms",
        "production_mes",
    }


def test_validate_rejects_bad_pk_type_and_class():
    base = c.load_contracts()["bc.items"]
    with pytest.raises(ValueError, match="pk/updated_at"):
        c.validate_contracts({"x": dataclasses.replace(base, pk="nope")})
    bad = dataclasses.replace(base, columns=base.columns + (c.Column("z", "WEIRD"),))
    with pytest.raises(ValueError, match="invalid type"):
        c.validate_contracts({"x": bad})
    dup = dataclasses.replace(base, columns=base.columns + (base.columns[0],))
    with pytest.raises(ValueError, match="duplicate"):
        c.validate_contracts({"x": dup})


def test_normalise_alias_additive_and_missing():
    ct = c.load_contracts()["bg.orders"]
    n = c.normalise(
        ct,
        {
            "id": "1",
            "date_created": "2026-01-01T00:00:00Z",
            "total": 9.5,
            "modified_at": "2026-01-01T00:00:00Z",
            "extra": 1,
        },
    )
    assert (
        n.renamed == {"total": "total_inc_tax"}
        and n.payload["total_inc_tax"] == 9.5
        and n.added == ["extra"]
        and not n.missing_required
    )
    assert c.normalise(ct, {"id": "1"}).missing_required


def test_diff_breaking_vs_additive():
    old = c.load_contracts()["bc.items"]
    new = dataclasses.replace(
        old, columns=tuple(x for x in old.columns if x.name != "uom") + (c.Column("colour", "VARCHAR"),)
    )
    d = c.diff_contracts(old, new)
    assert d["breaking"] == ["removed:uom"] and d["additive"] == ["added:colour"]
    retyped = dataclasses.replace(
        old,
        columns=tuple(
            dataclasses.replace(x, type="VARCHAR") if x.name == "unit_price" else x for x in old.columns
        ),
    )
    assert "type:unit_price" in c.diff_contracts(old, retyped)["breaking"]
