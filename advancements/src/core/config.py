"""
Configuration — loads .env and provides typed settings + constants.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class Settings:
    """Application settings populated from environment variables."""

    # LLM
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "google"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    google_model: str = field(default_factory=lambda: os.getenv("GOOGLE_MODEL", "gemini-2.0-flash"))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    )

    # Agent behaviour
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )
    agent_timeout: int = field(
        default_factory=lambda: int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
    )
    max_total_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOTAL_TOKENS", "50000"))
    )

    # Jira (future — stub for now)
    jira_url: str = field(default_factory=lambda: os.getenv("JIRA_URL", ""))
    jira_email: str = field(default_factory=lambda: os.getenv("JIRA_EMAIL", ""))
    jira_api_token: str = field(default_factory=lambda: os.getenv("JIRA_API_TOKEN", ""))
    jira_project_key: str = field(default_factory=lambda: os.getenv("JIRA_PROJECT_KEY", "KERN"))

    # Codebase
    kernel_repo_path: str = field(default_factory=lambda: os.getenv("KERNEL_REPO_PATH", ""))
    target_arch: str = field(default_factory=lambda: os.getenv("TARGET_ARCH", "arm64"))

    # Evolution
    evolution_db_path: str = field(
        default_factory=lambda: os.getenv("EVOLUTION_DB_PATH", ".kca/evolution.db")
    )


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the global settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
