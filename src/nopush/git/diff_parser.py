"""Parse unified diff output from ``git diff``."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

from nopush.git.models import ChangeType, FileDiff, FileStatus, Hunk, HunkLine

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
}

# Regex for the ``@@ -old_start,old_count +new_start,new_count @@`` header
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)?$"
)


def _detect_language(file_path: str) -> str:
    """Infer programming language from the file extension."""
    suffix = PurePosixPath(file_path).suffix.lower()
    return _EXTENSION_MAP.get(suffix, "")


# ---------------------------------------------------------------------------
# Git interaction
# ---------------------------------------------------------------------------


def get_staged_diff() -> str:
    """Return the unified diff for staged changes.

    Raises
    ------
    RuntimeError
        If ``git`` is not available or the current directory is not a repo.
    """
    return _run_git("diff", "--staged", "--unified=3", "--no-color")


def get_diff(ref_a: str = "HEAD", ref_b: str | None = None) -> str:
    """Return the unified diff between two refs (or a ref and the working tree)."""
    args = ["diff", ref_a, "--unified=3", "--no-color"]
    if ref_b is not None:
        args.insert(2, ref_b)
    return _run_git(*args)


def get_file_diff(paths: list[str]) -> str:
    """Return the diff for specific file paths."""
    return _run_git("diff", "--staged", "--unified=3", "--no-color", "--", *paths)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_diff(raw_diff: str, ignore_patterns: list[str] | None = None) -> list[FileDiff]:
    """Parse a unified diff string into a list of :class:`FileDiff` objects.

    Parameters
    ----------
    raw_diff:
        Raw unified diff output from ``git diff``.
    ignore_patterns:
        Optional list of glob patterns. Files matching any pattern are excluded.
    """
    if not raw_diff.strip():
        return []

    ignore_patterns = ignore_patterns or []
    file_diffs: list[FileDiff] = []

    # Split on "diff --git" boundaries
    file_sections = re.split(r"^diff --git ", raw_diff, flags=re.MULTILINE)

    for section in file_sections:
        if not section.strip():
            continue

        file_diff = _parse_file_section("diff --git " + section)
        if file_diff is None:
            continue

        # Apply ignore patterns
        if _should_ignore(file_diff.path, ignore_patterns):
            continue

        file_diffs.append(file_diff)

    return file_diffs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_git(*args: str) -> str:
    """Execute a git command and return its stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        msg = "git is not installed or not on PATH."
        raise RuntimeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = f"git command failed: {exc.stderr.strip()}"
        raise RuntimeError(msg) from exc
    return result.stdout


def _parse_file_section(section: str) -> FileDiff | None:
    """Parse a single file section of a unified diff."""
    lines = section.split("\n")
    if not lines:
        return None

    # Extract file paths from the "diff --git a/... b/..." line
    first_line = lines[0]
    match = re.match(r"diff --git a/(.*) b/(.*)", first_line)
    if not match:
        return None

    old_path = match.group(1)
    new_path = match.group(2)

    # Determine file status
    status = FileStatus.MODIFIED
    is_binary = False
    header_end = 0

    for i, line in enumerate(lines[1:], start=1):
        if line.startswith("new file"):
            status = FileStatus.ADDED
        elif line.startswith("deleted file"):
            status = FileStatus.DELETED
        elif line.startswith("rename from"):
            status = FileStatus.RENAMED
        elif line.startswith("Binary files"):
            is_binary = True
        elif line.startswith("--- "):
            header_end = i
            break
        elif line.startswith("@@"):
            header_end = i
            break

    # Handle /dev/null paths
    if status == FileStatus.ADDED:
        old_path = "/dev/null"
    elif status == FileStatus.DELETED:
        new_path = "/dev/null"

    # Parse hunks
    hunks = _parse_hunks(lines[header_end:]) if not is_binary else []

    return FileDiff(
        old_path=old_path,
        new_path=new_path,
        status=status,
        language=_detect_language(new_path if new_path != "/dev/null" else old_path),
        is_binary=is_binary,
        hunks=hunks,
    )


def _parse_hunks(lines: list[str]) -> list[Hunk]:
    """Parse hunk blocks from the body of a file diff."""
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
    """Check if a file path matches any of the ignore glob patterns."""
    path = PurePosixPath(file_path)
    return any(path.match(pattern) for pattern in patterns)
