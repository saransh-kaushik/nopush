"""Git diff parsing and related utilities.

Public API
----------
- :func:`get_staged_diff` — raw diff text for staged changes.
- :func:`get_diff` — raw diff text between two refs.
- :func:`get_file_diff` — raw diff for specific file paths.
- :func:`parse_diff` — parse raw unified diff into structured objects.
- Data models: :class:`FileDiff`, :class:`Hunk`, :class:`HunkLine`,
  :class:`FileStatus`, :class:`ChangeType`.
"""

from nopush.git.diff_parser import get_diff, get_file_diff, get_staged_diff, parse_diff
from nopush.git.models import ChangeType, FileDiff, FileStatus, Hunk, HunkLine

__all__ = [
    "ChangeType",
    "FileDiff",
    "FileStatus",
    "Hunk",
    "HunkLine",
    "get_diff",
    "get_file_diff",
    "get_staged_diff",
    "parse_diff",
]
