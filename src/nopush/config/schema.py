"""Pydantic models for NoPush configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from nopush.config.constants import (
    DEFAULT_MAX_FILES,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_REVIEW_DEPTH,
    DEFAULT_TIMEOUT_SECONDS,
)

# ---------------------------------------------------------------------------
# Provider credentials
# ---------------------------------------------------------------------------


class ProviderCredentials(BaseModel):
    """Credentials for a single LLM provider."""

    provider: str = Field(default=DEFAULT_PROVIDER, description="LLM provider name.")
    api_key: str = Field(default="", description="API key for the provider.")
    model: str = Field(default=DEFAULT_MODEL, description="Model identifier.")
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL (e.g. for Azure OpenAI).",
    )


# ---------------------------------------------------------------------------
# Project configuration
# ---------------------------------------------------------------------------


class NoPushConfig(BaseModel):
    """Top-level configuration model for NoPush.

    This represents the merged configuration from all sources:
    CLI flags > env vars > project ``nopush.yaml`` > user config > defaults.
    """

    # Provider settings
    provider: str = Field(default=DEFAULT_PROVIDER, description="LLM provider name.")
    model: str = Field(default=DEFAULT_MODEL, description="Model identifier.")
    api_key: str = Field(default="", description="API key (prefer credentials file).")
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL (e.g. for Azure OpenAI).",
    )

    # Review behaviour
    review_depth: Literal["minimal", "standard", "thorough"] = Field(
        default=DEFAULT_REVIEW_DEPTH,
        description="How thorough the review should be.",
    )
    max_files: int = Field(
        default=DEFAULT_MAX_FILES,
        description="Maximum number of files to include in a single review.",
    )

    # File filtering
    ignore: list[str] = Field(
        default_factory=list,
        description="Glob patterns for files/directories to exclude from review.",
    )

    # Timeouts
    timeout: int = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        description="Request timeout in seconds for LLM API calls.",
    )

    # GitHub integration (optional)
    github_token: str = Field(
        default="",
        description="GitHub personal access token for PR comments.",
    )
