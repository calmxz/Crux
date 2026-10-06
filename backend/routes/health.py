import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from config import settings
from contracts import HealthResponse
from db.database import get_db

router = APIRouter()

log = logging.getLogger(__name__)


def _ok() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health", response_model=HealthResponse)
def health():
    return _ok()


@router.get("/healthz", response_model=HealthResponse, include_in_schema=False)
def healthz():
    return _ok()


def _probe(db: Session) -> None:
    """G-07: the cheapest round trip that proves the pool can hand out a
    working connection.

    Bounded at the driver, not by abandoning the awaiter. An asyncio.wait_for
    around this call only timed out the coroutine: the worker thread kept
    running against a Session that get_db was about to close, and every
    abandoned thread held an anyio limiter token plus a pool slot. Now the
    connect is capped by psycopg's connect_timeout (db/database.py) and the
    query by a transaction-local statement_timeout, issued in the same
    transaction.
    """
    if db.get_bind().dialect.name == "postgresql":
        # set_config(name, value, is_local=true) is SET LOCAL with bind
        # parameters: no SQL text is ever built from a value.
        timeout_ms = int(settings.readiness_timeout_s * 1000)
        db.execute(
            text("SELECT set_config('statement_timeout', :v, true)"),
            {"v": str(timeout_ms)},
        )
    db.execute(select(1)).scalar_one()


# include_in_schema=False: /ready is infrastructure (Render health check), not
# part of the client-facing API contract in docs/api/openapi.yaml.
@router.get("/ready", include_in_schema=False)
async def ready(db: Session = Depends(get_db)):
    """Readiness: the process answers AND the database answers.

    /health and /healthz stay pure liveness -- they must keep returning 200
    while the DB is down so the platform does not kill a process that is
    merely waiting on an upstream.
    """
    try:
        await run_in_threadpool(_probe, db)
    except Exception as e:
        log.warning("readiness probe failed error=%s", e)
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ok"})
