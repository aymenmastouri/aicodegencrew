"""
Stage 2: Context Collector

Gathers source code and patterns from the target repository
for each affected component.

Duration: 2-5s (file I/O only, no LLM)
"""

from pathlib import Path

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

        # Truncate if too large
        if len(content) > MAX_FILE_CHARS:
            logger.info(f"[Stage2] Truncating {file_path.name}: {len(content)} -> {MAX_FILE_CHARS} chars")
            content = content[:MAX_FILE_CHARS] + "\n// ... (truncated)"

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
