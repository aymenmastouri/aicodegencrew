"""
Code Writer Tool - Write generated code to in-memory staging.

Does NOT write to disk. Accumulates files in a shared staging dict
that Stage 5 (Output Writer) collects after the crew finishes.
Provides diff preview using difflib.unified_diff.
"""

import difflib
import json
from pathlib import Path
from typing import Literal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import truncate_response
from .code_reader_tool import EXT_TO_LANG

logger = setup_logger(__name__)

# Staging dict type: file_path -> {content, action, original_content, language}
StagingDict = dict[str, dict]


class CodeWriterInput(BaseModel):
    """Input schema for CodeWriterTool."""

    file_path: str = Field(
        ..., description="Target file path (absolute or repo-relative)"
    )
    content: str = Field(
        ..., description="Complete file content to write"
    )
    action: Literal["modify", "create", "delete"] = Field(
        default="modify",
        description="Type of change: modify (update existing), create (new file), delete",
    )


class CodeWriterTool(BaseTool):
    """
    Write generated code to an in-memory staging area.

    Files are NOT written to disk immediately. They accumulate in a
    shared staging dict that the orchestrator collects after the crew finishes.

    Usage Examples:
    1. write_code(file_path="src/.../FooService.java", content="...", action="modify")
    2. write_code(file_path="src/.../NewFile.java", content="...", action="create")
    """

    name: str = "write_code"
    description: str = (
        "Write generated code to the staging area (in-memory, not to disk). "
        "Provide the complete file content. Returns a diff preview. "
        "Use action='create' for new files, 'modify' for updates, 'delete' to remove."
    )
    args_schema: type[BaseModel] = CodeWriterInput

    # Configuration
    repo_path: str = ""

    # Shared staging dict (injected at instantiation)
    _staging: StagingDict = {}

    def __init__(self, repo_path: str = "", staging: StagingDict | None = None, **kwargs):
        """Initialize with repo path and shared staging dict."""
        super().__init__(**kwargs)
        if repo_path:
            self.repo_path = repo_path
        self._staging = staging if staging is not None else {}

    @property
    def staging(self) -> StagingDict:
        """Access the staging dict."""
        return self._staging

    def _run(
        self,
        file_path: str,
        content: str,
        action: str = "modify",
    ) -> str:
        """Stage a file for writing."""
        try:
            # Validate inputs
            if not file_path or not file_path.strip():
                return json.dumps({"error": "file_path cannot be empty"})

            if action != "delete" and not content.strip():
                return json.dumps({"error": "content cannot be empty for modify/create"})

            # Normalize path
            file_path = file_path.strip()

            # Detect language
            ext = Path(file_path).suffix.lower()
            language = EXT_TO_LANG.get(ext, "other")

            # Get original content for diff (from previous staging or disk)
            original = ""
            if file_path in self._staging:
                original = self._staging[file_path].get("original_content", "")
            elif self.repo_path and action == "modify":
                original = self._read_original(file_path)

            # Generate diff preview
            diff_preview = self._generate_diff(original, content, file_path)

            # Stage the file
            self._staging[file_path] = {
                "content": content if action != "delete" else "",
                "action": action,
                "original_content": original,
                "language": language,
            }

            result = {
                "status": "staged",
                "file_path": file_path,
                "action": action,
                "language": language,
                "size_chars": len(content),
                "total_staged_files": len(self._staging),
                "diff_preview": diff_preview,
            }

            output = json.dumps(result, ensure_ascii=False)
            return truncate_response(output, hint="diff preview truncated")

        except Exception as e:
            logger.error(f"CodeWriterTool error: {e}")
            return json.dumps({"error": str(e), "file_path": file_path})

    def _read_original(self, file_path: str) -> str:
        """Try to read original file from disk for diff."""
        try:
            p = Path(file_path)
            if not p.is_absolute() and self.repo_path:
                p = Path(self.repo_path) / file_path
            if p.exists():
                return p.read_text(encoding="utf-8")
        except Exception:
            pass
        return ""

    @staticmethod
    def _generate_diff(original: str, new_content: str, file_path: str, max_lines: int = 20) -> str:
        """Generate a unified diff preview (first N lines)."""
        if not original:
            # New file — show first lines
            lines = new_content.splitlines()[:max_lines]
            preview = "\n".join(f"+{line}" for line in lines)
            if len(new_content.splitlines()) > max_lines:
                preview += f"\n... (+{len(new_content.splitlines()) - max_lines} more lines)"
            return preview

        diff_lines = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{Path(file_path).name}",
            tofile=f"b/{Path(file_path).name}",
            lineterm="",
        ))

        if not diff_lines:
            return "(no changes)"

        # Return first max_lines of diff
        preview = "\n".join(diff_lines[:max_lines])
        if len(diff_lines) > max_lines:
            preview += f"\n... (+{len(diff_lines) - max_lines} more diff lines)"
        return preview
