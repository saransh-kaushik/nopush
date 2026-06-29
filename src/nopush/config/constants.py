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
DEFAULT_MAX_FILES: int = 50
DEFAULT_TIMEOUT_SECONDS: int = 120

# ---------------------------------------------------------------------------
# Supported values
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS: list[str] = ["openai", "anthropic", "gemini"]

SUPPORTED_REVIEW_DEPTHS: list[str] = ["minimal", "standard", "thorough"]
