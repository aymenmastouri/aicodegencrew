"""Tools for Implement Crew - Phase 5.

Custom tools for code generation and build verification.
Reuses FactsQueryTool and RAGQueryTool from the architecture analysis crew.

Tools:
- CodeReaderTool: Read source files from target repo
- CodeWriterTool: Write generated code to in-memory staging
- BuildRunnerTool: Run build commands per container
- BuildErrorParserTool: Parse build output into structured errors
- ImportIndexTool: Resolve exact imports (language-aware)
- DependencyLookupTool: Query dependency order/relations for a file
- PlanReaderTool: Read normalized plan context for developer agent
- TaskSourceTool: Read original JIRA XML task content from TASK_INPUT_DIR
- FactsQueryTool: (reused) Query architecture facts
- RAGQueryTool: (reused) ChromaDB semantic search
"""

# Re-export from architecture analysis crew (reuse, not copy)
from ....shared.tools import FactsQueryTool, RAGQueryTool
from .build_error_parser_tool import BuildErrorParserTool
from .build_runner_tool import BuildRunnerTool
from .code_reader_tool import CodeReaderTool
from .code_writer_tool import CodeWriterTool
from .dependency_tool import DependencyLookupTool
from .import_index_tool import ImportIndexTool
from .plan_reader_tool import PlanReaderTool
from .task_source_tool import TaskSourceTool

__all__ = [
    "BuildErrorParserTool",
    "BuildRunnerTool",
    "CodeReaderTool",
    "CodeWriterTool",
    "DependencyLookupTool",
    "FactsQueryTool",
    "ImportIndexTool",
    "PlanReaderTool",
    "RAGQueryTool",
    "TaskSourceTool",
]
