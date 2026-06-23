"""Tests for JSON parsing of LLM output."""

from src.core.agent.review_service import ReviewService


class TestFixJsonBackslashes:
    """Test _fix_json_backslashes — handles PHP namespaces in JSON."""

    def test_valid_json_unchanged(self):
        text = '{"key": "value", "number": 42}'
        result = ReviewService._fix_json_backslashes(text)
        assert result == text

    def test_valid_escapes_unchanged(self):
        text = r'{"text": "line1\nline2\ttab"}'
        result = ReviewService._fix_json_backslashes(text)
        assert result == text

    def test_php_namespace_single_backslash(self):
        text = r'{"class": "Magento\Sales\Api\OrderRepository"}'
        result = ReviewService._fix_json_backslashes(text)
        assert "Magento\\\\Sales\\\\Api\\\\OrderRepository" in result

    def test_php_namespace_mixed_escaping(self):
        """LLM sometimes escapes some backslashes but not others."""
        text = r'{"class": "Magento\\Sales\Api\OrderRepository"}'
        result = ReviewService._fix_json_backslashes(text)
        # After fix, all backslashes should be properly escaped
        import json

        parsed = json.loads(result)
        assert "Magento" in parsed["class"]
        assert "OrderRepository" in parsed["class"]

    def test_unicode_escape_preserved(self):
        text = r'{"text": "\u0041"}'  # \u0041 = "A"
        result = ReviewService._fix_json_backslashes(text)
        import json

        parsed = json.loads(result)
        assert parsed["text"] == "A"

    def test_already_escaped_not_double_escaped(self):
        text = r'{"path": "C:\\Users\\test"}'
        result = ReviewService._fix_json_backslashes(text)
        import json

        parsed = json.loads(result)
        assert parsed["path"] == "C:\\Users\\test"


class TestParseFindings:
    """Test _parse_findings — full pipeline from raw LLM text to Finding objects."""

    def _make_service(self):
        """Create ReviewService with a dummy LLM (won't be called)."""

        # We only test _parse_findings, which doesn't use self._llm
        class DummyLLM:
            model = "test"

        service = ReviewService.__new__(ReviewService)
        service._llm = DummyLLM()
        return service

    def test_valid_json_array(self):
        service = self._make_service()
        raw = '[{"severity": "critical", "line": 10, "category": "security", "issue": "SQL injection", "suggestion": "Fix it"}]'
        findings = service._parse_findings(raw)
        assert len(findings) == 1
        assert findings[0].severity.value == "critical"

    def test_json_with_markdown_fences(self):
        service = self._make_service()
        raw = '```json\n[{"severity": "warning", "category": "style", "issue": "test", "suggestion": "fix"}]\n```'
        findings = service._parse_findings(raw)
        assert len(findings) == 1

    def test_json_with_fences_no_language(self):
        service = self._make_service()
        raw = '```\n[{"severity": "error", "category": "bug", "issue": "test", "suggestion": "fix"}]\n```'
        findings = service._parse_findings(raw)
        assert len(findings) == 1

    def test_invalid_json_returns_empty(self):
        service = self._make_service()
        raw = "This is not JSON at all"
        findings = service._parse_findings(raw)
        assert len(findings) == 0

    def test_json_object_instead_of_array(self):
        service = self._make_service()
        raw = '{"severity": "critical", "issue": "test"}'
        findings = service._parse_findings(raw)
        assert len(findings) == 0  # expects array, not object

    def test_empty_array(self):
        service = self._make_service()
        raw = "[]"
        findings = service._parse_findings(raw)
        assert len(findings) == 0

    def test_partially_valid_items(self):
        """Some items valid, some not — valid ones should survive."""
        service = self._make_service()
        raw = """[
            {"severity": "critical", "category": "security", "issue": "good one", "suggestion": "fix"},
            {"severity": "critical", "category": "security", "issue": "also good", "suggestion": "fix too"}
        ]"""
        findings = service._parse_findings(raw)
        assert len(findings) == 2

    def test_php_namespaces_in_suggestions(self):
        service = self._make_service()
        raw = r'[{"severity": "error", "category": "architecture", "issue": "Wrong class", "suggestion": "Use \Magento\Sales\Api\OrderRepositoryInterface"}]'
        findings = service._parse_findings(raw)
        assert len(findings) == 1
        assert "OrderRepositoryInterface" in findings[0].suggestion
