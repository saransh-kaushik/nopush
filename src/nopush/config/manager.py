"""Load, save, and merge configuration from multiple sources."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from nopush.config.constants import (
    CREDENTIALS_FILE,
    ENV_API_KEY,
    ENV_MODEL,
    ENV_PROVIDER,
    PROJECT_CONFIG_FILENAME,
    USER_CONFIG_DIR,
    USER_CONFIG_FILE,
)
from nopush.config.schema import NoPushConfig, ProviderCredentials


class ConfigManager:
    """Discovers, loads, and merges NoPush configuration.

    Resolution order (highest priority first):

    1. Explicit overrides (CLI flags)
    2. Environment variables
    3. Project-level ``nopush.yaml``
    4. User-level ``~/.nopush/config.yaml``
    5. Built-in defaults
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def load(overrides: dict[str, Any] | None = None) -> NoPushConfig:
        """Return a fully-resolved :class:`NoPushConfig`.

        Parameters
        ----------
        overrides:
            Key/value pairs that take highest priority (e.g. from CLI flags).
        """
        layers: dict[str, Any] = {}

        # Layer 5 — defaults (handled by Pydantic)

        # Layer 4 — user config
        user_cfg = ConfigManager._load_yaml(USER_CONFIG_FILE)
        layers.update(user_cfg)

        # Layer 3 — project config
        project_cfg_path = ConfigManager._find_project_config()
        if project_cfg_path is not None:
            project_cfg = ConfigManager._load_yaml(project_cfg_path)
            layers.update(project_cfg)

        # Layer 2 — environment variables
        env_layer = ConfigManager._load_env()
        layers.update(env_layer)

        # Layer 1 — explicit overrides
        if overrides:
            layers.update(overrides)

        # Merge credentials file as the lowest-priority layer (provider, model, api_key).
        # Higher layers (env vars, project config, CLI flags) will override these.
        creds = ConfigManager.load_credentials()
        if creds.api_key:
            layers.setdefault("api_key", creds.api_key)
        if creds.provider:
            layers.setdefault("provider", creds.provider)
        if creds.model:
            layers.setdefault("model", creds.model)

        return NoPushConfig(**layers)

    @staticmethod
    def load_credentials() -> ProviderCredentials:
        """Load credentials from ``~/.nopush/credentials.yaml``."""
        data = ConfigManager._load_yaml(CREDENTIALS_FILE)
        return ProviderCredentials(**data)

    @staticmethod
    def save_credentials(credentials: ProviderCredentials) -> Path:
        """Persist credentials to ``~/.nopush/credentials.yaml``.

        Returns the path to the saved file.
        """
        USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_FILE.write_text(
            yaml.dump(
                credentials.model_dump(exclude_none=True),
                default_flow_style=False,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        # Restrict permissions — credentials should be user-readable only.
        CREDENTIALS_FILE.chmod(0o600)
        return CREDENTIALS_FILE

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        """Read a YAML file and return its contents as a dict.

        Returns an empty dict if the file does not exist or is empty.
        """
        if not path.is_file():
            return {}
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}

    @staticmethod
    def _load_env() -> dict[str, Any]:
        """Extract NoPush configuration from environment variables."""
        env: dict[str, Any] = {}
        if val := os.environ.get(ENV_PROVIDER):
            env["provider"] = val
        if val := os.environ.get(ENV_API_KEY):
            env["api_key"] = val
        if val := os.environ.get(ENV_MODEL):
            env["model"] = val
        return env

    @staticmethod
    def _find_project_config() -> Path | None:
        """Walk up from CWD to locate the nearest ``nopush.yaml``."""
        current = Path.cwd().resolve()
        for parent in [current, *current.parents]:
            candidate = parent / PROJECT_CONFIG_FILENAME
            if candidate.is_file():
                return candidate
        return None
