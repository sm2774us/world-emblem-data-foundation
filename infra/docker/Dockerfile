# syntax=docker/dockerfile:1.7
FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

FROM python:3.14-slim
RUN useradd --system --uid 10001 --home /app emblem && mkdir -p /app/build && chown emblem /app/build
WORKDIR /app
COPY --from=build --chown=emblem /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 EMBLEM_ENV=dev EMBLEM_DB=/app/build/emblem.duckdb
USER 10001
EXPOSE 8000
ENTRYPOINT ["emblem"]
CMD ["serve", "--host", "0.0.0.0"]
