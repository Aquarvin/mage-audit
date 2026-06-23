"""Tests for Finding parsing and validation."""

import pytest

from src.core.agent.types import Category, Finding, Severity


class TestFindingCreation:
    """Test normal Finding creation."""

    def test_valid_finding(self):
        f = Finding(
            severity=Severity.CRITICAL,
            line=45,
            category=Category.SECURITY,
            issue="SQL injection",
            suggestion="Use prepared statements",
        )
        assert f.severity == Severity.CRITICAL
        assert f.line == 45
        assert f.category == Category.SECURITY

    def test_finding_without_line(self):
        f = Finding(
            severity=Severity.WARNING,
            category=Category.STYLE,
            issue="Missing type hint",
            suggestion="Add type hint",
        )
        assert f.line is None

    def test_invalid_severity_raises(self):
        with pytest.raises(Exception):
            Finding(
                severity="catastrophic",
                category=Category.BUG,
                issue="test",
                suggestion="test",
            )


class TestFromLLMOutput:
    """Test Finding.from_llm_output() — handles LLM mistakes."""

    def test_normal_input(self):
        data = {
            "severity": "critical",
            "line": 10,
            "category": "security",
            "issue": "SQL injection",
            "suggestion": "Fix it",
        }
        f = Finding.from_llm_output(data)
        assert f.severity == Severity.CRITICAL
        assert f.category == Category.SECURITY
        assert f.line == 10

    def test_severity_contains_category_value(self):
        """LLM put 'architecture' in severity field."""
        data = {
            "severity": "architecture",
            "category": "style",
            "issue": "Bad pattern",
            "suggestion": "Refactor",
        }
        f = Finding.from_llm_output(data)
        assert f.severity == Severity.WARNING  # fallback
        assert f.category == Category.STYLE

    def test_category_contains_severity_value(self):
        """LLM put 'warning' in category field."""
        data = {
            "severity": "error",
            "category": "warning",
            "issue": "Something wrong",
            "suggestion": "Fix",
        }
        f = Finding.from_llm_output(data)
        assert f.severity == Severity.ERROR
        assert f.category == Category.ARCHITECTURE  # fallback

    def test_both_fields_swapped(self):
        """LLM swapped severity and category completely."""
        data = {
            "severity": "bug",
            "category": "critical",
            "issue": "Found a bug",
            "suggestion": "Fix the bug",
        }
        f = Finding.from_llm_output(data)
        assert f.severity == Severity.WARNING  # "bug" is not a severity
        assert f.category == Category.ARCHITECTURE  # "critical" is not a category

    def test_missing_fields_use_defaults(self):
        data = {
            "issue": "Something",
            "suggestion": "Fix",
        }
        f = Finding.from_llm_output(data)
        assert f.severity == Severity.WARNING
        assert f.category == Category.ARCHITECTURE
        assert f.line is None

    def test_unknown_severity_falls_back(self):
        data = {
            "severity": "catastrophic",
            "category": "security",
            "issue": "test",
            "suggestion": "test",
        }
        f = Finding.from_llm_output(data)
        assert f.severity == Severity.WARNING

    def test_unknown_category_falls_back(self):
        data = {
            "severity": "error",
            "category": "maintainability",
            "issue": "test",
            "suggestion": "test",
        }
        f = Finding.from_llm_output(data)
        assert f.category == Category.ARCHITECTURE


class TestReviewResult:
    """Test ReviewResult counters."""

    def test_severity_counts(self):
        from src.core.agent.types import ReviewResult

        result = ReviewResult(
            file_path="test.php",
            findings=[
                Finding(
                    severity=Severity.CRITICAL,
                    category=Category.SECURITY,
                    issue="a",
                    suggestion="b",
                ),
                Finding(
                    severity=Severity.CRITICAL,
                    category=Category.BUG,
                    issue="c",
                    suggestion="d",
                ),
                Finding(
                    severity=Severity.ERROR,
                    category=Category.ARCHITECTURE,
                    issue="e",
                    suggestion="f",
                ),
                Finding(
                    severity=Severity.WARNING,
                    category=Category.STYLE,
                    issue="g",
                    suggestion="h",
                ),
            ],
            model="test-model",
            input_tokens=100,
            output_tokens=200,
        )
        assert result.critical_count == 2
        assert result.error_count == 1
        assert result.warning_count == 1

    def test_empty_findings(self):
        from src.core.agent.types import ReviewResult

        result = ReviewResult(
            file_path="test.php",
            findings=[],
            model="test",
            input_tokens=0,
            output_tokens=0,
        )
        assert result.critical_count == 0
        assert result.error_count == 0
