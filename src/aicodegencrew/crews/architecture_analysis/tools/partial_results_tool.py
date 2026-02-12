"""Tool to read partial analysis results for synthesis."""

import json
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PartialResultsInput(BaseModel):
    """Input for reading partial results."""

    pass  # No input needed - reads all files


class PartialResultsTool(BaseTool):
    """
    Tool to read all partial analysis JSON files for synthesis.

    This tool reads all task outputs from knowledge/phase2_analysis/analysis/
    and returns them as a merged context for the synthesis agent.
    """

    name: str = "read_partial_results"
    description: str = """
    Reads all partial analysis results from previous tasks.
    Returns a combined summary of all analyses for synthesis.
    Use this FIRST to get all the analysis outputs to merge.
    """
    args_schema: type[BaseModel] = PartialResultsInput

    analysis_dir: str = Field(default="knowledge/phase2_analysis/analysis")

    def __init__(self, analysis_dir: str = "knowledge/phase2_analysis/analysis"):
        super().__init__()
        self.analysis_dir = analysis_dir

    def _run(self) -> str:
        """Read all partial results and return summary."""
        analysis_path = Path(self.analysis_dir)

        if not analysis_path.exists():
            return json.dumps({"error": f"Analysis directory not found: {analysis_path}"})

        results = {}

        # Read all JSON files in analysis directory
        for json_file in sorted(analysis_path.glob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Use filename without extension as key
                    key = json_file.stem
                    results[key] = data
            except Exception as e:
                results[json_file.stem] = {"error": str(e)}

        if not results:
            return json.dumps({"error": "No analysis files found", "path": str(analysis_path)})

        # Create summary
        summary = {"files_read": len(results), "analyses": results}

        return json.dumps(summary, indent=2, ensure_ascii=False)
