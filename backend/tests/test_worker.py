from datetime import datetime, timedelta, timezone

import worker
from db.models import Document, User
from db.models import Session as SessionModel


def _seed_doc(db, status="pending", claimed_at=None, sid="s_w", uid="u_w"):
    if db.get(User, uid) is None:
        db.add(User(id=uid))
        db.flush()
        db.add(
            SessionModel(
                id=sid, user_id=uid, topic="t", topic_profile_json="{}"
            )
        )
    doc = Document(
        session_id=sid, filename="a.txt", status=status, claimed_at=claimed_at
    )
    db.add(doc)
    db.commit()
    return doc


def test_claim_next_claims_oldest_pending(db_session):
    d1 = _seed_doc(db_session)
    d2 = _seed_doc(db_session)
    got = worker.claim_next(db_session)
    assert got == d1.id
    db_session.expire_all()
    assert db_session.get(Document, d1.id).status == "processing"
    assert db_session.get(Document, d1.id).claimed_at is not None
    assert db_session.get(Document, d2.id).status == "pending"


def test_claim_next_returns_none_when_empty(db_session):
    assert worker.claim_next(db_session) is None


def test_recover_stuck_resets_old_processing(db_session):
    old = datetime.now(timezone.utc) - timedelta(minutes=45)
    d = _seed_doc(db_session, status="processing", claimed_at=old)
    fresh = _seed_doc(db_session, status="processing",
                      claimed_at=datetime.now(timezone.utc))
    n = worker.recover_stuck(db_session)
    assert n == 1
    db_session.expire_all()
    assert db_session.get(Document, d.id).status == "pending"
    assert db_session.get(Document, fresh.id).status == "processing"


def test_main_loop_recovers_stale_claim_mid_run_without_restart(db_session, monkeypatch):
    """PR-4 Finding 2: recover_stuck must not run only at boot. A worker
    that claims a doc and then dies leaves it "processing" with a stale
    claimed_at; the SAME running loop (no restart) must eventually recover
    it once it goes stale, not just at process start."""
    from sqlalchemy.orm import sessionmaker

    d = _seed_doc(db_session, status="pending")

    test_engine = db_session.get_bind()
    monkeypatch.setattr(
        "worker.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=test_engine),
    )
    monkeypatch.setattr("worker.time", type("T", (), {
        "sleep": staticmethod(lambda s: None)
    }))
    monkeypatch.setattr("worker.RECOVER_EVERY_ITERATIONS", 2)

    call_count = {"n": 0}

    def fake_claim_next(db):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Simulate a worker that claimed the doc and died immediately --
            # by the next iteration its claim is already stale.
            doc = db.get(Document, d.id)
            doc.status = "processing"
            doc.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=45)
            db.commit()
        return None

    monkeypatch.setattr("worker.claim_next", fake_claim_next)

    worker.main_loop(max_iterations=3)

    db_session.expire_all()
    assert db_session.get(Document, d.id).status == "pending"


def test_main_loop_processes_then_exits(db_session, monkeypatch):
    d = _seed_doc(db_session)
    processed = []
    monkeypatch.setattr(
        "worker.ingestion_service", type("M", (), {
            "run": staticmethod(lambda doc_id: processed.append(doc_id))
        }),
    )
    from sqlalchemy.orm import sessionmaker

    test_engine = db_session.get_bind()
    monkeypatch.setattr(
        "worker.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=test_engine),
    )
    monkeypatch.setattr("worker.time", type("T", (), {
        "sleep": staticmethod(lambda s: None)
    }))
    worker.main_loop(max_iterations=2)
    assert processed == [d.id]


def test_main_loop_exits_when_stop_event_already_set(db_session, monkeypatch):
    """A stop_event set before entry must exit the loop without claiming
    anything, even with max_iterations=None (the in-process mode)."""
    import threading

    from sqlalchemy.orm import sessionmaker

    d = _seed_doc(db_session, status="pending")
    test_engine = db_session.get_bind()
    monkeypatch.setattr(
        "worker.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=test_engine),
    )
    ev = threading.Event()
    ev.set()
    worker.main_loop(stop_event=ev)  # must return, not hang
    db_session.expire_all()
    assert db_session.get(Document, d.id).status == "pending"


def test_main_loop_idle_wait_uses_stop_event_not_sleep(db_session, monkeypatch):
    """With a stop_event provided, idle waiting must go through
    stop_event.wait(POLL_INTERVAL_S) so shutdown interrupts the wait.
    time.sleep must not be touched on this path."""
    from sqlalchemy.orm import sessionmaker

    test_engine = db_session.get_bind()
    monkeypatch.setattr(
        "worker.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=test_engine),
    )

    def _boom(_s):
        raise AssertionError("time.sleep must not be used when stop_event given")

    monkeypatch.setattr("worker.time", type("T", (), {"sleep": staticmethod(_boom)}))

    class _SelfStoppingEvent:
        def __init__(self):
            self.waits = 0
            self._set = False

        def is_set(self):
            return self._set

        def wait(self, timeout=None):
            assert timeout == worker.POLL_INTERVAL_S
            self.waits += 1
            self._set = True

    ev = _SelfStoppingEvent()
    worker.main_loop(stop_event=ev)  # empty queue: one wait, then exits
    assert ev.waits == 1
