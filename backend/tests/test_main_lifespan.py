"""Lifespan startup guard: prod must not boot without SUPABASE_URL configured.

Dev/test must NOT be affected — CI's backend job and the `client` fixture in
conftest.py never set SUPABASE_URL, and both rely on lifespan() completing
without raising.
"""

import pytest

import main as main_module
from config import settings


@pytest.fixture
def isolated_db(monkeypatch):
    """Route create_tables() to a no-op -- these tests must not touch a real
    database (Postgres in dev, an unmigrated file in CI) just to exercise
    the boot guard."""
    monkeypatch.setattr(main_module, "create_tables", lambda: None)


@pytest.mark.asyncio
async def test_prod_without_supabase_url_raises(monkeypatch, isolated_db):
    monkeypatch.setattr(settings, "env", "prod")
    monkeypatch.setattr(settings, "database_url", "postgresql://u:p@host:5432/db")
    monkeypatch.setattr(settings, "supabase_url", "")

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        async with main_module.lifespan(main_module.app):
            pass


@pytest.mark.asyncio
async def test_dev_without_supabase_url_does_not_raise(monkeypatch, isolated_db):
    monkeypatch.setattr(settings, "env", "dev")
    monkeypatch.setattr(settings, "supabase_url", "")
    # F-61: validate_jwks_startup now fail-fasts on unconfigured auth unless
    # AUTH_OPTIONAL is set -- this test is exercising the dev/prod boot guard,
    # not the auth guard, so opt out of it.
    monkeypatch.setattr(settings, "auth_optional", True)

    async with main_module.lifespan(main_module.app):
        pass


@pytest.mark.asyncio
async def test_prod_with_supabase_url_does_not_raise(monkeypatch, isolated_db):
    monkeypatch.setattr(settings, "env", "prod")
    monkeypatch.setattr(settings, "database_url", "postgresql://u:p@host:5432/db")
    monkeypatch.setattr(settings, "supabase_url", "https://real-project.supabase.co")
    monkeypatch.setattr(main_module, "validate_jwks_startup", lambda: None)

    async with main_module.lifespan(main_module.app):
        pass
