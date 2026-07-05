"""Data models for parsed Git diffs."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """The type of change applied to a line."""

    ADDED = "added"
    REMOVED = "removed"
    CONTEXT = "context"


class FileStatus(str, Enum):
    """High-level status of a file in a diff."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class HunkLine(BaseModel):
    """A single line within a diff hunk."""

    change_type: ChangeType
    content: str = Field(description="The line content (without the leading +/-/ ).")
    old_line_number: int | None = Field(
        default=None,
        description="Line number in the old file (None for added lines).",
    )
    new_line_number: int | None = Field(
        default=None,
        description="Line number in the new file (None for removed lines).",
    )


class Hunk(BaseModel):
    """A contiguous block of changes within a file diff."""

    old_start: int = Field(description="Starting line in the old file.")
    old_count: int = Field(description="Number of lines from the old file.")
    new_start: int = Field(description="Starting line in the new file.")
    new_count: int = Field(description="Number of lines in the new file.")
    header: str = Field(default="", description="Optional hunk header (function name, etc.).")
    lines: list[HunkLine] = Field(default_factory=list)

    @property
    def added_lines(self) -> list[HunkLine]:
        """Return only the added lines in this hunk."""
        return [line for line in self.lines if line.change_type == ChangeType.ADDED]

    @property
    def removed_lines(self) -> list[HunkLine]:
        """Return only the removed lines in this hunk."""
        return [line for line in self.lines if line.change_type == ChangeType.REMOVED]


class FileDiff(BaseModel):
    """Parsed diff for a single file."""

    old_path: str = Field(description="Path in the old tree (or /dev/null for new files).")
    new_path: str = Field(description="Path in the new tree (or /dev/null for deleted files).")
    status: FileStatus = Field(default=FileStatus.MODIFIED)
    language: str = Field(
        default="",
        description="Programming language inferred from the file extension.",
    )
    is_binary: bool = Field(default=False)
    hunks: list[Hunk] = Field(default_factory=list)

    @property
    def path(self) -> str:
        """Return the most relevant file path for display."""
        if self.new_path and self.new_path != "/dev/null":
            return self.new_path
        return self.old_path

    @property
    def total_additions(self) -> int:
        """Total number of added lines across all hunks."""
        return sum(len(h.added_lines) for h in self.hunks)

    @property
    def total_deletions(self) -> int:
        """Total number of removed lines across all hunks."""
        return sum(len(h.removed_lines) for h in self.hunks)
