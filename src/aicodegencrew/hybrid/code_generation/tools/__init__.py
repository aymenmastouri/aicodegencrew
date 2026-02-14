"""Tools for Implement Crew - Phase 6.

Custom tools for code generation, build verification, and test writing.
Reuses FactsQueryTool and RAGQueryTool from the architecture analysis crew.

Tools:
- CodeReaderTool: Read source files from target repo
- CodeWriterTool: Write generated code to in-memory staging
- BuildRunnerTool: Run build commands per container
- BuildErrorParserTool: Parse build output into structured errors
- TestPatternTool: Query test patterns from architecture facts
- TestWriterTool: Write test files to staging area
- FactsQueryTool: (reused) Query architecture facts
- RAGQueryTool: (reused) ChromaDB semantic search
"""

from .build_error_parser_tool import BuildErrorParserTool
from .build_runner_tool import BuildRunnerTool
from .code_reader_tool import CodeReaderTool
from .code_writer_tool import CodeWriterTool
from .test_pattern_tool import TestPatternTool
from .test_writer_tool import TestWriterTool

# Re-export from architecture analysis crew (reuse, not copy)
from ...architecture_analysis.tools import FactsQueryTool, RAGQueryTool

__all__ = [
    "BuildErrorParserTool",
    "BuildRunnerTool",
    "CodeReaderTool",
    "CodeWriterTool",
    "TestPatternTool",
    "TestWriterTool",
    "FactsQueryTool",
    "RAGQueryTool",
]
