"""Data models for code review results."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level of a review comment."""

    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NITPICK = "nitpick"


class ReviewComment(BaseModel):
    """A single review comment from the AI."""

    severity: Severity
    file_path: str = Field(description="Path to the file containing the issue.")
    line_number: int = Field(description="Line number in the new file.")
    title: str = Field(description="Brief one-line summary.")
    explanation: str = Field(description="Detailed explanation of the issue.")
    suggestion: str | None = Field(
        default=None,
        description="Suggested fix or improved code. None if not applicable.",
    )


class ReviewResult(BaseModel):
    """The complete result of a code review."""

    comments: list[ReviewComment] = Field(default_factory=list)
    files_reviewed: int = Field(default=0, description="Number of files in the diff.")
    model: str = Field(default="", description="Model used for the review.")
    provider: str = Field(default="", description="Provider used for the review.")

    @property
    def total_issues(self) -> int:
        """Total number of issues found."""
        return len(self.comments)

    def count_by_severity(self) -> dict[Severity, int]:
        """Return a count of comments grouped by severity."""
        counts: dict[Severity, int] = {s: 0 for s in Severity}
        for comment in self.comments:
            counts[comment.severity] += 1
        return counts
