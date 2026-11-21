"""Crux #726 item 1: row-level security through Supavisor in transaction mode.

Two pooler clients (A = Ana's request, B = Ben's request) log in as the
non-owner role crux_app through the local Supavisor transaction port, with
pool size 1, so both must land on the same Postgres backend. Every step reads
pg_backend_pid() in the same statement or transaction as the data it vouches
for, and asserts A's pid equals B's pid.

Usage:  python pooler_rls_test.py <supabase-cli-version>
Exit code 0 only when every check matched its expected value.
Output is ASCII only (Windows cp1252 pipes).
"""

import subprocess
import sys
import time
from datetime import datetime, timezone

import psycopg

ANA = "aaaaaaaa-0000-4000-8000-000000000001"
BEN = "bbbbbbbb-0000-4000-8000-000000000002"

# Local default passwords only; the stack is thrown away after the run.
ADMIN_DSN = "host=127.0.0.1 port=54322 dbname=postgres user=postgres password=postgres connect_timeout=5"
META_DSN = "host=127.0.0.1 port=54322 dbname=_supabase user=postgres password=postgres connect_timeout=5"
POOLER_DSN = (
    "host=127.0.0.1 port=54329 dbname=postgres user=crux_app.pooler-dev "
    "password=crux_app_local connect_timeout=5 options='-c statement_timeout=5000'"
)
POOLER_CONTAINER = "supabase_pooler_crux-726-pooler"
DB_CONTAINER = "supabase_db_crux-726-pooler"

checks = []  # (step, name, expected, observed, ok)


def log(msg=""):
    print(msg, flush=True)


def check(step, name, expected, observed):
    ok = expected == observed
    checks.append((step, name, expected, observed, ok))
    log(f"  [{'PASS' if ok else 'FAIL'}] {step} {name}: expected={expected!r} observed={observed!r}")
    return ok


def q(conn, who, sql, params=None):
    cur = conn.execute(sql, params)
    rows = cur.fetchall() if cur.description else []
    shown = sql if params is None else f"{sql}  -- params={params!r}"
    log(f"  [{who}] {shown}")
    for r in rows:
        log(f"  [{who}]   -> {tuple(r)!r}")
    return rows


def probe_sql(table="sessions"):
    # pid, the setting, and the row count in ONE statement, so the pid vouches
    # for exactly the data it is printed with.
    return (
        "select pg_backend_pid() as pid, current_user as usr, "
        "current_setting('app.home_id', true) as home_setting, "
        f"(select count(*) from {table}) as n_rows, "
        f"(select coalesce(string_agg(title, ' | ' order by id), '') from {table}) as titles"
    )


def pooler_connect():
    return psycopg.connect(POOLER_DSN, autocommit=True, prepare_threshold=None)


def backends(admin, label):
    rows = admin.execute(
        "select pid, usename, application_name, backend_start "
        "from pg_stat_activity where usename = 'crux_app' order by pid"
    ).fetchall()
    log(f"  [admin] crux_app server backends ({label}): {[(r[0], str(r[3])) for r in rows]!r}")
    return [r[0] for r in rows]


def fresh_backend(admin, a, b):
    """Kill crux_app's server connection so the pool opens a new one."""
    killed = admin.execute(
        "select pid, pg_terminate_backend(pid) from pg_stat_activity where usename = 'crux_app'"
    ).fetchall()
    log(f"  [admin] terminated crux_app backends: {killed!r}")
    time.sleep(1.5)
    # The first statement after the kill may fail while the pool reconnects.
    for who, c in (("A", a), ("B", b)):
        for attempt in range(1, 6):
            try:
                c.execute("select 1").fetchall()
                break
            except psycopg.Error as e:
                log(f"  [{who}] warm-up attempt {attempt} error: {type(e).__name__}: {str(e).strip()!r}")
                time.sleep(1.0)
                if c.closed or c.broken:
                    log(f"  [{who}] client connection broken; reconnecting")
                    c = pooler_connect()
                    if who == "A":
                        a = c
                    else:
                        b = c
    return a, b


def same_pid(step, pids):
    distinct = sorted(set(pids))
    log(f"  [pid] {step} pids seen by A and B: {pids!r}")
    return check(step, "A and B on the same backend pid", 1, len(distinct))


def docker_logs_since(since_iso):
    out = subprocess.run(
        ["docker", "logs", "--since", since_iso, POOLER_CONTAINER],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    lines = (out.stdout + out.stderr).splitlines()
    return lines


def main():
    cli_version = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    log(f"# Crux #726 item 1 pooler RLS test, run at {datetime.now(timezone.utc).isoformat()}")
    log()

    # ---------------------------------------------------------------- step 1
    log("## Step 1: versions and pooler settings")
    log(f"  Supabase CLI: {cli_version}")
    log(f"  psycopg: {psycopg.__version__}  libpq: {psycopg.pq.version()}")
    for c in (POOLER_CONTAINER, DB_CONTAINER):
        img = subprocess.run(["docker", "inspect", "--format", "{{.Config.Image}}", c],
                             capture_output=True, text=True).stdout.strip()
        log(f"  image {c}: {img}")
    admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    q(admin, "admin", "select version()")
    with psycopg.connect(META_DSN, autocommit=True) as meta:
        rows = q(meta, "meta", "select external_id, default_pool_size, require_user, "
                 "txn_mode_leak_action, server_reset_query from _supavisor.tenants")
        leak_action = rows[0][3]
        q(meta, "meta", "select db_user, mode_type, pool_size from _supavisor.users")
    log()

    # ---------------------------------------------------------------- step 2
    log("## Step 2: roles, owners, grants")
    rows = q(admin, "admin", "select rolname, rolbypassrls, rolsuper from pg_roles "
             "where rolname in ('postgres', 'crux_app') order by rolname")
    roles = {r[0]: (r[1], r[2]) for r in rows}
    check("step2", "crux_app (bypassrls, superuser)", (False, False), roles.get("crux_app"))
    q(admin, "admin", "select relname, pg_get_userbyid(relowner) as owner, relrowsecurity, "
      "relforcerowsecurity from pg_class where relnamespace = 'public'::regnamespace and relname in ('homes','sessions','sessions_no_nullif') "
      "order by relname")
    q(admin, "admin", "select table_name, string_agg(privilege_type, ',' order by privilege_type) "
      "from information_schema.role_table_grants where grantee = 'crux_app' group by 1 order by 1")
    q(admin, "admin", "select polname, pg_get_expr(polqual, polrelid) from pg_policy order by polname")
    log()

    a = pooler_connect()
    b = pooler_connect()
    log("## Connected A and B through the pooler as crux_app.pooler-dev on port 54329 (transaction mode)")
    log()

    # ---------------------------------------------------------------- step 7a
    log("## Step 7a: unset setting on a fresh backend that never saw app.home_id")
    a, b = fresh_backend(admin, a, b)
    backends(admin, "after reset")
    rb = q(b, "B", probe_sql("sessions"))
    rb2 = q(b, "B", probe_sql("sessions_no_nullif"))
    same_pid("step7a", [rb[0][0], rb2[0][0]] + [q(a, "A", "select pg_backend_pid()")[0][0]])
    check("step7a", "current_user through pooler", "crux_app", rb[0][1])
    check("step7a", "setting on fresh backend", None, rb[0][2])
    check("step7a", "rows, nullif policy", 0, rb[0][3])
    check("step7a", "rows, no-nullif policy (no error)", 0, rb2[0][3])
    log()

    # ---------------------------------------------------------------- step 5
    log("## Step 5a: positive control, session-level SET by A in autocommit")
    a, b = fresh_backend(admin, a, b)
    t0 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ra = q(a, "A", f"set app.home_id = '{ANA}'")
    ra = q(a, "A", probe_sql())
    rb = q(b, "B", probe_sql())
    same_pid("step5a", [ra[0][0], rb[0][0]])
    check("step5a", "B reads A's leftover setting (leak expected)", ANA, rb[0][2])
    check("step5a", "B sees Ana's rows (leak expected)", 3, rb[0][3])
    backends(admin, "step5a")
    log()

    log("## Step 5b: positive control, set_config(..., false) by A in autocommit, new backend")
    a, b = fresh_backend(admin, a, b)
    ra = q(a, "A", "select set_config('app.home_id', %s, false)", (ANA,))
    ra = q(a, "A", probe_sql())
    rb = q(b, "B", probe_sql())
    same_pid("step5b", [ra[0][0], rb[0][0]])
    check("step5b", "B reads A's leftover setting (leak expected)", ANA, rb[0][2])
    check("step5b", "B sees Ana's rows (leak expected)", 3, rb[0][3])
    log()

    log("## Step 5c: A's session-level setting left behind on purpose; B uses the safe pattern")
    # Backend still carries Ana from 5b.
    rb_before = q(b, "B", probe_sql())
    with b.transaction():
        q(b, "B", "select set_config('app.home_id', %s, true)", (BEN,))
        rb_in = q(b, "B", probe_sql())
    rb_after = q(b, "B", probe_sql())
    same_pid("step5c", [rb_before[0][0], rb_in[0][0], rb_after[0][0]])
    check("step5c", "B inside its own transaction sees only Ben's rows", (BEN, 2), (rb_in[0][2], rb_in[0][3]))
    check("step5c", "after B commits, Ana's session value is back (still leaked)", (ANA, 3),
          (rb_after[0][2], rb_after[0][3]))
    log()

    log("## Step 8a: Supavisor log lines since the session-level SET (local txn_mode_leak_action="
        f"{leak_action!r})")
    lines = docker_logs_since(t0)
    hits = [ln for ln in lines if any(k in ln.lower() for k in ("leak", "set ", "session state", "warn", "error"))]
    log(f"  [docker] {len(lines)} pooler log lines since {t0}; {len(hits)} mention leak/SET/warn/error")
    for ln in hits[:40]:
        log(f"  [docker]   {ln.encode('ascii', 'replace').decode('ascii')}")
    check("step8a", "local leak action value", "ignore", leak_action)
    log()

    # ---------------------------------------------------------------- step 6
    log("## Step 6: safe pattern, transaction-local setting, on a new backend")
    a, b = fresh_backend(admin, a, b)

    log("### 6a: A sets Ana with set_config(..., true) inside a transaction, commits")
    with a.transaction():
        q(a, "A", "select set_config('app.home_id', %s, true)", (ANA,))
        ra = q(a, "A", probe_sql())
    rb = q(b, "B", probe_sql())
    same_pid("step6a", [ra[0][0], rb[0][0]])
    check("step6a", "A inside its transaction sees Ana's rows", (ANA, 3), (ra[0][2], ra[0][3]))
    check("step6a", "B sees no setting value (NULL or empty)", True, rb[0][2] in (None, ""))
    check("step6a", "B sees 0 rows", 0, rb[0][3])
    log(f"  [note] step6a B setting repr after a committed local set: {rb[0][2]!r}")

    log("### 6b: same, but A rolls back")
    with a.transaction():
        q(a, "A", "select set_config('app.home_id', %s, true)", (ANA,))
        ra = q(a, "A", probe_sql())
        raise psycopg.Rollback()
    rb = q(b, "B", probe_sql())
    same_pid("step6b", [ra[0][0], rb[0][0]])
    check("step6b", "A inside its transaction sees Ana's rows", (ANA, 3), (ra[0][2], ra[0][3]))
    check("step6b", "B sees no setting value (NULL or empty)", True, rb[0][2] in (None, ""))
    check("step6b", "B sees 0 rows", 0, rb[0][3])

    log("### 6c: same, but A errors mid-transaction (division by zero)")
    err = None
    try:
        with a.transaction():
            q(a, "A", "select set_config('app.home_id', %s, true)", (ANA,))
            ra = q(a, "A", probe_sql())
            q(a, "A", "select 1/0")
    except psycopg.Error as e:
        err = f"{type(e).__name__}: {str(e).strip()}"
        log(f"  [A] error, transaction rolled back by psycopg: {err!r}")
    rb = q(b, "B", probe_sql())
    same_pid("step6c", [ra[0][0], rb[0][0]])
    check("step6c", "A's mid-transaction error raised", True, err is not None)
    check("step6c", "B sees no setting value (NULL or empty)", True, rb[0][2] in (None, ""))
    check("step6c", "B sees 0 rows", 0, rb[0][3])

    log("### 6d: SET LOCAL statement form inside a transaction, commit")
    with a.transaction():
        q(a, "A", f"set local app.home_id = '{ANA}'")
        ra = q(a, "A", probe_sql())
    rb = q(b, "B", probe_sql())
    same_pid("step6d", [ra[0][0], rb[0][0]])
    check("step6d", "A inside its transaction sees Ana's rows", (ANA, 3), (ra[0][2], ra[0][3]))
    check("step6d", "B sees 0 rows", 0, rb[0][3])

    log("### 6e: B sets Ben in its own transaction on the same backend")
    with b.transaction():
        q(b, "B", "select set_config('app.home_id', %s, true)", (BEN,))
        rb = q(b, "B", probe_sql())
    ra = q(a, "A", probe_sql())
    same_pid("step6e", [ra[0][0], rb[0][0]])
    check("step6e", "B sees only Ben's 2 rows", (BEN, 2), (rb[0][2], rb[0][3]))
    check("step6e", "A afterwards sees 0 rows", 0, ra[0][3])

    log("### 6f: pitfall, set_config(..., true) as its own autocommit statement")
    q(a, "A", "select set_config('app.home_id', %s, true)", (ANA,))
    ra = q(a, "A", probe_sql())
    check("step6f", "next autocommit statement sees 0 rows", 0, ra[0][3])

    log("### 6g: pitfall, SET LOCAL outside a transaction block")
    notices = []
    a.add_notice_handler(lambda d: notices.append(f"{d.severity}: {d.message_primary}"))
    q(a, "A", f"set local app.home_id = '{ANA}'")
    ra = q(a, "A", probe_sql())
    log(f"  [A] server notices: {notices!r}")
    check("step6g", "next statement sees 0 rows", 0, ra[0][3])
    check("step6g", "server warned", True, any("WARNING" in n for n in notices))
    log()

    # ---------------------------------------------------------------- step 7b
    log("## Step 7b: unset setting on a reused backend after a transaction-local set")
    # Backend has had app.home_id set locally (6a-6g) and never at session level.
    rb = q(b, "B", probe_sql("sessions"))
    check("step7b", "setting on reused backend", "", rb[0][2])
    check("step7b", "rows, nullif policy", 0, rb[0][3])
    no_nullif_err = None
    try:
        rb2 = q(b, "B", probe_sql("sessions_no_nullif"))
        log(f"  [B] no-nullif rows: {rb2[0][3]!r}")
    except psycopg.Error as e:
        no_nullif_err = f"{type(e).__name__}: {str(e).strip()}"
        log(f"  [B] no-nullif policy error: {no_nullif_err!r}")
    rpid = q(a, "A", "select pg_backend_pid()")
    rpid_b = q(b, "B", "select pg_backend_pid()")
    same_pid("step7b", [rb[0][0], rpid[0][0], rpid_b[0][0]])
    check("step7b", "no-nullif policy raises on empty string", True,
          no_nullif_err is not None and "uuid" in no_nullif_err)
    log()

    a.close()
    b.close()
    admin.close()

    # ---------------------------------------------------------------- summary
    log("## Summary")
    failed = [c for c in checks if not c[4]]
    log(f"  checks: {len(checks)}  passed: {len(checks) - len(failed)}  failed: {len(failed)}")
    for c in failed:
        log(f"  [FAIL] {c[0]} {c[1]}: expected={c[2]!r} observed={c[3]!r}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
