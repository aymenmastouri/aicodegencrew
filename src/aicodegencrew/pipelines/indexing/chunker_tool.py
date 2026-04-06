"""Text chunking tool for stable, deterministic chunking."""

import hashlib
from typing import Any

from ...shared.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChunkerInput(BaseModel):
    """Input schema for ChunkerTool."""

    files: list[dict[str, Any]] = Field(..., description="List of file dictionaries with 'path' and 'content'")
    chunk_chars: int = Field(default=1500, description="Target characters per chunk")
    chunk_overlap: int = Field(default=200, description="Character overlap between chunks")


class ChunkerTool(BaseTool):
    name: str = "chunker"
    description: str = (
        "Chunks text files into overlapping segments with deterministic chunk IDs. "
        "Preserves context and generates stable identifiers for indexing."
    )
    args_schema: type[BaseModel] = ChunkerInput

    def _run(
        self,
        files: list[dict[str, Any]],
        chunk_chars: int = 1500,
        chunk_overlap: int = 200,
    ) -> dict[str, Any]:
        """Chunk files into text segments."""
        if chunk_overlap >= chunk_chars:
            return {
                "success": False,
                "error": f"chunk_overlap ({chunk_overlap}) must be less than chunk_chars ({chunk_chars})",
            }

        all_chunks = []
        for file_info in files:
            if content := file_info.get("content"):
                all_chunks.extend(self._chunk_text(content, file_info.get("path", ""), chunk_chars, chunk_overlap))

        stats = {
            "total_files": len(files),
            "total_chunks": len(all_chunks),
            "avg_chunk_size": sum(len(c["text"]) for c in all_chunks) // len(all_chunks) if all_chunks else 0,
        }
        logger.info(f"Created {stats['total_chunks']} chunks from {stats['total_files']} files")

        return {
            "success": True,
            "chunks": all_chunks,
            "stats": stats,
        }

    def _chunk_text(
        self,
        text: str,
        file_path: str,
        chunk_chars: int,
        chunk_overlap: int,
    ) -> list[dict[str, Any]]:
        """Chunk text into overlapping segments."""
        if len(text) <= chunk_chars:
            return [self._create_chunk(file_path, 0, text, 0, len(text))]

        chunks = []
        start = 0
        chunk_index = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_chars, text_len)
            chunk_text = text[start:end]

            chunks.append(self._create_chunk(file_path, chunk_index, chunk_text, start, end))

            if end >= text_len:
                break

            start = end - chunk_overlap
            chunk_index += 1

        return chunks

    def _create_chunk(self, file_path: str, index: int, text: str, start: int, end: int) -> dict[str, Any]:
        """Helper to create consistent chunk objects."""
        return {
            "chunk_id": self._generate_chunk_id(file_path, index, text),
            "file_path": file_path,
            "chunk_index": index,
            "text": text,
            "start_char": start,
            "end_char": end,
        }

    def _generate_chunk_id(self, file_path: str, chunk_index: int, text: str) -> str:
        """Generate deterministic chunk ID.

        Args:
            file_path: Source file path
            chunk_index: Chunk index
            text: Chunk text

        Returns:
            Deterministic chunk ID
        """
        # Create hash from file path, index, and text prefix
        text_prefix = text[:100] if len(text) > 100 else text
        hash_input = f"{file_path}:{chunk_index}:{text_prefix}"

        hash_digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        # Format: {file_path_hash[:8]}:{chunk_index:04d}:{content_hash[:8]}
        file_hash = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:8]
        content_hash = hash_digest[:8]

        return f"{file_hash}:{chunk_index:04d}:{content_hash}"
