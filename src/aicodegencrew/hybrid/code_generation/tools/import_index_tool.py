"""Import index lookup tool for Phase 5 agents."""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.token_budget import truncate_response
from ..preflight.import_index import ImportIndex, ImportIndexBuilder


class ImportIndexInput(BaseModel):
    """Input schema for ImportIndexTool."""

    symbol: str = Field(..., description="Symbol name to resolve (e.g. CoreModule, UserService)")
    from_file: str = Field(..., description="Current file path where import is needed")
    language: str = Field(..., description="Target language: java or typescript")


class ImportIndexTool(BaseTool):
    """Resolve exact import statements from a prebuilt index."""

    name: str = "lookup_import"
    description: str = (
        "Resolve an exact import statement for a symbol from the repository import index. "
        "Language-aware: TypeScript files get only TypeScript imports, Java files only Java imports."
    )
    args_schema: type[BaseModel] = ImportIndexInput

    repo_path: str = ""
    facts_path: str = "knowledge/extract/architecture_facts.json"
    _index: ImportIndex | None = None

    def __init__(
        self,
        repo_path: str = "",
        facts_path: str = "knowledge/extract/architecture_facts.json",
        import_index: ImportIndex | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if repo_path:
            self.repo_path = repo_path
        if facts_path:
            self.facts_path = facts_path
        self._index = import_index

    @property
    def import_index(self) -> ImportIndex:
        if self._index is None:
            self._index = ImportIndexBuilder(repo_path=self.repo_path, facts_path=self.facts_path).run()
        return self._index

    def _run(self, symbol: str, from_file: str, language: str) -> str:
        stmt = self.import_index.resolve(symbol, from_file, language)
        result = {
            "symbol": symbol,
            "from_file": from_file,
            "language": language,
            "import_statement": stmt,
            "found": bool(stmt),
        }
        return truncate_response(json.dumps(result, ensure_ascii=False), hint="import lookup truncated")
