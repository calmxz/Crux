"""Seed pre-confirmed debug accounts into Supabase Auth.

Real registrations go through email confirmation. Debug accounts are created
with `email_confirm: true` via the GoTrue Admin API so they can sign in
immediately. Requires SUPABASE_URL + SUPABASE_SECRET_KEY (service role) from
the backend env. The secret key is backend-only and never shipped to clients.

Usage (from backend/):
    python scripts/seed_debug_accounts.py [path/to/debug-accounts.txt]

Default account list: docs/dev/debug-accounts.txt (gitignored).
File format: one `email,password` per line; blank lines and `#` comments
are ignored.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

# Make `config` importable when run as a script from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ACCOUNTS = _REPO_ROOT / "docs" / "dev" / "debug-accounts.txt"
_EXISTS_MARKERS = ("already been registered", "email_exists", "already registered")


def parse_accounts(text: str) -> list[tuple[str, str]]:
    """Parse `email,password` lines, skipping blanks and `#` comments."""
    accounts: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        email, _, password = stripped.partition(",")
        email = email.strip()
        password = password.strip()
        if email and password:
            accounts.append((email, password))
    return accounts


def create_account(client: httpx.Client, email: str, password: str) -> str:
    """Create one pre-confirmed account. Returns 'created' or 'exists'.

    Raises RuntimeError on any other non-success response.
    """
    resp = client.post(
        "/auth/v1/admin/users",
        json={"email": email, "password": password, "email_confirm": True},
    )
    if resp.status_code in (200, 201):
        return "created"
    body = resp.text.lower()
    if resp.status_code in (422, 409, 400) and any(m in body for m in _EXISTS_MARKERS):
        return "exists"
    # Do not log email or the response body: both can carry the submitted
    # password (clear-text logging of sensitive data). Status code is enough
    # to diagnose; the caller adds the account index for context.
    raise RuntimeError(f"Failed to create account: HTTP {resp.status_code}")


def run(accounts_path: Path) -> int:
    if not settings.supabase_url or not settings.supabase_secret_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY must be set.", file=sys.stderr)
        return 2
    if not accounts_path.exists():
        print(f"ERROR: account file not found: {accounts_path}", file=sys.stderr)
        print("Create it from docs/dev/debug-accounts.example.txt.", file=sys.stderr)
        return 2

    accounts = parse_accounts(accounts_path.read_text(encoding="utf-8"))
    if not accounts:
        print(f"No accounts found in {accounts_path}.")
        return 0

    key = settings.supabase_secret_key
    with httpx.Client(
        base_url=settings.supabase_url.rstrip("/"),
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=30.0,
    ) as client:
        total = len(accounts)
        for index, (email, password) in enumerate(accounts, start=1):
            try:
                result = create_account(client, email, password)
            except RuntimeError as e:
                print(f"  account {index}/{total}: {e}", file=sys.stderr)
                return 1
            print(f"  {result:>8}  account {index}/{total}")
    print(f"Done. {len(accounts)} account(s) processed.")
    return 0


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_ACCOUNTS
    return run(path)


if __name__ == "__main__":
    raise SystemExit(main())
