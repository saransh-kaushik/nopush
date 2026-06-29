"""Tests for the ReviewEngine."""

from __future__ import annotations

import json

from nopush.review.engine import ReviewEngine
from nopush.review.models import Severity


class TestResponseParsing:
    """Test the ReviewEngine's JSON response parsing."""

    def test_valid_json_array(self) -> None:
        """A well-formed JSON array should be parsed correctly."""
        raw = json.dumps([
            {
                "severity": "warning",
                "file_path": "app/utils.py",
                "line_number": 11,
                "title": "Missing type check",
                "explanation": "data might not be a string.",
                "suggestion": "str(data).strip()",
            }
        ])
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
        assert comments[0].severity == Severity.WARNING
        assert comments[0].file_path == "app/utils.py"

    def test_json_wrapped_in_markdown_fences(self) -> None:
        """JSON wrapped in ```json ... ``` should still parse."""
        raw = '```json\n[{"severity": "critical", "file_path": "x.py", ' \
              '"line_number": 1, "title": "Bug", "explanation": "bad"}]\n```'
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
        assert comments[0].severity == Severity.CRITICAL

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
        raw = json.dumps({
            "severity": "suggestion",
            "file_path": "main.py",
            "line_number": 5,
            "title": "Improve naming",
            "explanation": "Use a more descriptive name.",
        })
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1

    def test_trailing_comma_handled(self) -> None:
        """Trailing commas in JSON should be cleaned up."""
        raw = '[{"severity": "nitpick", "file_path": "a.py", "line_number": 1, ' \
              '"title": "Style", "explanation": "minor",},]'
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1

    def test_malformed_entry_skipped(self) -> None:
        """A partially malformed entry should be skipped, not fail."""
        raw = json.dumps([
            {"severity": "warning", "file_path": "a.py", "line_number": 1,
             "title": "Good", "explanation": "ok"},
            {"bad": "entry"},  # Missing required fields
        ])
        comments = ReviewEngine._parse_response(raw)
        assert len(comments) == 1
