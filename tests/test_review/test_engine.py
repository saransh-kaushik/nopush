"""Comprehensive tests for the ReviewEngine.

Covers:
- JSON response parsing (valid, malformed, edge cases)
- Full review orchestration with mocked LLM provider
- Empty diff handling
- File path validation (hallucinated references discarded)
- Multi-chunk review aggregation
- Engine construction and configuration
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from nopush.config.schema import NoPushConfig
from nopush.git.models import (
    ChangeType,
    FileDiff,
    FileStatus,
    Hunk,
    HunkLine,
)
from nopush.providers.base import LLMProvider
from nopush.review.engine import ReviewEngine
from nopush.review.models import ReviewComment, ReviewResult, Severity

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_config(**kwargs: object) -> NoPushConfig:
    """Create a NoPushConfig with sensible defaults for testing."""
    defaults = {
        "provider": "openai",
        "api_key": "sk-test-key-123",
        "model": "gpt-4.1",
        "timeout": 30,
    }
    defaults.update(kwargs)
    return NoPushConfig(**defaults)  # type: ignore[arg-type]


def _make_file_diff(
    path: str = "app/utils.py",
    language: str = "python",
    additions: int = 2,
    deletions: int = 1,
) -> FileDiff:
    """Create a simple FileDiff for testing."""
    lines: list[HunkLine] = [
        HunkLine(
            change_type=ChangeType.CONTEXT,
            content="def process(data):",
            old_line_number=10,
            new_line_number=10,
        ),
    ]
    for i in range(deletions):
        lines.append(
            HunkLine(
                change_type=ChangeType.REMOVED,
                content=f"    old_line_{i}",
                old_line_number=11 + i,
                new_line_number=None,
            )
        )
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
        status=FileStatus.MODIFIED,
        language=language,
        hunks=[
            Hunk(
                old_start=10,
                old_count=1 + deletions,
                new_start=10,
                new_count=1 + additions,
                lines=lines,
            )
        ],
    )


def _make_mock_provider(response: str) -> LLMProvider:
    """Create a mock LLM provider that returns a fixed response."""
    mock = MagicMock(spec=LLMProvider)
    mock.complete.return_value = response
    return mock


def _valid_review_json(
    file_path: str = "app/utils.py",
    severity: str = "warning",
    line_number: int = 11,
) -> str:
    """Generate a valid JSON review response."""
    return json.dumps(
        [
            {
                "severity": severity,
                "file_path": file_path,
                "line_number": line_number,
                "title": "Test issue",
                "explanation": "This is a test explanation.",
                "suggestion": "    fixed_code()",
            }
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Response Parsing
# ═══════════════════════════════════════════════════════════════════════════


class TestResponseParsing:
    """Test the ReviewEngine's JSON response parsing."""

    def test_valid_json_array(self) -> None:
        """A well-formed JSON array should be parsed correctly."""
        raw = json.dumps(
            [
                {
                    "severity": "warning",
                    "file_path": "app/utils.py",
                    "line_number": 11,
                    "title": "Missing type check",
                    "explanation": "data might not be a string.",
                    "suggestion": "str(data).strip()",
                }
            ]
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
        assert comments[0].severity == Severity.WARNING
        assert comments[0].file_path == "app/utils.py"

    def test_json_wrapped_in_markdown_fences(self) -> None:
        """JSON wrapped in ```json ... ``` should still parse."""
        raw = (
            '```json\n[{"severity": "critical", "file_path": "x.py", '
            '"line_number": 1, "title": "Bug", "explanation": "bad"}]\n```'
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
        assert comments[0].severity == Severity.CRITICAL

    def test_plain_markdown_fences(self) -> None:
        """JSON wrapped in ``` ... ``` (without json) should still parse."""
        raw = (
            '```\n[{"severity": "suggestion", "file_path": "a.py", '
            '"line_number": 5, "title": "Style", "explanation": "improve"}]\n```'
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
        assert comments[0].severity == Severity.SUGGESTION

    def test_empty_array(self) -> None:
        """An empty JSON array should produce no comments."""
        comments = ReviewEngine._parse_response("[]")
        assert comments == []

    def test_malformed_json_returns_empty(self) -> None:
        """Completely invalid JSON should return an empty list, not crash."""
        comments = ReviewEngine._parse_response("this is not json at all")
        assert comments == []

    def test_single_object_normalized_to_list(self) -> None:
        """A single JSON object (not in an array) should be handled."""
        raw = json.dumps(
            {
                "severity": "suggestion",
                "file_path": "main.py",
                "line_number": 5,
                "title": "Improve naming",
                "explanation": "Use a more descriptive name.",
            }
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1

    def test_trailing_comma_handled(self) -> None:
        """Trailing commas in JSON should be cleaned up."""
        raw = (
            '[{"severity": "nitpick", "file_path": "a.py", "line_number": 1, '
            '"title": "Style", "explanation": "minor",},]'
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1

    def test_malformed_entry_skipped(self) -> None:
        """A partially malformed entry should be skipped, not fail."""
        raw = json.dumps(
            [
                {
                    "severity": "warning",
                    "file_path": "a.py",
                    "line_number": 1,
                    "title": "Good",
                    "explanation": "ok",
                },
                {"bad": "entry"},  # Missing required fields
            ]
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1

    def test_null_suggestion_accepted(self) -> None:
        """A comment with suggestion=null should parse correctly."""
        raw = json.dumps(
            [
                {
                    "severity": "warning",
                    "file_path": "a.py",
                    "line_number": 1,
                    "title": "Issue",
                    "explanation": "Problem.",
                    "suggestion": None,
                }
            ]
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
        assert comments[0].suggestion is None

    def test_embedded_json_in_text(self) -> None:
        """JSON array embedded within surrounding text should be extracted."""
        raw = (
            'Here are my findings:\n[{"severity": "critical", '
            '"file_path": "x.py", "line_number": 1, "title": "Bug", '
            '"explanation": "bad"}]\nHope this helps!'
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1

    def test_multiple_comments_parsed(self) -> None:
        """Multiple valid comments should all be parsed."""
        raw = json.dumps(
            [
                {
                    "severity": "critical",
                    "file_path": "a.py",
                    "line_number": 1,
                    "title": "Bug 1",
                    "explanation": "first",
                },
                {
                    "severity": "warning",
                    "file_path": "b.py",
                    "line_number": 2,
                    "title": "Bug 2",
                    "explanation": "second",
                },
                {
                    "severity": "suggestion",
                    "file_path": "c.py",
                    "line_number": 3,
                    "title": "Improve",
                    "explanation": "third",
                },
            ]
        )
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 3
        assert comments[0].severity == Severity.CRITICAL
        assert comments[1].severity == Severity.WARNING
        assert comments[2].severity == Severity.SUGGESTION

    def test_non_list_non_dict_returns_empty(self) -> None:
        """A JSON value that is neither list nor dict should return empty."""
        comments = ReviewEngine._parse_response('"just a string"')
        assert comments == []

    def test_numeric_json_returns_empty(self) -> None:
        """A numeric JSON value should return empty list."""
        comments = ReviewEngine._parse_response("42")
        assert comments == []


# ═══════════════════════════════════════════════════════════════════════════
# Tests: JSON Cleaning
# ═══════════════════════════════════════════════════════════════════════════


class TestJsonCleaning:
    """Test the _clean_json helper."""

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        assert ReviewEngine._clean_json("  []  ") == "[]"

    def test_removes_json_fence(self) -> None:
        """```json ... ``` wrappers should be removed."""
        assert ReviewEngine._clean_json("```json\n[]\n```") == "[]"

    def test_removes_plain_fence(self) -> None:
        """``` ... ``` wrappers should be removed."""
        assert ReviewEngine._clean_json("```\n[]\n```") == "[]"

    def test_removes_trailing_commas_in_array(self) -> None:
        """Trailing commas before ] should be removed."""
        cleaned = ReviewEngine._clean_json('[{"a": 1},]')
        assert cleaned == '[{"a": 1}]'

    def test_removes_trailing_commas_in_object(self) -> None:
        """Trailing commas before } should be removed."""
        cleaned = ReviewEngine._clean_json('{"a": 1,}')
        assert cleaned == '{"a": 1}'


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Review Orchestration
# ═══════════════════════════════════════════════════════════════════════════


class TestReviewOrchestration:
    """Test the full ReviewEngine.review() flow with mocked providers."""

    def test_empty_diffs_returns_empty_result(self) -> None:
        """An empty diff list should return a result with zero files and no comments."""
        config = _make_config()
        provider = _make_mock_provider("[]")
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([])

        assert isinstance(result, ReviewResult)
        assert result.files_reviewed == 0
        assert result.total_issues == 0
        assert result.model == "gpt-4.1"
        assert result.provider == "openai"
        # Provider should not be called
        provider.complete.assert_not_called()

    def test_successful_review_single_file(self) -> None:
        """A single file review should return parsed comments."""
        config = _make_config()
        response = _valid_review_json()
        provider = _make_mock_provider(response)
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([_make_file_diff()])

        assert result.files_reviewed == 1
        assert result.total_issues == 1
        assert result.comments[0].severity == Severity.WARNING
        assert result.comments[0].file_path == "app/utils.py"
        provider.complete.assert_called_once()

    def test_successful_review_multiple_files(self) -> None:
        """A review with multiple files should include all valid comments."""
        config = _make_config()
        response = json.dumps(
            [
                {
                    "severity": "warning",
                    "file_path": "a.py",
                    "line_number": 11,
                    "title": "Issue 1",
                    "explanation": "Problem in a.py",
                },
                {
                    "severity": "suggestion",
                    "file_path": "b.py",
                    "line_number": 11,
                    "title": "Issue 2",
                    "explanation": "Problem in b.py",
                },
            ]
        )
        provider = _make_mock_provider(response)
        engine = ReviewEngine(provider=provider, config=config)

        diffs = [_make_file_diff("a.py"), _make_file_diff("b.py")]
        result = engine.review(diffs)

        assert result.files_reviewed == 2
        assert result.total_issues == 2

    def test_hallucinated_file_path_discarded(self) -> None:
        """Comments referencing non-existent file paths should be discarded."""
        config = _make_config()
        response = json.dumps(
            [
                {
                    "severity": "warning",
                    "file_path": "app/utils.py",
                    "line_number": 11,
                    "title": "Real issue",
                    "explanation": "Valid.",
                },
                {
                    "severity": "critical",
                    "file_path": "nonexistent.py",
                    "line_number": 1,
                    "title": "Fake issue",
                    "explanation": "Hallucinated.",
                },
            ]
        )
        provider = _make_mock_provider(response)
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([_make_file_diff("app/utils.py")])

        assert result.total_issues == 1
        assert result.comments[0].file_path == "app/utils.py"

    def test_all_hallucinated_paths_empty_result(self) -> None:
        """If all comments reference non-existent paths, result should be empty."""
        config = _make_config()
        response = json.dumps(
            [
                {
                    "severity": "critical",
                    "file_path": "fake.py",
                    "line_number": 1,
                    "title": "Fake",
                    "explanation": "Not real.",
                },
            ]
        )
        provider = _make_mock_provider(response)
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([_make_file_diff("real.py")])

        assert result.total_issues == 0
        assert result.files_reviewed == 1

    def test_clean_code_returns_empty_comments(self) -> None:
        """If the LLM returns an empty array, no comments should be produced."""
        config = _make_config()
        provider = _make_mock_provider("[]")
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([_make_file_diff()])

        assert result.total_issues == 0
        assert result.files_reviewed == 1

    def test_malformed_llm_response_returns_empty(self) -> None:
        """A completely invalid LLM response should produce no comments."""
        config = _make_config()
        provider = _make_mock_provider("I can't review this code sorry")
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([_make_file_diff()])

        assert result.total_issues == 0
        assert result.files_reviewed == 1

    def test_config_metadata_in_result(self) -> None:
        """The result should contain the provider and model from config."""
        config = _make_config(provider="gemini", model="gemini-2.5-pro")
        provider = _make_mock_provider("[]")
        engine = ReviewEngine(provider=provider, config=config)

        result = engine.review([_make_file_diff()])

        assert result.provider == "gemini"
        assert result.model == "gemini-2.5-pro"


# ═══════════════════════════════════════════════════════════════════════════
# Tests: ReviewResult Model
# ═══════════════════════════════════════════════════════════════════════════


class TestReviewResult:
    """Test the ReviewResult model properties."""

    def test_total_issues(self) -> None:
        """total_issues should return the count of comments."""
        result = ReviewResult(
            comments=[
                ReviewComment(
                    severity=Severity.WARNING,
                    file_path="a.py",
                    line_number=1,
                    title="Issue",
                    explanation="Problem.",
                ),
                ReviewComment(
                    severity=Severity.CRITICAL,
                    file_path="b.py",
                    line_number=2,
                    title="Bug",
                    explanation="Bad.",
                ),
            ],
            files_reviewed=2,
            model="gpt-4.1",
            provider="openai",
        )
        assert result.total_issues == 2

    def test_count_by_severity(self) -> None:
        """count_by_severity should correctly aggregate."""
        result = ReviewResult(
            comments=[
                ReviewComment(
                    severity=Severity.CRITICAL,
                    file_path="a.py",
                    line_number=1,
                    title="A",
                    explanation="X",
                ),
                ReviewComment(
                    severity=Severity.CRITICAL,
                    file_path="b.py",
                    line_number=2,
                    title="B",
                    explanation="Y",
                ),
                ReviewComment(
                    severity=Severity.WARNING,
                    file_path="c.py",
                    line_number=3,
                    title="C",
                    explanation="Z",
                ),
            ],
            files_reviewed=3,
        )
        counts = result.count_by_severity()
        assert counts[Severity.CRITICAL] == 2
        assert counts[Severity.WARNING] == 1
        assert counts[Severity.SUGGESTION] == 0
        assert counts[Severity.NITPICK] == 0

    def test_empty_result(self) -> None:
        """An empty result should have zero totals."""
        result = ReviewResult()
        assert result.total_issues == 0
        assert result.files_reviewed == 0
        assert all(v == 0 for v in result.count_by_severity().values())
