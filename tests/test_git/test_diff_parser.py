"""Tests for the Git diff parser."""

from __future__ import annotations

from nopush.git.diff_parser import parse_diff
from nopush.git.models import ChangeType, FileStatus

# A minimal unified diff for testing
_SAMPLE_DIFF = """\
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


class TestParseDiff:
    """Tests for the parse_diff function."""

    def test_empty_diff(self) -> None:
        """An empty diff should return no file diffs."""
        assert parse_diff("") == []
        assert parse_diff("   \n  ") == []

    def test_modified_file(self) -> None:
        """A standard modification should be parsed correctly."""
        diffs = parse_diff(_SAMPLE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.old_path == "hello.py"
        assert fd.new_path == "hello.py"
        assert fd.status == FileStatus.MODIFIED
        assert fd.language == "python"
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

    def test_deleted_file(self) -> None:
        """A deleted file should have status DELETED."""
        diffs = parse_diff(_DELETED_FILE_DIFF)
        assert len(diffs) == 1
        fd = diffs[0]
        assert fd.status == FileStatus.DELETED
        assert fd.new_path == "/dev/null"

    def test_ignore_patterns(self) -> None:
        """Files matching ignore patterns should be excluded."""
        diffs = parse_diff(_SAMPLE_DIFF, ignore_patterns=["*.py"])
        assert len(diffs) == 0

    def test_multiple_files(self) -> None:
        """Multiple file diffs should all be parsed."""
        combined = _SAMPLE_DIFF + "\n" + _NEW_FILE_DIFF
        diffs = parse_diff(combined)
        assert len(diffs) == 2
