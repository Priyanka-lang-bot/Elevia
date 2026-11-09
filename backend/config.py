"""Settings, read from environment variables (or a local .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv is optional at runtime
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    db_path: str
    llm_provider: str  # "anthropic", "openai", or "mock"
    llm_api_key: str
    llm_model: str
    llm_base_url: str
    llm_timeout: float
    teacher_pin: str
    retest_delay_hours: float
    allow_early_retest: bool
    cors_origins: list[str]

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider in ("anthropic", "openai") and bool(self.llm_api_key)


def get_settings() -> Settings:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    default_model = {"anthropic": "claude-haiku-4-5", "openai": "gpt-4o-mini"}.get(provider, "")
    default_base = {
        "anthropic": "https://api.anthropic.com",
        "openai": "https://api.openai.com/v1",
    }.get(provider, "")
    return Settings(
        db_path=os.getenv("ELEVIA_DB_PATH", str(ROOT / "elevia.db")),
        llm_provider=provider,
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", default_model).strip(),
        llm_base_url=os.getenv("LLM_BASE_URL", default_base).strip().rstrip("/"),
        llm_timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
        teacher_pin=os.getenv("TEACHER_PIN", "").strip(),
        retest_delay_hours=float(os.getenv("RETEST_DELAY_HOURS", "24")),
        allow_early_retest=_bool("ALLOW_EARLY_RETEST", True),
        cors_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",") if o.strip()],
    )
