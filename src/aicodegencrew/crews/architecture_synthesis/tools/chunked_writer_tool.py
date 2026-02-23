"""
Chunked Writer Tool - Generate large documents in parts

CrewAI Best Practice: Split large documents into chunks to avoid token limits.
Each chunk is generated separately, then combined into final document.

Strategy 7: Chunked Generation
- Large documents (400+ lines) are split into sections
- Each section generated with focused context
- Final assembly combines all chunks
"""

from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChunkedWriteInput(BaseModel):
    """Input schema for ChunkedWriterTool."""

    file_path: str = Field(
        ..., description="Path to the output file (e.g., 'knowledge/document/arc42/05-building-blocks.md')"
    )
    section_title: str = Field(..., description="Title of the section to write (e.g., '## 5.2.1 Controllers')")
    content: str = Field(..., description="Content for this section (markdown formatted)")
    mode: str = Field(
        default="append",
        description="Write mode: 'create' (new file), 'append' (add section), 'finalize' (close document)",
    )


class ChunkedWriterTool(BaseTool):
    """
    Chunked documentation writer for large documents.

    CrewAI Best Practice:
    - Generate large docs in sections
    - Each section has focused context
    - Prevents token overflow
    - Maintains document coherence

    Usage Pattern:
    1. create: Initialize document with header
    2. append: Add each section (controllers, services, etc.)
    3. finalize: Complete document with footer/summary

    Example Agent Usage:
    1. ChunkedWriter(mode="create", file="05-building-blocks.md", section="# 05 Building Blocks")
    2. ChunkedWriter(mode="append", section="## Controllers", content="...")
    3. ChunkedWriter(mode="append", section="## Services", content="...")
    4. ChunkedWriter(mode="finalize", section="## Summary", content="...")
    """

    # Configurable output directory (set by base_crew)
    output_dir: str | None = None

    name: str = "chunked_writer"
    description: str = (
        "Write large documentation files in chunks/sections. "
        "Use this for documents over 200 lines! "
        "Modes: 'create' to start new doc, 'append' to add sections, 'finalize' to complete. "
        "Each call writes one section to avoid token limits."
    )
    args_schema: type[BaseModel] = ChunkedWriteInput

    # Track active documents being built
    _active_docs: dict[str, list[str]] = {}

    def _run(
        self,
        file_path: str,
        section_title: str,
        content: str,
        mode: str = "append",
    ) -> str:
        """
        Write a document section.

        Args:
            file_path: Target file path
            section_title: Section header
            content: Section content (markdown)
            mode: 'create', 'append', or 'finalize'

        Returns:
            Status message
        """
        try:
            # Base directory for architecture docs (same as doc_writer)
            base_dir = Path(self.output_dir) if self.output_dir else Path("knowledge/document")

            # Strip base_dir prefix if agent already included it (prevents double-nesting)
            clean_path = file_path.replace("knowledge/document/", "").replace("knowledge\\document\\", "")
            # Also strip legacy path if agent uses old convention
            clean_path = clean_path.replace("knowledge/architecture/", "").replace("knowledge\\architecture\\", "")
            path = base_dir / clean_path

            path.parent.mkdir(parents=True, exist_ok=True)

            if mode == "create":
                return self._create_document(path, section_title, content)
            elif mode == "append":
                return self._append_section(path, section_title, content)
            elif mode == "finalize":
                return self._finalize_document(path, section_title, content)
            else:
                return f"ERROR: Unknown mode '{mode}'. Use 'create', 'append', or 'finalize'."

        except Exception as e:
            logger.error(f"ChunkedWriter error: {e}")
            return f"ERROR: {e}"

    def _create_document(self, path: Path, title: str, content: str) -> str:
        """Create a new document with initial content."""
        # Start fresh
        self._active_docs[str(path)] = []

        # Build initial content
        doc_content = []

        # Add title
        if title:
            doc_content.append(title)
            doc_content.append("")

        # Add content
        if content:
            doc_content.append(content)
            doc_content.append("")

        self._active_docs[str(path)] = doc_content

        # Write to file
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(doc_content))

        line_count = len(doc_content)
        logger.info(f"Created document: {path} ({line_count} lines)")
        return f"SUCCESS: Created {path} with {line_count} lines. Ready for sections."

    def _append_section(self, path: Path, section_title: str, content: str) -> str:
        """Append a section to an existing document."""
        # Load current content if not in cache
        if str(path) not in self._active_docs:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    self._active_docs[str(path)] = f.read().splitlines()
            else:
                self._active_docs[str(path)] = []

        doc_content = self._active_docs[str(path)]

        # Add section
        doc_content.append("")  # Blank line before section
        if section_title:
            doc_content.append(section_title)
            doc_content.append("")

        if content:
            # Split content into lines
            content_lines = content.split("\n")
            doc_content.extend(content_lines)

        self._active_docs[str(path)] = doc_content

        # Write to file
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(doc_content))

        section_lines = len(content.split("\n")) if content else 0
        total_lines = len(doc_content)
        logger.info(f"Appended section '{section_title}' to {path} (+{section_lines} lines, total: {total_lines})")
        return f"SUCCESS: Added '{section_title}' ({section_lines} lines). Total: {total_lines} lines."

    def _finalize_document(self, path: Path, section_title: str, content: str) -> str:
        """Finalize document with closing content."""
        # Add final section
        self._append_section(path, section_title, content)

        # Add generation footer
        doc_content = self._active_docs.get(str(path), [])
        doc_content.append("")
        doc_content.append("---")
        doc_content.append("*Generated by Architecture Synthesis Crew*")

        # Write final version
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(doc_content))

        total_lines = len(doc_content)

        # Clean up cache
        if str(path) in self._active_docs:
            del self._active_docs[str(path)]

        logger.info(f"Finalized document: {path} ({total_lines} lines)")
        return f"SUCCESS: Finalized {path} with {total_lines} total lines."

    def get_document_status(self, file_path: str) -> dict[str, Any]:
        """Get status of a document being built."""
        path_str = str(Path(file_path))

        if path_str in self._active_docs:
            lines = self._active_docs[path_str]
            return {
                "status": "in_progress",
                "lines": len(lines),
                "sections": sum(1 for ln in lines if ln.startswith("#")),
            }

        path = Path(file_path)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                content = f.read()
            lines = content.splitlines()
            return {
                "status": "complete",
                "lines": len(lines),
                "sections": sum(1 for ln in lines if ln.startswith("#")),
            }

        return {
            "status": "not_started",
            "lines": 0,
            "sections": 0,
        }


class ComponentListInput(BaseModel):
    """Input for listing components by stereotype."""

    stereotype: str = Field(..., description="Component stereotype: 'controller', 'service', 'repository', 'entity'")
    container: str = Field(default="", description="Optional container filter")


class StereotypeListTool(BaseTool):
    """
    Helper tool to get component lists by stereotype.

    CrewAI Best Practice:
    - Agent requests specific stereotype list
    - Reduces context size vs full components list

    Strategy 2 Support: For Building Blocks splitting
    """

    name: str = "list_components_by_stereotype"
    description: str = (
        "Get list of components filtered by stereotype (controller/service/repository/entity). "
        "Use this to get focused lists for Building Block documentation. "
        "Returns component names, packages, and brief description."
    )
    args_schema: type[BaseModel] = ComponentListInput

    facts_path: str = "knowledge/extract/architecture_facts.json"
    _facts_cache: dict[str, Any] | None = None

    def __init__(self, facts_path: str = None, **kwargs):
        super().__init__(**kwargs)
        if facts_path:
            self.facts_path = facts_path

    def _load_facts(self) -> dict[str, Any]:
        if self._facts_cache is not None:
            return self._facts_cache

        path = Path(self.facts_path)
        if not path.exists():
            return {}

        import json

        with open(path, encoding="utf-8") as f:
            self._facts_cache = json.load(f)
        return self._facts_cache

    def _run(self, stereotype: str, container: str = "", **kwargs) -> str:
        """Get components by stereotype (limited to 30 to prevent token overflow)."""
        import json

        MAX_RESULTS = 30  # Prevent token overflow

        facts = self._load_facts()
        components = facts.get("components", [])

        # Filter by stereotype
        filtered = [c for c in components if c.get("stereotype", "").lower() == stereotype.lower()]

        # Filter by container if specified
        if container:
            filtered = [c for c in filtered if container.lower() in c.get("container", "").lower()]

        total_count = len(filtered)

        # LIMIT results to prevent token overflow
        limited = filtered[:MAX_RESULTS]

        # Build result
        result = {
            "stereotype": stereotype,
            "container_filter": container,
            "total_count": total_count,
            "returned_count": len(limited),
            "note": f"Showing top {len(limited)} of {total_count}. Focus on these key components."
            if total_count > MAX_RESULTS
            else None,
            "components": [
                {
                    "name": c.get("name", "Unknown"),
                    "package": c.get("package", ""),
                    "container": c.get("container", ""),
                    "description": c.get("description", "")[:80] if c.get("description") else "",
                }
                for c in limited
            ],
        }

        return json.dumps(result, indent=2, ensure_ascii=False)
