FROM python:3.12.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

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
