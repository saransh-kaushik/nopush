"""Comprehensive tests for the Git diff parser.

Covers:
- Empty diffs
- Modified files (single and multi-hunk)
- New files
- Deleted files
- Renamed files
- Binary files
- Ignore patterns (glob matching)
- Multiple files in a single diff
- Line number accuracy
- Edge cases (no newline at EOF, empty hunks)
- git command error handling
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from nopush.git.diff_parser import (
    _detect_language,
    _should_ignore,
    get_diff,
    get_file_diff,
    get_staged_diff,
    parse_diff,
)
from nopush.git.models import ChangeType, FileStatus


# ═══════════════════════════════════════════════════════════════════════════
# Test data — realistic unified diffs
# ═══════════════════════════════════════════════════════════════════════════

_MODIFIED_DIFF = """\
diff --git a/hello.py b/hello.py
index abc1234..def5678 100644
--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
 import os
+import sys
 
 def main():
"""

_NEW_FILE_DIFF = """\
diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def hello():
+    print("hello")
+    return True
"""

_DELETED_FILE_DIFF = """\
diff --git a/old_file.py b/old_file.py
deleted file mode 100644
index abc1234..0000000
--- a/old_file.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def goodbye():
-    pass
"""

_RENAMED_FILE_DIFF = """\
diff --git a/old_name.py b/new_name.py
similarity index 85%
rename from old_name.py
rename to new_name.py
index abc1234..def5678 100644
--- a/old_name.py
+++ b/new_name.py
@@ -1,3 +1,4 @@
 def greet():
-    print("hi")
+    print("hello")
+    return True
"""

_RENAMED_NO_CHANGE_DIFF = """\
diff --git a/utils.py b/helpers.py
similarity index 100%
rename from utils.py
rename to helpers.py
"""

_BINARY_FILE_DIFF = """\
diff --git a/image.png b/image.png
new file mode 100644
index 0000000..abc1234
Binary files /dev/null and b/image.png differ
"""

_MULTI_HUNK_DIFF = """\
diff --git a/server.py b/server.py
index abc1234..def5678 100644
--- a/server.py
+++ b/server.py
@@ -5,7 +5,7 @@ import flask
 
 app = flask.Flask(__name__)
 
-DEBUG = True
+DEBUG = False
 
 
 @app.route("/")
@@ -20,6 +20,8 @@ def index():
 
 @app.route("/api")
 def api():
+    if not request.is_json:
+        return jsonify(error="Bad Request"), 400
     return jsonify(data="ok")
 
 
"""

_NO_NEWLINE_DIFF = """\
diff --git a/config.txt b/config.txt
index abc1234..def5678 100644
--- a/config.txt
+++ b/config.txt
@@ -1,3 +1,3 @@
 setting1=value1
-setting2=value2
+setting2=new_value2
 setting3=value3
\\ No newline at end of file
"""


# ═══════════════════════════════════════════════════════════════════════════
# Tests: parse_diff — Core parsing
# ═══════════════════════════════════════════════════════════════════════════


class TestParseDiffBasic:
    """Tests for basic parsing of different diff types."""

    def test_empty_diff(self) -> None:
        """An empty diff should return no file diffs."""
        assert parse_diff("") == []
        assert parse_diff("   \n  ") == []

    def test_modified_file(self) -> None:
        """A standard modification should be parsed correctly."""
        diffs = parse_diff(_MODIFIED_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.old_path == "hello.py"
        assert fd.new_path == "hello.py"
        assert fd.status == FileStatus.MODIFIED
        assert fd.language == "python"
        assert fd.is_binary is False
        assert len(fd.hunks) == 1

        # Check the added line
        added_lines = [
            line for line in fd.hunks[0].lines if line.change_type == ChangeType.ADDED
        ]
        assert len(added_lines) == 1
        assert added_lines[0].content == "import sys"

    def test_new_file(self) -> None:
        """A new file should have status ADDED and old_path /dev/null."""
        diffs = parse_diff(_NEW_FILE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.status == FileStatus.ADDED
        assert fd.old_path == "/dev/null"
        assert fd.new_path == "new_file.py"
        assert fd.language == "python"
        assert len(fd.hunks) == 1
        assert len(fd.hunks[0].lines) == 3
        assert all(
            line.change_type == ChangeType.ADDED for line in fd.hunks[0].lines
        )

    def test_deleted_file(self) -> None:
        """A deleted file should have status DELETED and new_path /dev/null."""
        diffs = parse_diff(_DELETED_FILE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.status == FileStatus.DELETED
        assert fd.new_path == "/dev/null"
        assert fd.old_path == "old_file.py"
        assert len(fd.hunks) == 1
        assert all(
            line.change_type == ChangeType.REMOVED for line in fd.hunks[0].lines
        )

    def test_renamed_file_with_changes(self) -> None:
        """A renamed file should have status RENAMED and correct old/new paths."""
        diffs = parse_diff(_RENAMED_FILE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.status == FileStatus.RENAMED
        assert fd.old_path == "old_name.py"
        assert fd.new_path == "new_name.py"
        assert fd.language == "python"
        # The diff has actual content changes
        assert len(fd.hunks) == 1
        assert fd.total_additions == 2
        assert fd.total_deletions == 1

    def test_renamed_file_no_changes(self) -> None:
        """A pure rename (100% similarity) with no diff content."""
        diffs = parse_diff(_RENAMED_NO_CHANGE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.status == FileStatus.RENAMED
        assert fd.old_path == "utils.py"
        assert fd.new_path == "helpers.py"
        assert fd.hunks == []  # No content change
        assert fd.total_additions == 0
        assert fd.total_deletions == 0

    def test_binary_file(self) -> None:
        """Binary files should be marked and have no hunks."""
        diffs = parse_diff(_BINARY_FILE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.is_binary is True
        assert fd.status == FileStatus.ADDED
        assert fd.hunks == []


# ═══════════════════════════════════════════════════════════════════════════
# Tests: parse_diff — Multi-hunk and line numbers
# ═══════════════════════════════════════════════════════════════════════════


class TestParseDiffHunks:
    """Tests for multi-hunk diffs and line number accuracy."""

    def test_multi_hunk(self) -> None:
        """A diff with multiple hunks should produce multiple Hunk objects."""
        diffs = parse_diff(_MULTI_HUNK_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert len(fd.hunks) == 2

        # First hunk: line 5-11 (old), replaces DEBUG = True → False
        h1 = fd.hunks[0]
        assert h1.old_start == 5
        assert h1.new_start == 5
        assert len(h1.added_lines) == 1
        assert len(h1.removed_lines) == 1
        assert h1.added_lines[0].content == "DEBUG = False"
        assert h1.removed_lines[0].content == "DEBUG = True"

        # Second hunk: adds two lines
        h2 = fd.hunks[1]
        assert h2.old_start == 20
        assert h2.new_start == 20
        assert len(h2.added_lines) == 2

    def test_line_numbers_modified(self) -> None:
        """Line numbers should be accurate for modified files."""
        diffs = parse_diff(_MODIFIED_DIFF)
        hunk = diffs[0].hunks[0]

        # First line is context: "import os" at old line 1, new line 1
        first_line = hunk.lines[0]
        assert first_line.change_type == ChangeType.CONTEXT
        assert first_line.old_line_number == 1
        assert first_line.new_line_number == 1

        # Second line is added: "import sys" at new line 2, no old line
        added = hunk.lines[1]
        assert added.change_type == ChangeType.ADDED
        assert added.old_line_number is None
        assert added.new_line_number == 2

        # Third line is context: "" at old line 2, new line 3
        context = hunk.lines[2]
        assert context.change_type == ChangeType.CONTEXT
        assert context.old_line_number == 2
        assert context.new_line_number == 3

    def test_line_numbers_new_file(self) -> None:
        """All lines in a new file should start from line 1."""
        diffs = parse_diff(_NEW_FILE_DIFF)
        hunk = diffs[0].hunks[0]
        assert hunk.new_start == 1

        for i, line in enumerate(hunk.lines):
            assert line.new_line_number == i + 1
            assert line.old_line_number is None

    def test_no_newline_at_eof(self) -> None:
        """The parser should skip '\\ No newline at end of file' markers."""
        diffs = parse_diff(_NO_NEWLINE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        # Should not have a line with content starting with "\"
        for hunk in fd.hunks:
            for line in hunk.lines:
                assert not line.content.startswith(" No newline at end of file")

    def test_hunk_header_function_name(self) -> None:
        """The hunk header should capture trailing function context."""
        diffs = parse_diff(_MULTI_HUNK_DIFF)
        h1 = diffs[0].hunks[0]
        assert h1.header == "import flask"


# ═══════════════════════════════════════════════════════════════════════════
# Tests: parse_diff — Filtering and multiple files
# ═══════════════════════════════════════════════════════════════════════════


class TestParseDiffFiltering:
    """Tests for ignore patterns and multi-file diffs."""

    def test_ignore_patterns_glob(self) -> None:
        """Files matching ignore patterns should be excluded."""
        diffs = parse_diff(_MODIFIED_DIFF, ignore_patterns=["*.py"])
        assert len(diffs) == 0

    def test_ignore_patterns_directory(self) -> None:
        """Directory-style ignore patterns should work."""
        diff_with_path = _MODIFIED_DIFF.replace("hello.py", "vendor/lib/hello.py")
        diffs = parse_diff(diff_with_path, ignore_patterns=["vendor/**"])
        assert len(diffs) == 0

    def test_ignore_patterns_no_match(self) -> None:
        """Non-matching patterns should keep all files."""
        diffs = parse_diff(_MODIFIED_DIFF, ignore_patterns=["*.js"])
        assert len(diffs) == 1

    def test_multiple_files(self) -> None:
        """Multiple file diffs should all be parsed."""
        combined = _MODIFIED_DIFF + "\n" + _NEW_FILE_DIFF + "\n" + _DELETED_FILE_DIFF
        diffs = parse_diff(combined)
        assert len(diffs) == 3

        statuses = {fd.status for fd in diffs}
        assert statuses == {FileStatus.MODIFIED, FileStatus.ADDED, FileStatus.DELETED}

    def test_multiple_files_with_ignore(self) -> None:
        """Ignore patterns should apply across all files in a multi-file diff."""
        combined = _MODIFIED_DIFF + "\n" + _NEW_FILE_DIFF
        diffs = parse_diff(combined, ignore_patterns=["new_file.py"])
        assert len(diffs) == 1
        assert diffs[0].path == "hello.py"


# ═══════════════════════════════════════════════════════════════════════════
# Tests: FileDiff properties
# ═══════════════════════════════════════════════════════════════════════════


class TestFileDiffProperties:
    """Tests for the convenience properties on FileDiff."""

    def test_path_uses_new_path(self) -> None:
        """The path property should prefer new_path."""
        diffs = parse_diff(_MODIFIED_DIFF)
        assert diffs[0].path == "hello.py"

    def test_path_uses_old_path_for_deleted(self) -> None:
        """For deleted files, path should fall back to old_path."""
        diffs = parse_diff(_DELETED_FILE_DIFF)
        assert diffs[0].path == "old_file.py"

    def test_total_additions(self) -> None:
        """total_additions should count all added lines across hunks."""
        diffs = parse_diff(_MULTI_HUNK_DIFF)
        fd = diffs[0]
        assert fd.total_additions == 3  # 1 in first hunk + 2 in second

    def test_total_deletions(self) -> None:
        """total_deletions should count all removed lines across hunks."""
        diffs = parse_diff(_MULTI_HUNK_DIFF)
        fd = diffs[0]
        assert fd.total_deletions == 1  # 1 in first hunk


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Language detection
# ═══════════════════════════════════════════════════════════════════════════


class TestLanguageDetection:
    """Tests for file extension → language mapping."""

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("app/main.py", "python"),
            ("src/index.ts", "typescript"),
            ("lib/utils.js", "javascript"),
            ("Makefile", ""),
            ("README.md", "markdown"),
            ("styles.css", "css"),
            ("Dockerfile.prod", ""),  # no extension match
            ("server.go", "go"),
            ("main.rs", "rust"),
            ("app.swift", "swift"),
            ("query.sql", "sql"),
            ("schema.graphql", "graphql"),
        ],
    )
    def test_detect_language(self, path: str, expected: str) -> None:
        assert _detect_language(path) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Ignore helper
# ═══════════════════════════════════════════════════════════════════════════


class TestShouldIgnore:
    """Tests for the _should_ignore helper."""

    def test_matches_extension(self) -> None:
        assert _should_ignore("hello.py", ["*.py"]) is True

    def test_no_match(self) -> None:
        assert _should_ignore("hello.py", ["*.js"]) is False

    def test_empty_patterns(self) -> None:
        assert _should_ignore("hello.py", []) is False

    def test_directory_pattern(self) -> None:
        assert _should_ignore("vendor/lib/foo.py", ["vendor/**"]) is True

    def test_exact_filename(self) -> None:
        assert _should_ignore("package-lock.json", ["package-lock.json"]) is True


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Git command wrappers
# ═══════════════════════════════════════════════════════════════════════════


class TestGitCommands:
    """Tests for git subprocess wrappers (mocked)."""

    def test_get_staged_diff_calls_git(self) -> None:
        """get_staged_diff should invoke git diff --staged."""
        with patch("nopush.git.diff_parser.subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            get_staged_diff()
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert "--staged" in args

    def test_get_diff_with_two_refs(self) -> None:
        """get_diff with two refs should include both."""
        with patch("nopush.git.diff_parser.subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            get_diff("main", "feature")
            args = mock_run.call_args[0][0]
            assert "main" in args
            assert "feature" in args

    def test_get_file_diff_passes_paths(self) -> None:
        """get_file_diff should pass file paths after --."""
        with patch("nopush.git.diff_parser.subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            get_file_diff(["foo.py", "bar.py"])
            args = mock_run.call_args[0][0]
            assert "--" in args
            assert "foo.py" in args
            assert "bar.py" in args

    def test_git_not_installed_raises(self) -> None:
        """Missing git should raise RuntimeError."""
        with patch(
            "nopush.git.diff_parser.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(RuntimeError, match="not installed"):
                get_staged_diff()

    def test_git_command_failure_raises(self) -> None:
        """A failing git command should raise RuntimeError."""
        import subprocess

        with patch(
            "nopush.git.diff_parser.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                128, "git", stderr="fatal: not a git repo"
            ),
        ):
            with pytest.raises(RuntimeError, match="git command failed"):
                get_staged_diff()

    def test_git_timeout_raises(self) -> None:
        """A timed-out git command should raise RuntimeError."""
        import subprocess

        with patch(
            "nopush.git.diff_parser.subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 30),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                get_staged_diff()

    def test_cwd_is_passed_through(self) -> None:
        """The cwd parameter should be forwarded to subprocess.run."""
        with patch("nopush.git.diff_parser.subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            get_staged_diff(cwd="/some/repo")
            kwargs = mock_run.call_args[1]
            assert kwargs["cwd"] == "/some/repo"
