"""Ingestion worker: claims pending documents and ingests them
out-of-process (audit F-02/F-04/B-02).

Run: python -m worker
Queue: the documents row is the job record. Claim is an atomic
pending -> processing transition; on Postgres it uses
FOR UPDATE SKIP LOCKED so multiple workers are safe.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from db.database import SessionLocal
from db.models import Document
from lib.logging_config import configure_logging
from services import ingestion_service

log = logging.getLogger(__name__)

POLL_INTERVAL_S = 2.0
STALE_PROCESSING_MINUTES = 30

# recover_stuck must not run only once at process boot: a kill+immediate-
# restart would strand a "processing" doc until a future restart happens
# more than STALE_PROCESSING_MINUTES later. Run it periodically inside the
# running loop instead -- every N iterations is simpler to test than
# wall-clock, and at POLL_INTERVAL_S=2.0 this is roughly once a minute.
RECOVER_EVERY_ITERATIONS = 30


def claim_next(db) -> int | None:
    stmt = select(Document.id).where(Document.status == "pending").order_by(Document.id).limit(1)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    row = db.execute(stmt).first()
    if row is None:
        db.rollback()
        return None
    doc = db.get(Document, row[0])
    doc.status = "processing"
    doc.claimed_at = datetime.now(timezone.utc)
    db.commit()
    return doc.id


def recover_stuck(db, *, now: datetime | None = None) -> int:
    """A worker died mid-ingestion: put its claims back in the queue.
    Safe because ingestion re-runs are idempotent (persisted chunk
    indexes are skipped)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=STALE_PROCESSING_MINUTES)
    result = db.execute(
        update(Document)
        .where(Document.status == "processing")
        .where(Document.claimed_at < cutoff)
        .values(status="pending", claimed_at=None)
    )
    db.commit()
    return result.rowcount


def main_loop(max_iterations: int | None = None, stop_event=None) -> None:
    """stop_event (threading.Event, optional): set to request a prompt
    exit. Used by the in-process mode (main.py lifespan); worker mode
    (python -m worker) passes nothing and keeps the plain sleep path."""
    iterations = 0
    boot_db = SessionLocal()
    try:
        n = recover_stuck(boot_db)
        if n:
            log.info("recovered %s stuck documents on boot", n)
    finally:
        boot_db.close()
    while max_iterations is None or iterations < max_iterations:
        if stop_event is not None and stop_event.is_set():
            break
        iterations += 1
        if iterations % RECOVER_EVERY_ITERATIONS == 0:
            recover_db = SessionLocal()
            try:
                n = recover_stuck(recover_db)
                if n:
                    log.info("recovered %s stuck documents mid-run", n)
            finally:
                recover_db.close()
        db = SessionLocal()
        try:
            doc_id = claim_next(db)
        finally:
            db.close()
        if doc_id is None:
            if stop_event is not None:
                stop_event.wait(POLL_INTERVAL_S)
            else:
                time.sleep(POLL_INTERVAL_S)
            continue
        log.info("worker picked up document_id=%s", doc_id)
        ingestion_service.run(doc_id)


if __name__ == "__main__":
    configure_logging()
    log.info("ingestion worker starting (poll=%ss)", POLL_INTERVAL_S)
    main_loop()
