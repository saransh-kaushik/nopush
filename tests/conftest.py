"""Shared pytest fixtures for the NoPush test suite."""

from __future__ import annotations

import pytest

from nopush.config.schema import NoPushConfig
from nopush.git.models import (
    ChangeType,
    FileDiff,
    FileStatus,
    Hunk,
    HunkLine,
)
from nopush.review.models import ReviewComment, ReviewResult, Severity


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def default_config() -> NoPushConfig:
    """Return a NoPushConfig with all defaults."""
    return NoPushConfig()


@pytest.fixture()
def config_with_key() -> NoPushConfig:
    """Return a config with a dummy API key set."""
    return NoPushConfig(api_key="sk-test-key-12345")


# ---------------------------------------------------------------------------
# Git fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_file_diff() -> FileDiff:
    """Return a simple FileDiff for a Python file."""
    return FileDiff(
        old_path="app/utils.py",
        new_path="app/utils.py",
        status=FileStatus.MODIFIED,
        language="python",
        hunks=[
            Hunk(
                old_start=10,
                old_count=3,
                new_start=10,
                new_count=5,
                lines=[
                    HunkLine(
                        change_type=ChangeType.CONTEXT,
                        content="def process(data):",
                        old_line_number=10,
                        new_line_number=10,
                    ),
                    HunkLine(
                        change_type=ChangeType.REMOVED,
                        content="    return data",
                        old_line_number=11,
                        new_line_number=None,
                    ),
                    HunkLine(
                        change_type=ChangeType.ADDED,
                        content="    if data is None:",
                        old_line_number=None,
                        new_line_number=11,
                    ),
                    HunkLine(
                        change_type=ChangeType.ADDED,
                        content='        raise ValueError("data cannot be None")',
                        old_line_number=None,
                        new_line_number=12,
                    ),
                    HunkLine(
                        change_type=ChangeType.ADDED,
                        content="    return data.strip()",
                        old_line_number=None,
                        new_line_number=13,
                    ),
                    HunkLine(
                        change_type=ChangeType.CONTEXT,
                        content="",
                        old_line_number=12,
                        new_line_number=14,
                    ),
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Review fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_review_comment() -> ReviewComment:
    """Return a sample review comment."""
    return ReviewComment(
        severity=Severity.WARNING,
        file_path="app/utils.py",
        line_number=11,
        title="Potential TypeError on non-string data",
        explanation=(
            "The code calls data.strip() but data might not be a string. "
            "Consider adding a type check or type annotation."
        ),
        suggestion="    return str(data).strip()",
    )


@pytest.fixture()
def sample_review_result(sample_review_comment: ReviewComment) -> ReviewResult:
    """Return a sample review result with one comment."""
    return ReviewResult(
        comments=[sample_review_comment],
        files_reviewed=1,
        model="gpt-4.1",
        provider="openai",
    )
