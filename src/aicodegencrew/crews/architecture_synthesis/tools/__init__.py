"""Tools for Architecture Synthesis Crew.

CrewAI Best Practice Tools:
- FileReadTool: Read JSON/text files
- DocWriterTool: Write markdown documents
- DrawioDiagramTool: Create DrawIO diagrams
- FactsQueryTool: Architecture facts query — from shared module (ARCH-7 consolidation)
- ChunkedWriterTool: Chunked doc generation (Strategy 7)
- StereotypeListTool: Get components by stereotype (Strategy 2)
"""

from ....shared.tools import FactsQueryTool
from .chunked_writer_tool import ChunkedWriterTool, StereotypeListTool
from .doc_writer_tool import DocWriterTool
from .drawio_tool import DrawioDiagramTool
from .file_read_tool import FileReadTool

__all__ = [
    "ChunkedWriterTool",
    "DocWriterTool",
    "DrawioDiagramTool",
    "FactsQueryTool",
    "FileReadTool",
    "StereotypeListTool",
]
