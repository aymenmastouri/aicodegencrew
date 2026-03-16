"""Tests for Review-LLM-Call and JSON repair functionality."""

import json

import pytest


# =============================================================================
# AnalysisReviewer
# =============================================================================


class TestAnalysisReviewerParsing:
    """Test AnalysisReviewer JSON extraction."""

    def test_extract_clean_json(self):
        from aicodegencrew.pipelines.analysis.reviewer import AnalysisReviewer

        data = AnalysisReviewer._extract_json('{"quality_score": 85}')
        assert data == {"quality_score": 85}

    def test_extract_json_with_trailing_text(self):
        from aicodegencrew.pipelines.analysis.reviewer import AnalysisReviewer

        data = AnalysisReviewer._extract_json(
            '{"quality_score": 70}\nHere is my analysis of the sections...'
        )
        assert data is not None
        assert data["quality_score"] == 70

    def test_extract_json_with_markdown_fences(self):
        from aicodegencrew.pipelines.analysis.reviewer import AnalysisReviewer

        data = AnalysisReviewer._extract_json('```json\n{"score": 90}\n```')
        assert data == {"score": 90}

    def test_extract_json_buried_in_text(self):
        from aicodegencrew.pipelines.analysis.reviewer import AnalysisReviewer

        data = AnalysisReviewer._extract_json(
            'Here is my review:\n{"quality_score": 60, "sections_to_redo": {}}\nEnd.'
        )
        assert data is not None
        assert data["quality_score"] == 60

    def test_extract_json_returns_none_for_garbage(self):
        from aicodegencrew.pipelines.analysis.reviewer import AnalysisReviewer

        assert AnalysisReviewer._extract_json("no json here at all") is None

    def test_review_result_defaults(self):
        from aicodegencrew.pipelines.analysis.reviewer import ReviewResult

        r = ReviewResult(quality_score=80, sections_to_redo={}, gaps=[], contradictions=[])
        assert r.quality_score == 80
        assert r.sections_to_redo == {}


# =============================================================================
# DocumentReviewer
# =============================================================================


class TestDocumentReviewerParsing:
    """Test DocumentReviewer JSON extraction."""

    def test_extract_clean_json(self):
        from aicodegencrew.pipelines.document.reviewer import DocumentReviewer

        data = DocumentReviewer._extract_json('{"quality_score": 85, "rewrite_needed": false}')
        assert data["quality_score"] == 85
        assert data["rewrite_needed"] is False

    def test_extract_json_trailing_explanation(self):
        from aicodegencrew.pipelines.document.reviewer import DocumentReviewer

        data = DocumentReviewer._extract_json(
            '{"quality_score": 75, "rewrite_needed": false, "missing_topics": []}\n\n'
            "The chapter covers the main topics well but could use more detail."
        )
        assert data is not None
        assert data["quality_score"] == 75

    def test_extract_json_markdown_wrapped(self):
        from aicodegencrew.pipelines.document.reviewer import DocumentReviewer

        data = DocumentReviewer._extract_json(
            '```json\n{"quality_score": 90, "rewrite_needed": false}\n```'
        )
        assert data is not None
        assert data["quality_score"] == 90

    def test_review_result_feedback_property(self):
        from aicodegencrew.pipelines.document.reviewer import ReviewResult

        r = ReviewResult(
            quality_score=50,
            rewrite_needed=True,
            missing_topics=["deployment topology"],
            unsupported_claims=["claims Spring Boot but no evidence"],
            contradictions=[],
            weak_sections=["section 3 is vague"],
        )
        feedback = r.feedback
        assert len(feedback) == 3
        assert "Missing topic: deployment topology" in feedback
        assert "Unsupported claim: claims Spring Boot but no evidence" in feedback
        assert "Weak section: section 3 is vague" in feedback


# =============================================================================
# JSON Repair (Analysis Pipeline)
# =============================================================================


class TestJsonRepair:
    """Test _extract_and_repair_json in AnalysisPipeline."""

    @pytest.fixture
    def pipeline(self):
        from aicodegencrew.pipelines.analysis.pipeline import AnalysisPipeline

        p = AnalysisPipeline.__new__(AnalysisPipeline)
        return p

    def test_valid_json_passthrough(self, pipeline):
        result = pipeline._extract_and_repair_json('{"key": "value"}')
        assert json.loads(result) == {"key": "value"}

    def test_strip_markdown_fences(self, pipeline):
        result = pipeline._extract_and_repair_json('```json\n{"a": 1}\n```')
        assert json.loads(result) == {"a": 1}

    def test_trailing_text_trimmed(self, pipeline):
        result = pipeline._extract_and_repair_json('{"a": 1}\nHere is my explanation')
        assert json.loads(result) == {"a": 1}

    def test_missing_comma_fixed(self, pipeline):
        bad = '{\n  "a": 1\n  "b": 2\n}'
        result = pipeline._extract_and_repair_json(bad)
        data = json.loads(result)
        assert data["a"] == 1
        assert data["b"] == 2

    def test_truncated_json_repaired(self, pipeline):
        bad = '{"items": [{"name": "foo"'
        result = pipeline._extract_and_repair_json(bad)
        data = json.loads(result)
        assert data["items"][0]["name"] == "foo"

    def test_control_characters_accepted(self, pipeline):
        """strict=False allows control chars in strings."""
        bad = '{"text": "line1\nline2"}'
        result = pipeline._extract_and_repair_json(bad)
        data = json.loads(result)
        assert "line1" in data["text"]

    def test_unparseable_raises_valueerror(self, pipeline):
        with pytest.raises(ValueError, match="Could not parse"):
            pipeline._extract_and_repair_json("not json at all {{{")


# =============================================================================
# Key Normalization (Analysis Pipeline)
# =============================================================================


class TestKeyNormalization:
    """Test _normalize_keys in AnalysisPipeline."""

    def test_quality_alias(self):
        from aicodegencrew.pipelines.analysis.pipeline import AnalysisPipeline

        data = {"quality": {"grade": "B"}, "macro_architecture": {}}
        normalized = AnalysisPipeline._normalize_keys(data)
        assert "architecture_quality" in normalized
        assert "quality" not in normalized

    def test_no_overwrite_existing(self):
        from aicodegencrew.pipelines.analysis.pipeline import AnalysisPipeline

        data = {"quality": {"old": True}, "architecture_quality": {"new": True}}
        normalized = AnalysisPipeline._normalize_keys(data)
        # Should NOT overwrite existing canonical key
        assert normalized["architecture_quality"] == {"new": True}

    def test_multiple_aliases(self):
        from aicodegencrew.pipelines.analysis.pipeline import AnalysisPipeline

        data = {
            "quality": {"grade": "B"},
            "summary": "test",
            "grade": "A",
            "api_design": {"endpoints": 50},
        }
        normalized = AnalysisPipeline._normalize_keys(data)
        assert "architecture_quality" in normalized
        assert "executive_summary" in normalized
        assert "overall_grade" in normalized
        assert "api" in normalized


# =============================================================================
# Plan Stage4 JSON (strict=False)
# =============================================================================


class TestPlanJsonParsing:
    """Test json.loads(strict=False) for Plan stage."""

    def test_control_character_in_plan_json(self):
        """The exact error from the log: control char in implementation_steps."""
        bad = '{"plan": {"steps": ["Update angular.json\\nreplace legacy"]}}'
        # With strict=True this would fail
        data = json.loads(bad, strict=False)
        assert "steps" in data["plan"]

    def test_raw_newline_in_string(self):
        bad = '{"description": "line1\nline2"}'
        data = json.loads(bad, strict=False)
        assert "line1" in data["description"]

    def test_raw_tab_in_string(self):
        bad = '{"code": "if (x)\t{ return; }"}'
        data = json.loads(bad, strict=False)
        assert "if (x)" in data["code"]
