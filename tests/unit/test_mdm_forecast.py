from emblem.pipelines import forecast, mdm


def test_normalise_name_and_domain():
    assert (
        mdm.normalise_name("ACME  Embroidery, Inc.")
        == mdm.normalise_name("Acme Embroidery LLC")
        == "acme embroidery"
    )
    assert (
        mdm.email_domain("a@gmail.com") is None
        and mdm.email_domain("x@acme.com") == "acme.com"
        and mdm.email_domain(None, "ACME.com") == "acme.com"
    )


def test_resolution_rules_and_stable_keys(fresh_con):
    for ddl in (
        "silver.stg_bc__customers(no VARCHAR, name VARCHAR, email VARCHAR)",
        "silver.stg_hs__companies(id VARCHAR, name VARCHAR, domain VARCHAR)",
        "silver.stg_bg__customers(id VARCHAR, company VARCHAR, email VARCHAR)",
        "silver.stg_opti__quotes(id VARCHAR, company_name VARCHAR, contact_email VARCHAR)",
    ):
        fresh_con.execute(f"CREATE TABLE {ddl}")
    fresh_con.execute(
        "INSERT INTO silver.stg_bc__customers VALUES ('C1','Acme Embroidery Inc.','ap@acme.com'),('C2','Zed Corp','z@zed.com')"
    )
    fresh_con.execute(
        "INSERT INTO silver.stg_hs__companies VALUES ('H1','ACME EMBROIDERY, INC','acme.com'),('H2','Different Name','zed.com')"
    )
    fresh_con.execute("INSERT INTO silver.stg_bg__customers VALUES ('W1','Acme Embroydery','acme@gmail.com')")
    s = mdm.resolve(fresh_con)
    assert s["records"] == 5 and s["companies"] == 2
    rules = dict(
        fresh_con.execute("SELECT source||source_id, match_rule FROM silver.xref_company").fetchall()
    )
    assert (
        rules["bcC1"] == "exact_name" and rules["hsH2"] == "shared_domain" and rules["bgW1"] == "fuzzy_name"
    )
    k1 = fresh_con.execute("SELECT company_key FROM silver.xref_company ORDER BY 1").fetchall()
    mdm.resolve(fresh_con)
    assert fresh_con.execute("SELECT company_key FROM silver.xref_company ORDER BY 1").fetchall() == k1


def test_holt_trend_and_edge_cases():
    up = forecast.holt([10, 12, 14, 16, 18])
    assert up[0] > 18 and up[1] > up[0]
    assert forecast.holt([5.0]) == [5.0, 5.0, 5.0] and forecast.holt([]) == [0.0, 0.0, 0.0]
    assert all(v >= 0 for v in forecast.holt([10, 5, 1]))
