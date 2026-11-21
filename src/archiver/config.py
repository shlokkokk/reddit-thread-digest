"""YAML settings and Reddit OAuth environment handling."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv


DEFAULT_CONFIG_PATH = Path("config/settings.example.yaml")


@dataclass(frozen=True)
class RedditCredentials:
    """Reddit OAuth credentials read from environment variables."""

    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str


def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    """Load settings YAML, falling back to safe built-in defaults."""
    if path is None:
        local_path = Path("config/settings.yaml")
        path = local_path if local_path.exists() else DEFAULT_CONFIG_PATH

    settings_path = Path(path)
    if not settings_path.exists():
        return default_settings()

    with settings_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Configuration root must be a YAML mapping")

    settings = default_settings()
    settings.update(loaded)
    settings["write_cooldown_seconds"] = max(
        120, int(settings.get("write_cooldown_seconds", 120))
    )
    settings["requests_per_minute"] = min(
        9, max(1, int(settings.get("requests_per_minute", 9)))
    )
    return settings


def default_settings() -> dict[str, Any]:
    """Return conservative defaults independent of the YAML file."""
    return {
        "subreddits": [
            "AskReddit",
            "NoStupidQuestions",
            "CasualConversation",
            "explainlikeimfive",
            "Advice",
        ],
        "write_cooldown_seconds": 120,
        "requests_per_minute": 9,
        "category_tags": {
            "advice": "Community Advice",
            "faq": "Frequently Asked Question",
            "discussion": "Discussion",
        },
        "templates": {
            "digest_title": "Weekly Community Digest",
            "archive_title": "Archived Context",
        },
        "opt_out": {
            "commands": ["!optout"],
            "content_exclusion_filters": ["nsfw", "personally identifying"],
        },
    }


load_config = load_settings


def load_credentials(
    environ: Mapping[str, str] | None = None,
) -> RedditCredentials:
    """Load Reddit OAuth credentials from .env and the environment."""
    load_dotenv()
    values = os.environ if environ is None else environ
    return RedditCredentials(
        client_id=values.get("REDDIT_CLIENT_ID", ""),
        client_secret=values.get("REDDIT_CLIENT_SECRET", ""),
        username=values.get("REDDIT_USERNAME", ""),
        **{"password": values.get("REDDIT_PASSWORD", "")},
        user_agent=values.get(
            "REDDIT_USER_AGENT",
            "reddit-thread-digest/1.0",
        ),
    )
