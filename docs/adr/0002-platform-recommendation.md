# ADR 0002: Platform recommendation (Microsoft Fabric, reversible)
Status: proposed for CTO review. **Context:** Microsoft-centric estate (Business Central, Power BI, M365), AI roadmap, small team.
**Decision:** Recommend Microsoft Fabric (OneLake, Spark, Power BI Direct Lake) scored 4.25/5 in `platform_options.yaml`; Databricks is the runner-up if heavy ML or multi-cloud grows. The decision survives +/-50% weight perturbation (`uv run emblem platform`).
**Reversibility:** all logic is SQL/Spark over open formats (Parquet/Delta); orchestration is Airflow; no Fabric-only constructs in transformation code.
**Terraform:** `infra/terraform` provisions the Azure landing zone (ADLS Gen2 bronze/silver/gold, Key Vault with purge protection, Log Analytics).
