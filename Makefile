.PHONY: help install hooks run demo serve verify test unit integration e2e spark airflow dbt lint fmt types secrets docs lakehouse docker tf-validate
help:
	@echo "make install | hooks | demo | serve | verify | test | e2e | spark | airflow | dbt | lint | fmt | types | secrets | docs | lakehouse | docker"
install:
	uv sync --locked
hooks:
	uv run python tools/install_hooks.py
demo:
	uv run emblem demo
serve:
	uv run emblem serve
lint:
	uv run ruff check src tests dags tools
fmt:
	uv run ruff format src tests dags tools
types:
	uv run mypy
test:
	uv run pytest -m "not e2e and not spark and not airflow" --cov
unit:
	uv run pytest tests/unit --no-cov
integration:
	uv run pytest -m "integration and not spark and not airflow" --no-cov
e2e:
	uv run pytest -m e2e --no-cov
spark:
	uv sync --locked --group spark && uv run pytest -m spark --no-cov
airflow:
	uv sync --locked --group airflow && uv run pytest -m airflow --no-cov
dbt:
	uv sync --locked --group dbt && uv run emblem demo && EMBLEM_DB=build/emblem.duckdb uv run dbt build --project-dir dbt_project --profiles-dir dbt_project
verify: lint types test e2e
secrets:
	gitleaks detect --source . --config .gitleaks.toml --redact --no-banner
docs:
	uv run emblem docs && python tools/sync_dbt.py
lakehouse:
	uv run emblem lakehouse
docker:
	docker build -f infra/docker/Dockerfile -t emblem:local . && docker run --rm -p 8000:8000 emblem:local serve --host 0.0.0.0
tf-validate:
	@for d in infra/terraform/envs/*/; do terraform -chdir=$$d init -backend=false -input=false >/dev/null && terraform -chdir=$$d validate; done
