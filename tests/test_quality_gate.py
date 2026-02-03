"""Tests for quality gate tool."""

import pytest
import json
import tempfile
from pathlib import Path
from aicodegencrew.shared.tools.quality_gate_tool import QualityGateTool
from aicodegencrew.shared.models.analysis_schema import ArchitectureAnalysis, Evidence, Technology, ProjectUnit


@pytest.fixture
def quality_tool():
    """Fixture for quality gate tool."""
    return QualityGateTool()


@pytest.fixture
def valid_analysis():
    """Fixture for valid analysis."""
    return ArchitectureAnalysis(
        repo_name="test-repo",
        repo_path="/test/path",
        analysis_timestamp="2026-01-31T12:00:00Z",
        summary="Test architecture summary",
        technologies=[
            Technology(
                name="Java",
                category="backend",
                evidence=[
                    Evidence(
                        file_path="src/Main.java",
                        chunk_id="test_001",
                        snippet="public class Main"
                    )
                ]
            )
        ],
        project_units=[
            ProjectUnit(
                name="backend-service",
                type="backend-module",
                root_path="backend/",
                evidence=[
                    Evidence(
                        file_path="backend/pom.xml",
                        chunk_id="test_002",
                        snippet="<artifactId>backend</artifactId>"
                    )
                ]
            )
        ],
        recommendations=["Implement API documentation"],
        metadata={"evidence_count": 10}
    )


def test_quality_gate_valid_analysis(quality_tool, valid_analysis, tmp_path):
    """Test quality gate with valid analysis."""
    # Save analysis to file
    analysis_path = tmp_path / "analyze.json"
    with open(analysis_path, "w") as f:
        json.dump(valid_analysis.model_dump(), f)
    
    # Run quality gate
    output_path = tmp_path / "quality-report.md"
    result = quality_tool._run(
        analysis_path=str(analysis_path),
        output_path=str(output_path),
        min_evidence_count=1
    )
    
    assert result["success"] is True
    assert result["overall_status"] == "PASS"
    assert result["passed"] > 0
    assert result["failed"] == 0
    assert output_path.exists()


def test_quality_gate_missing_evidence(quality_tool, valid_analysis, tmp_path):
    """Test quality gate with missing evidence."""
    # Remove evidence from technology
    analysis_dict = valid_analysis.model_dump()
    analysis_dict["technologies"][0]["evidence"] = []
    
    analysis_path = tmp_path / "analyze.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis_dict, f)
    
    output_path = tmp_path / "quality-report.md"
    result = quality_tool._run(
        analysis_path=str(analysis_path),
        output_path=str(output_path),
        min_evidence_count=1
    )
    
    assert result["success"] is True
    assert result["overall_status"] == "FAIL"
    assert result["failed"] > 0


def test_quality_gate_missing_required_fields(quality_tool, tmp_path):
    """Test quality gate with missing required fields."""
    # Create analysis with missing summary
    analysis_dict = {
        "repo_name": "test",
        "repo_path": "/test",
        "analysis_timestamp": "2026-01-31T12:00:00Z",
        "summary": "",  # Empty summary
        "technologies": [],
        "project_units": [],
        "recommendations": [],
        "metadata": {}
    }
    
    analysis_path = tmp_path / "analyze.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis_dict, f)
    
    output_path = tmp_path / "quality-report.md"
    result = quality_tool._run(
        analysis_path=str(analysis_path),
        output_path=str(output_path),
        min_evidence_count=1
    )
    
    assert result["success"] is True
    assert result["overall_status"] == "FAIL"


def test_quality_gate_no_technologies(quality_tool, tmp_path):
    """Test quality gate with no technologies detected."""
    analysis_dict = {
        "repo_name": "test",
        "repo_path": "/test",
        "analysis_timestamp": "2026-01-31T12:00:00Z",
        "summary": "Test summary",
        "technologies": [],  # No technologies
        "project_units": [],
        "recommendations": [],
        "metadata": {}
    }
    
    analysis_path = tmp_path / "analyze.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis_dict, f)
    
    output_path = tmp_path / "quality-report.md"
    result = quality_tool._run(
        analysis_path=str(analysis_path),
        output_path=str(output_path)
    )
    
    assert result["success"] is True
    # Should fail because no technologies detected
    checks = result["checks"]
    tech_check = next((c for c in checks if "Technology" in c["name"]), None)
    assert tech_check is not None
    assert tech_check["status"] == "fail"


def test_quality_gate_invalid_json(quality_tool, tmp_path):
    """Test quality gate with invalid JSON."""
    analysis_path = tmp_path / "analyze.json"
    with open(analysis_path, "w") as f:
        f.write("invalid json content")
    
    output_path = tmp_path / "quality-report.md"
    result = quality_tool._run(
        analysis_path=str(analysis_path),
        output_path=str(output_path)
    )
    
    assert result["success"] is False
    assert "error" in result


def test_quality_gate_report_format(quality_tool, valid_analysis, tmp_path):
    """Test that quality report has correct format."""
    analysis_path = tmp_path / "analyze.json"
    with open(analysis_path, "w") as f:
        json.dump(valid_analysis.model_dump(), f)
    
    output_path = tmp_path / "quality-report.md"
    result = quality_tool._run(
        analysis_path=str(analysis_path),
        output_path=str(output_path)
    )
    
    assert result["success"] is True
    
    # Check report content
    report_content = output_path.read_text(encoding="utf-8")
    assert "# Quality Gate Report" in report_content
    assert "Overall Status:" in report_content
    assert "Check Results" in report_content
