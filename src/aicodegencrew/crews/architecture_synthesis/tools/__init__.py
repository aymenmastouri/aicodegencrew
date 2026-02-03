"""Tools for Architecture Synthesis Crew.

CrewAI Best Practice Tools:
- FileReadTool: Read JSON/text files
- DocWriterTool: Write markdown documents
- DrawioDiagramTool: Create DrawIO diagrams
- FactsQueryTool: RAG-based facts query (Strategy 6)
- ChunkedWriterTool: Chunked doc generation (Strategy 7)
- StereotypeListTool: Get components by stereotype (Strategy 2)
"""

from .file_read_tool import FileReadTool
from .doc_writer_tool import DocWriterTool
from .drawio_tool import DrawioDiagramTool
from .facts_query_tool import FactsQueryTool
from .chunked_writer_tool import ChunkedWriterTool, StereotypeListTool

__all__ = [
    "FileReadTool",
    "DocWriterTool",
    "DrawioDiagramTool",
    "FactsQueryTool",
    "ChunkedWriterTool",
    "StereotypeListTool",
]
