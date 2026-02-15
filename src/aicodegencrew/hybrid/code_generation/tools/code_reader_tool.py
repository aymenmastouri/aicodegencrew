"""
Code Reader Tool - Read source files from target repository.

Reuses file reading and sibling discovery logic from Stage 2 (Context Collector).
Provides agents with access to existing source code for context during generation.
"""

import json
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import truncate_response

logger = setup_logger(__name__)

# Language detection by file extension (reused from stage2_context_collector)
EXT_TO_LANG = {
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".html": "html",
    ".scss": "scss",
    ".css": "scss",
    ".json": "json",
    ".xml": "xml",
}

# Max characters per file to fit LLM context window
MAX_FILE_CHARS = 12000


class CodeReaderInput(BaseModel):
    """Input schema for CodeReaderTool."""

    file_path: str = Field(..., description="Path to the file to read (relative to repo root or absolute)")
    include_siblings: bool = Field(
        default=False,
        description="Include names of sibling files in the same directory for pattern reference",
    )


class CodeReaderTool(BaseTool):
    """
    Read source files from the target repository.

    Provides agents with existing source code context for generation.
    Supports both absolute and repo-relative paths.

    Usage Examples:
    1. read_file(file_path="src/main/java/com/app/FooService.java")
    2. read_file(file_path="src/app/foo/foo.component.ts", include_siblings=True)
    """

    name: str = "read_file"
    description: str = (
        "Read a source file from the target repository. "
        "Provide a repo-relative or absolute file path. "
        "Use include_siblings=True to see nearby files for pattern reference."
    )
    args_schema: type[BaseModel] = CodeReaderInput

    # Configuration
    repo_path: str = ""

    def __init__(self, repo_path: str = "", **kwargs):
        """Initialize with target repository path."""
        super().__init__(**kwargs)
        if repo_path:
            self.repo_path = repo_path

    def _run(self, file_path: str, include_siblings: bool = False) -> str:
        """Read a source file and optionally list siblings."""
        try:
            resolved = self._resolve_path(file_path)
            if resolved is None:
                return json.dumps(
                    {
                        "error": f"File not found: {file_path}",
                        "file_path": file_path,
                    }
                )

            content = self._read_file(resolved)
            if content is None:
                return json.dumps(
                    {
                        "error": f"Could not read file: {file_path}",
                        "file_path": file_path,
                    }
                )

            # Truncate large files
            truncated = False
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n// ... (truncated)"
                truncated = True

            language = self._detect_language(str(resolved))

            result = {
                "file_path": str(resolved),
                "content": content,
                "language": language,
                "size_chars": len(content),
                "truncated": truncated,
            }

            if include_siblings:
                result["siblings"] = self._find_siblings(str(resolved))

            output = json.dumps(result, ensure_ascii=False)
            return truncate_response(output, hint="file was truncated to fit context")

        except Exception as e:
            logger.error(f"CodeReaderTool error: {e}")
            return json.dumps({"error": str(e), "file_path": file_path})

    def _resolve_path(self, file_path: str) -> Path | None:
        """Resolve a file path to an absolute path in the target repo."""
        if not file_path:
            return None

        # Try absolute path first
        p = Path(file_path)
        if p.is_absolute() and p.exists():
            return p

        # Try relative to repo root
        if self.repo_path:
            repo = Path(self.repo_path)
            p = repo / file_path
            if p.exists():
                return p

            # Try stripping common prefixes
            for prefix in ("src/main/java/", "src/main/resources/", "src/", "app/"):
                p = repo / prefix / file_path
                if p.exists():
                    return p

        return None

    def _find_siblings(self, file_path: str, max_siblings: int = 5) -> list[str]:
        """Find sibling files in the same directory."""
        p = Path(file_path)
        parent = p.parent if p.is_absolute() else (Path(self.repo_path) / p).parent

        if not parent.exists():
            return []

        siblings = []
        try:
            for f in sorted(parent.iterdir()):
                if f.is_file() and f.name != p.name and f.suffix in EXT_TO_LANG:
                    siblings.append(f.name)
                    if len(siblings) >= max_siblings:
                        break
        except OSError:
            pass

        return siblings

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        return EXT_TO_LANG.get(ext, "other")

    @staticmethod
    def _read_file(path: Path) -> str | None:
        """Read file content safely."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="latin-1")
            except Exception:
                return None
        except Exception:
            return None
