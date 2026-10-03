import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data"

_ENV_FILE = (
    None
    if os.environ.get("CRUX_SKIP_DOTENV") == "1"
    else str(_REPO_ROOT / ".env")
)


REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    model: str = "gemini/gemini-3.5-flash-lite"
    embedding_model: str = "gemini/gemini-embedding-2"
    daily_cap: int = 50
    database_url: str = f"sqlite:///{(_DATA_DIR / 'app.db').as_posix()}"
    embedding_dim: int = 768
    uploads_path: str = (_DATA_DIR / "uploads").as_posix()
    # F-15: where uploaded blobs live. "local" writes under uploads_path
    # (dev / docker / tests); "r2" targets Cloudflare R2 (prod).
    uploads_store: str = "local"
    r2_endpoint: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    # B-10: pool sizing must respect Render instance + Supabase pooler client
    # limits; env-tunable so the deploy can be sized without a code change.
    db_pool_size: int = 5
    db_max_overflow: int = 5
    # F-01: how long a request waits for a pooled connection before failing.
    # SQLAlchemy's default is 30s, which turns pool exhaustion into a pile-up
    # of hung requests instead of fast, visible load shedding.
    db_pool_timeout_s: float = 5.0
    # G-07 follow-up: seconds psycopg waits for the TCP connect before failing.
    db_connect_timeout_s: float = 5.0
    llm_stub: bool = False
    debug_timing: bool = False
    # The web process drains the ingestion queue itself by default. Set false
    # only when a dedicated worker service (python -m worker) runs alongside.
    ingest_in_process: bool = True
    cors_origins: str = "http://localhost:5173"
    env: str = "dev"
    log_level: str = "INFO"
    # F-61: allow booting without Supabase auth config (local hacking, CI
    # subsets). Default False: a deploy missing SUPABASE_URL dies at startup
    # instead of 500ing "auth_not_configured" on every authenticated request.
    auth_optional: bool = False

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_jwks_url_override: str = ""
    supabase_secret_key: str = ""
    llm_soft_cap_usd: float = 2.00
    llm_hard_cap_usd: float = 3.00
    # B-05: provisional per-turn charge reserved at the cost gate, released
    # when the turn ends.
    llm_turn_reserve_usd: float = 0.02
    max_chunks: int = 5000
    # F-03: upload-time page/slide ceiling for .pdf/.pptx. Cheap structural
    # check that rejects a document before a worker loads and tokenises it.
    max_pages: int = 400
    global_daily_cost_cap_usd: float | None = None
    llm_temperature: float = 0.3
    summary_temperature: float = 0.0
    retrieval_fallback_threshold: float = 0.75
    # G-11: cosine-similarity floor for surfacing a retrieved chunk as a
    # citation; None-scored chunks pass.
    citation_min_similarity: float = 0.25
    # F-10: SET LOCAL hnsw.ef_search on the retrieval transaction; pgvector
    # default 40.
    hnsw_ef_search: int = 100

    # F-06: explicit LiteLLM timeouts. Chat streams get the longest budget;
    # summaries and embeddings are shorter single-shot calls.
    llm_timeout_s: float = 30.0
    summary_timeout_s: float = 20.0
    embedding_timeout_s: float = 15.0

    # B-07: per-user burst limit on paid endpoints (chat turn, upload, end,
    # check/complete). Rolling 60 s window, in-process (single Render
    # instance, single uvicorn worker). 0 disables. Independent of daily_cap.
    burst_limit_per_minute: int = 0

    # Bounded retry for transient provider failures on idempotent LiteLLM
    # embedding calls. Summaries (session end, rolling) and streaming chat are
    # not retried (design doc: summary falls back to the mechanical [auto]
    # summary). attempts = extra tries after the first; 0 disables.
    llm_retry_attempts: int = 2
    llm_retry_base_delay_s: float = 0.5

    # F-35: hard cap per profile concept list (confirmed_gaps,
    # mastered_concepts); oldest entries evicted at write time.
    max_profile_list: int = 40

    # C-03: non-multipart request bodies above this are rejected before
    # parsing.
    max_json_body_bytes: int = 64 * 1024

    # G-07: /ready DB probe budget.
    readiness_timeout_s: float = 2.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_jwks_url(self) -> str:
        if self.supabase_jwks_url_override:
            return self.supabase_jwks_url_override
        if not self.supabase_url:
            return ""
        return self.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"

    @property
    def llm_stub_enabled(self) -> bool:
        return self.llm_stub or self.gemini_api_key == "test"


settings = Settings()


def assert_prod_database(env: str, database_url: str) -> None:
    if env == "prod" and database_url.startswith("sqlite"):
        raise RuntimeError(
            "database_url must be a Postgres URL when env=prod (got sqlite). "
            "Set DATABASE_URL to the Supabase Postgres connection string."
        )


# Ensure runtime directories exist (data/uploads/ and parent of the sqlite file).
# The uploads dir is only used by the local store; with r2 the path may not
# even be creatable (read-only / in containers) and must not be touched.
for _p in (
    Path(settings.uploads_path) if settings.uploads_store == "local" else None,
    Path(settings.database_url.replace("sqlite:///", "", 1)).parent
    if settings.database_url.startswith("sqlite:///")
    else None,
):
    if _p is not None:
        _p.mkdir(parents=True, exist_ok=True)
