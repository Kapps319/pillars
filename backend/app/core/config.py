"""Central application settings.

Every value can be overridden via environment variables (see .env.example at the
repository root). Missing optional keys (API keys for external sources / LLM
providers) must never crash the app — adapters check availability at runtime
and are skipped with a log line instead.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config — YAML keyword lists, scoring weights and LLM prompts live
# here so behaviour (and later, new languages) can be changed without code edits.
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "AI Intent Lead Finder"
    environment: Literal["local", "test", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    # --- Database / cache ---
    database_url: str = "postgresql+psycopg://leadfinder:leadfinder@localhost:5432/leadfinder"
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth ---
    # SECRET_KEY signs JWTs and derives the Fernet key used to encrypt stored
    # integration API keys. MUST be overridden in production.
    secret_key: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- LLM classifier ---
    # rules  -> RulesOnlyClient, needs no API key (default; app runs keyless)
    # claude -> ClaudeClient, requires ANTHROPIC_API_KEY
    # openai -> OpenAIClient, requires OPENAI_API_KEY
    llm_provider: Literal["rules", "claude", "openai"] = "rules"
    anthropic_api_key: str | None = None  # API key required for LLM_PROVIDER=claude
    anthropic_model: str = "claude-opus-4-8"
    openai_api_key: str | None = None  # API key required for LLM_PROVIDER=openai
    openai_model: str = "gpt-4o-mini"

    # --- Data sources ---
    # Comma-separated adapter keys. Adapters missing their API keys degrade to
    # "unavailable" and are skipped at run time (never crash).
    sources_enabled: str = "mock,reddit,google,manual_url"
    reddit_client_id: str | None = None  # API key required for the Reddit source
    reddit_client_secret: str | None = None  # API key required for the Reddit source
    reddit_user_agent: str = "leadfinder/0.1 by leadfinder-app"
    google_api_key: str | None = None  # API key required for the Google CSE source
    google_cse_id: str | None = None  # API key required for the Google CSE source
    twitter_bearer: str | None = None  # X/Twitter is paid; adapter ships disabled by default

    # --- Generic public-page scraper (manual URL ingestion) ---
    scraper_user_agent: str = "LeadFinderBot/0.1 (+https://example.com/bot; respectful crawler)"
    scraper_timeout_seconds: float = 10.0
    scraper_rate_limit_seconds: float = 2.0  # min delay between requests to the same host

    # --- Search backend ---
    # postgres      -> Postgres full-text search (MVP default, no extra infra)
    # elasticsearch -> placeholder flag; falls back to postgres with a warning
    search_backend: Literal["postgres", "elasticsearch"] = "postgres"

    # --- Background jobs ---
    # When Celery/Redis are unreachable the API falls back to running scraping
    # jobs synchronously in-process so the demo works without a worker.
    celery_enabled: bool = True

    # --- Bootstrapping ---
    seed_on_startup: bool = False  # compose sets this true for the demo

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def enabled_source_keys(self) -> list[str]:
        return [s.strip() for s in self.sources_enabled.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
