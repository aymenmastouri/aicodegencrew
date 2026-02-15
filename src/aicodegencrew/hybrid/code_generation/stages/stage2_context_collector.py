"""
Stage 2: Context Collector

Gathers source code and patterns from the target repository
for each affected component.

Duration: 2-5s (file I/O only, no LLM)
"""

import json
from pathlib import Path

from ....shared.paths import DISCOVER_SYMBOLS
from ....shared.utils.logger import setup_logger
from ..schemas import CodegenPlanInput, CollectedContext, ComponentTarget, FileContext

logger = setup_logger(__name__)

# Language detection by file extension
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


class ContextCollectorStage:
    """Collect source code and context for each targeted component."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self._symbol_index: list[dict] | None = None

    def run(self, plan: CodegenPlanInput) -> CollectedContext:
        """
        Collect file contents and context for all affected components.

        Args:
            plan: Validated plan from Stage 1.

        Returns:
            CollectedContext with file contents and patterns.
        """
        logger.info(f"[Stage2] Collecting context for {len(plan.affected_components)} components from {self.repo_path}")

        file_contexts = []
        skipped = 0

        for comp in plan.affected_components:
            ctx = self._collect_file_context(comp, plan)
            if ctx:
                file_contexts.append(ctx)
            else:
                skipped += 1

        result = CollectedContext(
            file_contexts=file_contexts,
            total_files=len(file_contexts),
            skipped_files=skipped,
        )

        logger.info(f"[Stage2] Collected {result.total_files} files, skipped {result.skipped_files}")

        return result

    def _collect_file_context(self, comp: ComponentTarget, plan: CodegenPlanInput) -> FileContext | None:
        """Collect context for a single component file."""
        file_path = self._resolve_file_path(comp.file_path)

        if not file_path:
            if comp.change_type == "create":
                # New file — no existing content to read
                return FileContext(
                    file_path=comp.file_path,
                    content="",
                    language=self._detect_language(comp.file_path),
                    sibling_files=self._find_siblings(comp.file_path),
                    related_patterns=self._extract_related_patterns(comp, plan),
                    component=comp,
                )
            logger.warning(f"[Stage2] File not found: {comp.file_path}")
            return None

        # Read file content
        content = self._read_file(file_path)
        if content is None:
            logger.warning(f"[Stage2] Could not read: {file_path}")
            return None

        # Use symbol index for targeted extraction, or fall back to truncation
        content = self._extract_targeted_content(content, str(file_path), comp.name)

        return FileContext(
            file_path=str(file_path),
            content=content,
            language=self._detect_language(str(file_path)),
            sibling_files=self._find_siblings(str(file_path)),
            related_patterns=self._extract_related_patterns(comp, plan),
            component=comp,
        )

    def _resolve_file_path(self, file_path: str) -> Path | None:
        """Resolve a file path to an absolute path in the target repo."""
        if not file_path:
            return None

        # Try absolute path first
        p = Path(file_path)
        if p.is_absolute() and p.exists():
            return p

        # Try relative to repo root
        p = self.repo_path / file_path
        if p.exists():
            return p

        # Try stripping leading src/ or similar prefixes
        for prefix in ("src/main/java/", "src/main/resources/", "src/", "app/"):
            p = self.repo_path / prefix / file_path
            if p.exists():
                return p

        return None

    def _find_siblings(self, file_path: str, max_siblings: int = 5) -> list[str]:
        """Find sibling files in the same directory for pattern reference."""
        p = Path(file_path)
        parent = p.parent if p.is_absolute() else (self.repo_path / p).parent

        if not parent.exists():
            return []

        siblings = []
        try:
            for f in sorted(parent.iterdir()):
                if f.is_file() and f.name != p.name and f.suffix in EXT_TO_LANG:
                    siblings.append(str(f))
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

    def _load_symbol_index(self) -> list[dict]:
        """Lazy-load symbols.jsonl for targeted context extraction."""
        if self._symbol_index is not None:
            return self._symbol_index

        symbols_path = Path(DISCOVER_SYMBOLS)
        if not symbols_path.exists():
            self._symbol_index = []
            return self._symbol_index

        records = []
        try:
            with open(symbols_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            logger.info(f"[Stage2] Loaded {len(records)} symbols for context targeting")
        except Exception as e:
            logger.debug(f"[Stage2] Could not load symbol index: {e}")
            records = []

        self._symbol_index = records
        return self._symbol_index

    def _get_target_line_range(self, file_path: str, comp_name: str) -> tuple[int, int] | None:
        """Use symbol index to find the exact line range for a component.

        Returns (start_line, end_line) or None if not found.
        """
        symbols = self._load_symbol_index()
        if not symbols:
            return None

        # Normalize path for comparison
        norm_path = file_path.replace("\\", "/")

        best = None
        for sym in symbols:
            sym_path = sym.get("path", "").replace("\\", "/")
            if sym_path not in norm_path and norm_path not in sym_path:
                continue
            if sym.get("kind") in ("class", "interface") and sym.get("symbol", "") == comp_name:
                start = sym.get("line", 0)
                end = sym.get("end_line", 0)
                if start and end:
                    best = (start, end)
                    break

        return best

    def _extract_targeted_content(self, content: str, file_path: str, comp_name: str) -> str:
        """Extract only the relevant method/class body using symbol index.

        Falls back to full-file truncation if symbol index is unavailable.
        """
        line_range = self._get_target_line_range(file_path, comp_name)
        if not line_range:
            # Fall back to truncation
            if len(content) > MAX_FILE_CHARS:
                return content[:MAX_FILE_CHARS] + "\n// ... (truncated)"
            return content

        start, end = line_range
        lines = content.splitlines()

        # Add some context lines around the target range
        context_padding = 5
        start_idx = max(0, start - 1 - context_padding)
        end_idx = min(len(lines), end + context_padding)

        targeted = "\n".join(lines[start_idx:end_idx])

        # If the targeted section is still too large, truncate
        if len(targeted) > MAX_FILE_CHARS:
            targeted = targeted[:MAX_FILE_CHARS] + "\n// ... (truncated)"

        logger.info(
            f"[Stage2] Symbol-targeted: {comp_name} in {Path(file_path).name} "
            f"lines {start}-{end} ({len(targeted)} chars vs {len(content)} total)"
        )
        return targeted

    @staticmethod
    def _extract_related_patterns(comp: ComponentTarget, plan: CodegenPlanInput) -> list[str]:
        """Extract patterns relevant to this component."""
        patterns = []

        # Security patterns
        for sec in plan.patterns.get("security_considerations", []):
            if isinstance(sec, dict):
                patterns.append(f"[security] {sec.get('security_type', '')}: {sec.get('recommendation', '')}")

        # Validation patterns
        for val in plan.patterns.get("validation_strategy", []):
            if isinstance(val, dict):
                target = val.get("target_class", "")
                if comp.name.lower() in target.lower() or not target:
                    patterns.append(f"[validation] {val.get('validation_type', '')}: {val.get('recommendation', '')}")

        # Error handling patterns
        for err in plan.patterns.get("error_handling", []):
            if isinstance(err, dict):
                patterns.append(f"[error] {err.get('exception_class', '')}: {err.get('recommendation', '')}")

        return patterns[:10]
