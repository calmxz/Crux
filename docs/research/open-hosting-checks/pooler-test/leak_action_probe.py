"""Crux #726 item 1, step 8b: what the local Supavisor does with each
txn_mode_leak_action value. The caller sets the tenant row and restarts the
pooler container first. ASCII-only output.

Usage:  python leak_action_probe.py
"""

import subprocess
import sys
import time
from datetime import datetime, timezone

import psycopg

ANA = "aaaaaaaa-0000-4000-8000-000000000001"
BEN = "bbbbbbbb-0000-4000-8000-000000000002"
ADMIN_DSN = "host=127.0.0.1 port=54322 dbname=postgres user=postgres password=postgres connect_timeout=5"
META_DSN = "host=127.0.0.1 port=54322 dbname=_supabase user=postgres password=postgres connect_timeout=5"
POOLER_DSN = (
    "host=127.0.0.1 port=54329 dbname=postgres user=crux_app.pooler-dev "
    "password=crux_app_local connect_timeout=5 options='-c statement_timeout=5000'"
)
POOLER_CONTAINER = "supabase_pooler_crux-726-pooler"
PROBE = (
    "select pg_backend_pid(), current_setting('app.home_id', true), "
    "(select count(*) from sessions)"
)


def log(msg=""):
    print(msg, flush=True)


def connect():
    for attempt in range(1, 21):
        try:
            return psycopg.connect(POOLER_DSN, autocommit=True, prepare_threshold=None)
        except psycopg.Error as e:
            log(f"  connect attempt {attempt}: {type(e).__name__}: {str(e).strip()!r}")
            time.sleep(1.0)
    raise SystemExit("[ERROR] pooler not reachable")


def attempt(conn, who, sql, params=None):
    """Run one statement; return ('ok', rows) or ('error', text)."""
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
        log(f"  [{who}] {sql} -> ok {[tuple(r) for r in rows]!r}")
        return "ok", rows
    except psycopg.Error as e:
        text = f"{type(e).__name__}: {str(e).strip()}"
        log(f"  [{who}] {sql} -> ERROR {text!r}")
        return "error", text


def main():
    log(f"# step 8b leak-action probe, run at {datetime.now(timezone.utc).isoformat()}")
    with psycopg.connect(META_DSN, autocommit=True) as meta:
        action = meta.execute("select txn_mode_leak_action from _supavisor.tenants "
                              "where external_id = 'pooler-dev'").fetchone()[0]
    log(f"  tenant txn_mode_leak_action = {action!r}")
    admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    a, b = connect(), connect()
    attempt(a, "A", "select 1")
    killed = admin.execute("select pid, pg_terminate_backend(pid) from pg_stat_activity "
                           "where usename = 'crux_app'").fetchall()
    log(f"  [admin] terminated crux_app backends: {killed!r}")
    time.sleep(1.5)
    attempt(a, "A", "select 1")
    attempt(b, "B", "select 1")
    t0 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cases = [
        ("session SET", f"set app.home_id = '{ANA}'", None),
        ("set_config is_local=false", "select set_config('app.home_id', %s, false)", (ANA,)),
    ]
    for label, sql, params in cases:
        log(f"### {label}")
        status, _ = attempt(a, "A", sql, params)
        if a.closed or a.broken:
            log("  [A] client connection closed by the pooler; reconnecting")
            a = connect()
        attempt(b, "B", PROBE)
        # Clear any leftover before the next case, on a new backend.
        admin.execute("select pg_terminate_backend(pid) from pg_stat_activity where usename = 'crux_app'")
        time.sleep(1.5)
        attempt(b, "B", "select 1")

    log("### safe pattern under this action: set_config(..., true) and SET LOCAL in a transaction")
    for sql, params in (("select set_config('app.home_id', %s, true)", (BEN,)),
                        (f"set local app.home_id = '{BEN}'", None)):
        try:
            with a.transaction():
                attempt(a, "A", sql, params)
                attempt(a, "A", PROBE)
        except psycopg.Error as e:
            log(f"  [A] transaction error: {type(e).__name__}: {str(e).strip()!r}")
        if a.closed or a.broken:
            a = connect()
        attempt(b, "B", PROBE)

    time.sleep(1.0)
    out = subprocess.run(["docker", "logs", "--since", t0, POOLER_CONTAINER],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = (out.stdout + out.stderr).splitlines()
    log(f"## pooler log since {t0}: {len(lines)} lines")
    for ln in lines:
        log(f"  [docker] {ln.encode('ascii', 'replace').decode('ascii')}")
    a.close()
    b.close()
    admin.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
