"""
DocWriterTool - Tool for writing documentation files.

Used by Architecture Synthesis agents to write C4/arc42 documents.
"""

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class DocWriterInput(BaseModel):
    """Input schema for DocWriterTool."""

    file_path: str = Field(description="The path to the file to write (relative to knowledge/phase3_synthesis/)")
    content: str = Field(description="The content to write to the file")
    overwrite: bool = Field(default=True, description="Whether to overwrite existing file (default: True)")


class DocWriterTool(BaseTool):
    """
    Tool for writing documentation files.

    Writes markdown/text content to files in the knowledge/phase3_synthesis directory.
    Used by C4 and arc42 agents to persist their output.
    """

    name: str = "doc_writer"
    description: str = (
        "Write documentation content to a file. "
        "Use this tool to persist C4 diagrams or arc42 chapters. "
        "Provide the file path (relative to knowledge/phase3_synthesis/) and content."
    )
    args_schema: type[BaseModel] = DocWriterInput

    def _run(self, file_path: str, content: str, overwrite: bool = True) -> str:
        """Write content to a file."""
        try:
            # Base directory for Phase 3 synthesis docs
            base_dir = Path("knowledge/phase3_synthesis")

            # Strip base_dir prefix if agent already included it (prevents double-nesting)
            clean_path = file_path.replace("knowledge/phase3_synthesis/", "").replace("knowledge\\phase3_synthesis\\", "")
            # Also strip legacy path if agent uses old convention
            clean_path = clean_path.replace("knowledge/architecture/", "").replace("knowledge\\architecture\\", "")
            full_path = base_dir / clean_path

            # Check if file exists and overwrite is False
            if full_path.exists() and not overwrite:
                return f"File {full_path} already exists and overwrite=False. Skipping."

            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote {len(content)} characters to {full_path}"

        except Exception as e:
            return f"Error writing file: {e}"
