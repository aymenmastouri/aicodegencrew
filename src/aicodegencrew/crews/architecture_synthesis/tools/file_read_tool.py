"""File Read Tool for reading architecture facts JSON files.

IMPORTANT: This tool has safeguards to prevent token overflow:
- evidence_map.json: Returns only first 30 entries (use query tools for specific evidence)
- architecture_facts.json: Returns only summary (use FactsQueryTool for details)
"""

import json
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class FileReadInput(BaseModel):
    """Input for FileReadTool."""

    file_path: str = Field(..., description="Path to file to read")


# Maximum entries for evidence_map.json to prevent token overflow
MAX_EVIDENCE_ENTRIES = 30

# Maximum file size in bytes before truncation warning
MAX_FILE_SIZE_BYTES = 50000  # ~50KB


class FileReadTool(BaseTool):
    """
    Safe file read tool with size limits to prevent token overflow.

    IMPORTANT SAFEGUARDS:
    - evidence_map.json: Limited to 30 entries (422 entries would overflow)
    - architecture_facts.json: Returns structure summary only
    - Other JSON files: Size-limited output

    For detailed queries, use:
    - FactsQueryTool: Semantic search of architecture facts
    - StereotypeListTool: Get components by stereotype
    """

    name: str = "safe_file_read"
    description: str = (
        "Safely read files with size limits. "
        "For evidence_map.json: Returns first 30 entries only (use FactsQueryTool for queries). "
        "For architecture_facts.json: Returns structure summary only (use FactsQueryTool for details). "
        "WARNING: Prefer FactsQueryTool and StereotypeListTool for architecture data."
    )
    args_schema: type[BaseModel] = FileReadInput

    def _run(self, file_path: str, **kwargs) -> str:
        """Read file with safeguards against token overflow."""
        try:
            path = Path(file_path)

            if not path.exists():
                return f"ERROR: File not found: {file_path}"

            # Special handling for evidence_map.json
            if "evidence_map" in path.name.lower():
                return self._read_evidence_map_safe(path)

            # Special handling for architecture_facts.json
            if "architecture_facts" in path.name.lower():
                return self._read_facts_safe(path)

            # General JSON files - check size
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return f"WARNING: File {file_path} is {file_size} bytes (>{MAX_FILE_SIZE_BYTES}). Use FactsQueryTool for large files."

            # Read and return file content
            with open(path, encoding="utf-8") as f:
                content = f.read()

            return content

        except json.JSONDecodeError as e:
            return f"ERROR: Invalid JSON in {file_path}: {e}"
        except Exception as e:
            return f"ERROR reading {file_path}: {e}"

    def _read_evidence_map_safe(self, path: Path) -> str:
        """Read evidence_map.json with entry limit to prevent token overflow."""
        try:
            with open(path, encoding="utf-8") as f:
                evidence_map = json.load(f)

            total_entries = len(evidence_map)

            # Limit to first N entries
            limited_entries = dict(list(evidence_map.items())[:MAX_EVIDENCE_ENTRIES])

            result = {
                "_meta": {
                    "total_evidence_entries": total_entries,
                    "returned_entries": len(limited_entries),
                    "truncated": total_entries > MAX_EVIDENCE_ENTRIES,
                    "note": f"Only first {MAX_EVIDENCE_ENTRIES} entries returned. Use FactsQueryTool or grep for specific evidence IDs.",
                },
                "evidence": limited_entries,
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"ERROR reading evidence_map: {e}"

    def _read_facts_safe(self, path: Path) -> str:
        """Read architecture_facts.json with summary only to prevent token overflow."""
        try:
            with open(path, encoding="utf-8") as f:
                facts = json.load(f)

            # Create summary instead of full content
            summary = {
                "_meta": {"note": "Summary only. Use FactsQueryTool or StereotypeListTool for details."},
                "system": facts.get("system", {}),
                "architecture_style": facts.get("architecture_style", {}),
                "statistics": {
                    "containers": len(facts.get("containers", [])),
                    "components": len(facts.get("components", [])),
                    "relations": len(facts.get("relations", [])),
                    "interfaces": len(facts.get("interfaces", [])),
                },
                # Include containers (usually small) but not components (can be 800+)
                "containers": facts.get("containers", []),
            }

            return json.dumps(summary, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"ERROR reading facts: {e}"
