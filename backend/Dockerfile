# Must satisfy [tool.uv] required-version in pyproject.toml; uv sync fails
# the build otherwise.
FROM ghcr.io/astral-sh/uv:0.11.7@sha256:240fb85ab0f263ef12f492d8476aa3a2e4e1e333f7d67fbdd923d00a506a516a AS uv

FROM python:3.12.14-slim

# #609: install the committed uv.lock, never a fresh resolve. The image's
# Python, not a uv download; bytecode compiled at install as pip did (no
# runtime .pyc writes, so cold starts would recompile). The venv sits outside
# /app, root-owned like pip's site-packages, so the chown below does not copy
# it into another layer; its bin goes first so the entrypoint's alembic and
# uvicorn resolve to it.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /bin/uv

# Dependencies only: extras (dev) stay out, and the app is not installed as
# a package (uvicorn and alembic import it from /app, as with pip before).
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . ./

RUN adduser --system --no-create-home --group --uid 1000 app \
    && mkdir -p /app/data/uploads \
    && chmod +x /app/entrypoint.sh \
    && chown -R app:app /app

USER 1000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/bin/sh", "-c", "curl -fsS \"http://127.0.0.1:${PORT:-8000}/health\" || exit 1"]

CMD ["/app/entrypoint.sh"]
