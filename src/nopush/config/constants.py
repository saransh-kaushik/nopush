"""Default values, paths, and environment variable names."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------

#: User-level configuration directory (e.g. ``~/.nopush/``).
USER_CONFIG_DIR: Path = Path.home() / ".nopush"

#: User-level credentials file.
CREDENTIALS_FILE: Path = USER_CONFIG_DIR / "credentials.yaml"

#: User-level default configuration file.
USER_CONFIG_FILE: Path = USER_CONFIG_DIR / "config.yaml"

#: Project-level configuration file name (discovered by walking up from CWD).
PROJECT_CONFIG_FILENAME: str = "nopush.yaml"

# ---------------------------------------------------------------------------
# Environment variable names
# ---------------------------------------------------------------------------

ENV_PROVIDER: str = "NOPUSH_PROVIDER"
ENV_API_KEY: str = "NOPUSH_API_KEY"
ENV_MODEL: str = "NOPUSH_MODEL"
ENV_GITHUB_TOKEN: str = "GITHUB_TOKEN"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER: str = "openai"
DEFAULT_MODEL: str = "gpt-4.1"
DEFAULT_REVIEW_DEPTH: Literal["minimal", "standard", "thorough"] = "standard"

# Default model per provider — must be a real, currently-available model ID.
PROVIDER_DEFAULT_MODEL_FALLBACK: dict[str, str] = {
    "openai": "gpt-4.1",
    "gemini": "gemini-3.5-flash",
    "anthropic": "claude-sonnet-4-5",
}
DEFAULT_MAX_FILES: int = 50
DEFAULT_TIMEOUT_SECONDS: int = 120

# ---------------------------------------------------------------------------
# Supported values
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS: list[str] = ["openai", "gemini", "anthropic"]

SUPPORTED_REVIEW_DEPTHS: list[str] = ["minimal", "standard", "thorough"]

# ---------------------------------------------------------------------------
# Model catalogs (updated July 2026)
# Use the special sentinel "other" to allow custom model entry.
# ---------------------------------------------------------------------------

#: Canonical model IDs for each provider, ordered newest-first.
#: The last entry is the sentinel for entering a custom model name.
PROVIDER_MODELS: dict[str, list[tuple[str, str]]] = {
    "openai": [
        ("gpt-5.5", "GPT-5.5 — flagship, complex reasoning & coding"),
        ("gpt-5.4", "GPT-5.4 — high-performance, professional tasks"),
        ("gpt-5.4-pro", "GPT-5.4 Pro — higher precision variant"),
        ("gpt-5.4-mini", "GPT-5.4 mini — optimised for latency & cost"),
        ("gpt-5.4-nano", "GPT-5.4 nano — high-volume, simple tasks"),
        ("o3-pro", "o3 Pro — reasoning model, deep thinking"),
        ("o3", "o3 — reasoning model"),
        ("o4-mini", "o4-mini — fast reasoning, coding & vision"),
        ("gpt-4.1", "GPT-4.1 — previous generation, widely deployed"),
        ("gpt-4o", "GPT-4o — previous generation"),
        ("other", "Other — enter a custom model ID"),
    ],
    "gemini": [
        ("gemini-3.5-pro", "Gemini 3.5 Pro — flagship, advanced reasoning"),
        ("gemini-3.5-flash", "Gemini 3.5 Flash — fast agentic workhorse"),
        ("gemini-3.1-pro", "Gemini 3.1 Pro — reasoning & analysis"),
        ("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite — cost-sensitive workloads"),
        ("gemini-2.5-pro", "Gemini 2.5 Pro — previous generation"),
        ("gemini-2.5-flash", "Gemini 2.5 Flash — previous generation"),
        ("other", "Other — enter a custom model ID"),
    ],
    "anthropic": [
        ("claude-sonnet-5", "Claude Sonnet 5 — balanced, agentic & coding"),
        ("claude-opus-4-8", "Claude Opus 4.8 — premium, enterprise tasks"),
        ("claude-haiku-4-5", "Claude Haiku 4.5 — fastest & most cost-effective"),
        ("claude-fable-5", "Claude Fable 5 — most capable, long-running tasks"),
        ("other", "Other — enter a custom model ID"),
    ],
}

#: Default model to pre-select for each provider.
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4.1",
    "gemini": "gemini-3.5-flash",
    "anthropic": "claude-sonnet-5",
}
