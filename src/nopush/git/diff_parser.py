"""Parse unified diff output from ``git diff``.

This module provides functions to:

1. Run ``git diff`` commands and capture the raw output.
2. Parse the raw unified diff text into structured :class:`FileDiff` objects.

All git interactions use ``subprocess`` directly — no third-party git library
is required.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import PurePosixPath

from nopush.git.models import ChangeType, FileDiff, FileStatus, Hunk, HunkLine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language detection (extension → language name)
# ---------------------------------------------------------------------------

_EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".dockerfile": "dockerfile",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".zig": "zig",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".tf": "hcl",
    ".vue": "vue",
    ".svelte": "svelte",
    ".dart": "dart",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}

# Regex for the ``@@ -old_start,old_count +new_start,new_count @@`` header
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$"
)


def _detect_language(file_path: str) -> str:
    """Infer programming language from the file extension."""
    suffix = PurePosixPath(file_path).suffix.lower()
    return _EXTENSION_MAP.get(suffix, "")


# ---------------------------------------------------------------------------
# Git interaction
# ---------------------------------------------------------------------------


def get_staged_diff(cwd: str | None = None) -> str:
    """Return the unified diff for staged changes.

    Parameters
    ----------
    cwd:
        Working directory to run git in. Defaults to the current directory.

    Raises
    ------
    RuntimeError
        If ``git`` is not available or the current directory is not a repo.
    """
    return _run_git("diff", "--staged", "--unified=3", "--no-color", cwd=cwd)


def get_diff(
    ref_a: str = "HEAD",
    ref_b: str | None = None,
    cwd: str | None = None,
) -> str:
    """Return the unified diff between two refs (or a ref and the working tree).

    Parameters
    ----------
    ref_a:
        The base reference (default ``HEAD``).
    ref_b:
        Optional second reference. If ``None``, diffs against the working tree.
    cwd:
        Working directory to run git in.
    """
    args = ["diff", ref_a, "--unified=3", "--no-color"]
    if ref_b is not None:
        args.insert(2, ref_b)
    return _run_git(*args, cwd=cwd)


def get_file_diff(paths: list[str], cwd: str | None = None) -> str:
    """Return the staged diff for specific file paths.

    Parameters
    ----------
    paths:
        File paths to restrict the diff to.
    cwd:
        Working directory to run git in.
    """
    return _run_git(
        "diff", "--staged", "--unified=3", "--no-color", "--", *paths, cwd=cwd
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_diff(
    raw_diff: str,
    ignore_patterns: list[str] | None = None,
) -> list[FileDiff]:
    """Parse a unified diff string into a list of :class:`FileDiff` objects.

    Parameters
    ----------
    raw_diff:
        Raw unified diff output from ``git diff``.
    ignore_patterns:
        Optional list of glob patterns. Files matching any pattern are excluded.

    Returns
    -------
    list[FileDiff]
        Structured representation of each file's changes.
    """
    if not raw_diff.strip():
        return []

    ignore_patterns = ignore_patterns or []
    file_diffs: list[FileDiff] = []

    # Split on "diff --git" boundaries.  The first element is always empty
    # (or contains text before the first diff header).
    file_sections = re.split(r"^diff --git ", raw_diff, flags=re.MULTILINE)

    for section in file_sections:
        if not section.strip():
            continue

        file_diff = _parse_file_section("diff --git " + section)
        if file_diff is None:
            continue

        # Apply ignore patterns
        if _should_ignore(file_diff.path, ignore_patterns):
            logger.debug("Ignoring file %s (matched ignore pattern)", file_diff.path)
            continue

        file_diffs.append(file_diff)

    return file_diffs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_git(*args: str, cwd: str | None = None) -> str:
    """Execute a git command and return its stdout.

    Parameters
    ----------
    *args:
        Arguments to pass to ``git``.
    cwd:
        Working directory. If ``None``, uses the current directory.

    Raises
    ------
    RuntimeError
        If git is not installed or the command fails.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            cwd=cwd,
        )
    except FileNotFoundError as exc:
        msg = "git is not installed or not on PATH."
        raise RuntimeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = f"git command failed: {exc.stderr.strip()}"
        raise RuntimeError(msg) from exc
    except subprocess.TimeoutExpired as exc:
        msg = "git command timed out after 30 seconds."
        raise RuntimeError(msg) from exc
    return result.stdout


def _parse_file_section(section: str) -> FileDiff | None:
    """Parse a single file section of a unified diff.

    A file section starts with ``diff --git a/... b/...`` and contains
    optional extended headers (``new file``, ``deleted file``, ``rename from``,
    ``rename to``, ``index``, ``similarity index``), followed by ``---`` and
    ``+++`` lines, and then hunk blocks.
    """
    lines = section.split("\n")
    if not lines:
        return None

    # ── Extract file paths from the "diff --git a/... b/..." line ──
    first_line = lines[0]
    match = re.match(r"diff --git a/(.*) b/(.*)", first_line)
    if not match:
        return None

    old_path = match.group(1)
    new_path = match.group(2)

    # ── Scan extended header lines ──
    status = FileStatus.MODIFIED
    is_binary = False
    rename_from: str | None = None
    rename_to: str | None = None
    hunk_start_index = len(lines)  # Default: no hunks found

    i = 1
    while i < len(lines):
        line = lines[i]

        if line.startswith("new file"):
            status = FileStatus.ADDED
        elif line.startswith("deleted file"):
            status = FileStatus.DELETED
        elif line.startswith("rename from "):
            status = FileStatus.RENAMED
            rename_from = line[len("rename from "):]
        elif line.startswith("rename to "):
            rename_to = line[len("rename to "):]
        elif line.startswith("Binary files"):
            is_binary = True
        elif line.startswith("--- "):
            # The `--- ` and `+++ ` lines are part of the diff header.
            # The actual hunk data starts after `+++ `.
            if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                hunk_start_index = i + 2  # skip both --- and +++
            else:
                hunk_start_index = i + 1
            break
        elif _HUNK_HEADER_RE.match(line):
            # Some diffs (e.g. renames with no content change) may jump
            # directly to a hunk header without --- / +++ lines.
            hunk_start_index = i
            break

        i += 1

    # ── Update paths for renames ──
    if rename_from is not None:
        old_path = rename_from
    if rename_to is not None:
        new_path = rename_to

    # ── Handle /dev/null paths ──
    if status == FileStatus.ADDED:
        old_path = "/dev/null"
    elif status == FileStatus.DELETED:
        new_path = "/dev/null"

    # ── Parse hunks ──
    hunks = _parse_hunks(lines[hunk_start_index:]) if not is_binary else []

    return FileDiff(
        old_path=old_path,
        new_path=new_path,
        status=status,
        language=_detect_language(new_path if new_path != "/dev/null" else old_path),
        is_binary=is_binary,
        hunks=hunks,
    )


def _parse_hunks(lines: list[str]) -> list[Hunk]:
    """Parse hunk blocks from the body of a file diff.

    Each hunk starts with ``@@ -a,b +c,d @@`` and is followed by lines
    prefixed with ``+`` (added), ``-`` (removed), or `` `` (context).
    """
    hunks: list[Hunk] = []
    current_hunk: Hunk | None = None
    old_line = 0
    new_line = 0

    for line in lines:
        hunk_match = _HUNK_HEADER_RE.match(line)
        if hunk_match:
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or "1")
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or "1")
            header = (hunk_match.group(5) or "").strip()

            current_hunk = Hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                header=header,
            )
            hunks.append(current_hunk)
            old_line = old_start
            new_line = new_start
            continue

        if current_hunk is None:
            continue

        if line.startswith("+"):
            current_hunk.lines.append(
                HunkLine(
                    change_type=ChangeType.ADDED,
                    content=line[1:],
                    old_line_number=None,
                    new_line_number=new_line,
                )
            )
            new_line += 1
        elif line.startswith("-"):
            current_hunk.lines.append(
                HunkLine(
                    change_type=ChangeType.REMOVED,
                    content=line[1:],
                    old_line_number=old_line,
                    new_line_number=None,
                )
            )
            old_line += 1
        elif line.startswith(" "):
            current_hunk.lines.append(
                HunkLine(
                    change_type=ChangeType.CONTEXT,
                    content=line[1:],
                    old_line_number=old_line,
                    new_line_number=new_line,
                )
            )
            old_line += 1
            new_line += 1
        elif line.startswith("\\"):
            # "\ No newline at end of file" — skip
            continue

    return hunks


def _should_ignore(file_path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any of the ignore glob patterns.

    Supports simple globs (``*.py``), exact filenames (``package-lock.json``),
    and directory prefixes (``vendor/``, ``vendor/*``).  This implementation
    works consistently across Python 3.10+.
    """
    from fnmatch import fnmatch

    for pattern in patterns:
        # Directory prefix pattern — check if any path component matches
        # e.g. "vendor/**" or "vendor/*" should match "vendor/lib/foo.py"
        if "/" in pattern:
            # Normalise: "vendor/**" → "vendor" prefix check
            prefix = pattern.rstrip("/*")
            if file_path == prefix or file_path.startswith(prefix + "/"):
                return True
            # Also try fnmatch on the full path for patterns like "src/*.py"
            if fnmatch(file_path, pattern):
                return True
        else:
            # Simple basename pattern — match against the filename only
            basename = PurePosixPath(file_path).name
            if fnmatch(basename, pattern):
                return True
            # Also try against the full path
            if fnmatch(file_path, pattern):
                return True
    return False
