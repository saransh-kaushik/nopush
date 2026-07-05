"""Comprehensive tests for the PromptBuilder.

Covers:
- Empty diffs
- Single and multi-file prompt construction
- Binary file skipping
- File path, language, and status in prompts
- Review depth modifiers (minimal, standard, thorough)
- Token-based chunking
- Stats in user prompt (additions, deletions, file count)
- Token estimation
"""

from __future__ import annotations

from nopush.git.models import (
    ChangeType,
    FileDiff,
    FileStatus,
    Hunk,
    HunkLine,
)
from nopush.prompts.builder import PromptBuilder

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures / helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_file_diff(
    path: str = "app/utils.py",
    language: str = "python",
    status: FileStatus = FileStatus.MODIFIED,
    is_binary: bool = False,
    additions: int = 2,
    deletions: int = 1,
) -> FileDiff:
    """Create a FileDiff with configurable properties."""
    lines: list[HunkLine] = []

    # Context line
    lines.append(
        HunkLine(
            change_type=ChangeType.CONTEXT,
            content="def process(data):",
            old_line_number=10,
            new_line_number=10,
        )
    )

    # Removed lines
    for i in range(deletions):
        lines.append(
            HunkLine(
                change_type=ChangeType.REMOVED,
                content=f"    old_line_{i}",
                old_line_number=11 + i,
                new_line_number=None,
            )
        )

    # Added lines
    for i in range(additions):
        lines.append(
            HunkLine(
                change_type=ChangeType.ADDED,
                content=f"    new_line_{i}",
                old_line_number=None,
                new_line_number=11 + i,
            )
        )

    return FileDiff(
        old_path=path,
        new_path=path,
        status=status,
        language=language,
        is_binary=is_binary,
        hunks=[
            Hunk(
                old_start=10,
                old_count=1 + deletions,
                new_start=10,
                new_count=1 + additions,
                lines=lines,
            )
        ]
        if not is_binary
        else [],
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Basic prompt building
# ═══════════════════════════════════════════════════════════════════════════


class TestPromptBuilderBasic:
    """Tests for basic prompt construction."""

    def test_empty_diffs(self) -> None:
        """An empty diff list should produce no messages."""
        builder = PromptBuilder()
        result = builder.build([])
        assert result == []

    def test_single_file_produces_one_chunk(self) -> None:
        """A single file diff should produce exactly one message chunk."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff()])
        assert len(chunks) == 1
        messages = chunks[0]
        assert len(messages) == 2  # system + user
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    def test_multiple_files_single_chunk(self) -> None:
        """Multiple small files should fit into a single chunk."""
        builder = PromptBuilder()
        diffs = [
            _make_file_diff("a.py"),
            _make_file_diff("b.py"),
            _make_file_diff("c.py"),
        ]
        chunks = builder.build(diffs)
        assert len(chunks) == 1
        user_content = chunks[0][1].content
        assert "a.py" in user_content
        assert "b.py" in user_content
        assert "c.py" in user_content

    def test_binary_files_skipped(self) -> None:
        """Binary files should be excluded from the prompt."""
        builder = PromptBuilder()
        diffs = [
            _make_file_diff("image.png", is_binary=True),
            _make_file_diff("app.py"),
        ]
        chunks = builder.build(diffs)
        assert len(chunks) == 1
        user_content = chunks[0][1].content
        assert "image.png" not in user_content
        assert "app.py" in user_content

    def test_all_binary_returns_empty(self) -> None:
        """If all files are binary, no prompt should be built."""
        builder = PromptBuilder()
        diffs = [
            _make_file_diff("image.png", is_binary=True),
            _make_file_diff("video.mp4", is_binary=True),
        ]
        result = builder.build(diffs)
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Prompt content
# ═══════════════════════════════════════════════════════════════════════════


class TestPromptContent:
    """Tests for the content of generated prompts."""

    def test_file_path_in_prompt(self) -> None:
        """The user prompt should contain the file path."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff("src/main.py")])
        user_content = chunks[0][1].content
        assert "src/main.py" in user_content

    def test_language_in_prompt(self) -> None:
        """The file's language should appear in the prompt."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff(language="typescript")])
        user_content = chunks[0][1].content
        assert "typescript" in user_content

    def test_status_in_prompt(self) -> None:
        """The file's status should appear in the prompt."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff(status=FileStatus.ADDED)])
        user_content = chunks[0][1].content
        assert "added" in user_content

    def test_diff_content_in_prompt(self) -> None:
        """The actual diff lines should appear in the prompt."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff()])
        user_content = chunks[0][1].content
        assert "+    new_line_0" in user_content
        assert "-    old_line_0" in user_content
        assert " def process(data):" in user_content

    def test_stats_in_prompt(self) -> None:
        """The prompt should include file count and addition/deletion stats."""
        builder = PromptBuilder()
        diffs = [
            _make_file_diff("a.py", additions=3, deletions=1),
            _make_file_diff("b.py", additions=2, deletions=0),
        ]
        chunks = builder.build(diffs)
        user_content = chunks[0][1].content
        assert "Total files in this batch: 2" in user_content
        assert "Total additions: 5" in user_content
        assert "Total deletions: 1" in user_content

    def test_per_file_stats(self) -> None:
        """Each file block should include its own addition/deletion stats."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff(additions=5, deletions=3)])
        user_content = chunks[0][1].content
        assert "Additions: 5" in user_content
        assert "Deletions: 3" in user_content

    def test_unknown_language_fallback(self) -> None:
        """Files with no detected language should show 'unknown'."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff(language="")])
        user_content = chunks[0][1].content
        assert "unknown" in user_content


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Review depth
# ═══════════════════════════════════════════════════════════════════════════


class TestReviewDepth:
    """Tests for review depth modifiers in the system prompt."""

    def test_standard_depth(self) -> None:
        """Standard depth should mention critical issues and suggestions."""
        builder = PromptBuilder(review_depth="standard")
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        assert "critical" in system.lower()
        assert "warnings" in system.lower() or "warning" in system.lower()

    def test_minimal_depth(self) -> None:
        """Minimal depth should focus on critical issues only."""
        builder = PromptBuilder(review_depth="minimal")
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        assert "critical" in system.lower()
        assert "bugs" in system.lower() or "bug" in system.lower()

    def test_thorough_depth(self) -> None:
        """Thorough depth should cover all severity levels."""
        builder = PromptBuilder(review_depth="thorough")
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        assert "comprehensive" in system.lower()

    def test_unknown_depth_falls_back_to_standard(self) -> None:
        """An unknown depth should fall back to 'standard'."""
        builder = PromptBuilder(review_depth="nonexistent")
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        # Should use standard depth — contains "Prioritise"
        assert "prioritise" in system.lower() or "critical" in system.lower()

    def test_depth_in_system_message(self) -> None:
        """The system message should include the Review Depth section header."""
        builder = PromptBuilder(review_depth="thorough")
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        assert "## Review Depth" in system


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Chunking
# ═══════════════════════════════════════════════════════════════════════════


class TestChunking:
    """Tests for token-based chunking of large diffs."""

    def test_small_diffs_single_chunk(self) -> None:
        """Small diffs should fit in one chunk."""
        builder = PromptBuilder(max_input_tokens=120_000)
        diffs = [_make_file_diff(f"file{i}.py") for i in range(5)]
        chunks = builder.build(diffs)
        assert len(chunks) == 1

    def test_large_diffs_multiple_chunks(self) -> None:
        """Diffs exceeding the token budget should be split into chunks."""
        # Set a very small token budget to force chunking
        builder = PromptBuilder(max_input_tokens=200)
        diffs = [
            _make_file_diff("file1.py", additions=20, deletions=10),
            _make_file_diff("file2.py", additions=20, deletions=10),
        ]
        chunks = builder.build(diffs)
        assert len(chunks) >= 2

    def test_each_chunk_has_system_message(self) -> None:
        """Every chunk should include the system message."""
        builder = PromptBuilder(max_input_tokens=200)
        diffs = [
            _make_file_diff("file1.py", additions=20, deletions=10),
            _make_file_diff("file2.py", additions=20, deletions=10),
        ]
        chunks = builder.build(diffs)
        for chunk in chunks:
            assert chunk[0].role == "system"
            assert chunk[1].role == "user"

    def test_single_oversized_file_in_own_chunk(self) -> None:
        """A single file that exceeds the budget should still be included."""
        builder = PromptBuilder(max_input_tokens=50)
        diffs = [_make_file_diff("big.py", additions=100, deletions=50)]
        chunks = builder.build(diffs)
        # Should produce at least 1 chunk with the file
        assert len(chunks) >= 1
        assert "big.py" in chunks[0][1].content


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Token estimation
# ═══════════════════════════════════════════════════════════════════════════


class TestTokenEstimation:
    """Tests for the rough token estimation helper."""

    def test_estimate_tokens(self) -> None:
        """Token estimation should be roughly 1 token per 4 chars."""
        builder = PromptBuilder()
        assert builder._estimate_tokens("") == 0
        assert builder._estimate_tokens("abcd") == 1
        assert builder._estimate_tokens("a" * 100) == 25

    def test_estimate_tokens_short_text(self) -> None:
        """Very short text should round down."""
        builder = PromptBuilder()
        assert builder._estimate_tokens("ab") == 0
        assert builder._estimate_tokens("abc") == 0
        assert builder._estimate_tokens("abcd") == 1


# ═══════════════════════════════════════════════════════════════════════════
# Tests: System prompt content
# ═══════════════════════════════════════════════════════════════════════════


class TestSystemPrompt:
    """Tests for the system prompt template."""

    def test_json_schema_in_system(self) -> None:
        """The system prompt should contain the JSON output schema."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        assert "severity" in system
        assert "file_path" in system
        assert "line_number" in system
        assert "explanation" in system

    def test_severity_levels_defined(self) -> None:
        """All four severity levels should be defined in the system prompt."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        for level in ("critical", "warning", "suggestion", "nitpick"):
            assert level in system

    def test_empty_array_instruction(self) -> None:
        """The system prompt should instruct returning [] for clean code."""
        builder = PromptBuilder()
        chunks = builder.build([_make_file_diff()])
        system = chunks[0][0].content
        assert "[]" in system
