"""
Stage 1: Input Parser

Parses task inputs from multiple formats (JIRA XML, DOCX, Excel, logs)
and normalizes to TaskInput schema.

Duration: <1 second (deterministic)
"""

from pathlib import Path

from ....shared.utils.logger import setup_logger
from ..schemas import TaskInput

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Configurable task-type detection rules (ARCH-4)
# ---------------------------------------------------------------------------
# Extend by adding new entries without touching _detect_task_type() logic.
# Example: add "kotlin_feature": {"keywords": ["kotlin", "coroutine"]} to
# detect Kotlin-specific tasks.
TASK_TYPE_RULES: dict[str, dict] = {
    # Build-tool migrations that look like upgrades but are NOT version bumps.
    # Matched against task SUMMARY only (to avoid false positives from comments).
    "build_migration": {
        "summary_exclusions": [
            "sass compiler",
            "sass migration",
            "scss migration",
            "builder migration",
            "build tool migration",
            "webpack migration",
            "migration des sass",
            "sass import deprecation",
        ],
    },
    # Version upgrade detection uses a three-tier score system.
    "upgrade": {
        # Strong signals (weight=3): direct framework+action combos
        "strong_patterns": [
            # Angular
            "angular upgrade",
            "upgrade angular",
            "angular update",
            "update angular",
            "ng update",
            "angular migration",
            "migrate angular",
            # Spring
            "spring boot upgrade",
            "upgrade spring",
            "spring migration",
            "spring boot update",
            "spring security upgrade",
            # Java / JDK
            "java upgrade",
            "upgrade java",
            "jdk upgrade",
            "upgrade jdk",
            "java 17",
            "java 21",
            "java 25",
            "openjdk upgrade",
            # Playwright
            "playwright upgrade",
            "upgrade playwright",
            "playwright update",
            # React / Vue
            "react upgrade",
            "upgrade react",
            "vue upgrade",
            "upgrade vue",
        ],
        # Medium signals (weight=2)
        "medium_patterns": [
            "version bump",
            "breaking changes",
            "upgrade to v",
            "upgrade von",
            "upgrade auf",
            "migration guide",
            "ng update",
            "update guide",
        ],
        # Framework keywords used for weak signal detection
        "framework_keywords": [
            "angular",
            "spring",
            "react",
            "vue",
            "typescript",
            "@angular",
            "spring-boot",
            "spring boot",
            "playwright",
            "java ",
            "jdk",
            "openjdk",
        ],
        # Upgrade verbs for weak signal detection
        "upgrade_verbs": ["upgrade", "migrate", "migration"],
        # Minimum score to classify as upgrade
        "min_score": 3,
    },
    "bugfix": {
        "keywords": ["fix", "bug", "error", "crash", "regression", "defect"],
    },
    "refactoring": {
        "keywords": ["refactor", "clean up", "technical debt", "restructure"],
    },
    # "feature" is the default fallback — no keywords needed
}


class InputParserStage:
    """
    Parse task inputs from various formats.

    Supported formats:
    - JIRA XML (.xml)
    - Confluence DOCX (.docx)
    - Excel (.xlsx, .xls)
    - Text/Logs (.txt, .log)
    """

    def __init__(self):
        self.parsers_available = self._check_parsers()

    def _check_parsers(self) -> bool:
        """Check if parser modules are available."""
        try:
            from ..parsers import (  # noqa: F401
                parse_docx,
                parse_excel,
                parse_text,
                parse_xml,
            )

            return True
        except ImportError as e:
            logger.warning(f"Parser modules not available: {e}")
            return False

    def run(self, input_file: str) -> TaskInput:
        """
        Parse input file and return normalized TaskInput.

        Args:
            input_file: Path to input file

        Returns:
            TaskInput with normalized data

        Raises:
            ValueError: If file format not supported or parsing fails
        """
        logger.info(f"[Stage1] Parsing input file: {input_file}")

        file_path = Path(input_file)

        if not file_path.exists():
            raise ValueError(f"Input file not found: {input_file}")

        # Auto-detect format by extension
        extension = file_path.suffix.lower()

        if extension == ".xml":
            task = self._parse_xml(file_path)
        elif extension == ".docx":
            task = self._parse_docx(file_path)
        elif extension in [".xlsx", ".xls"]:
            task = self._parse_excel(file_path)
        elif extension in [".txt", ".log"]:
            task = self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}. Supported: .xml, .docx, .xlsx, .xls, .txt, .log")

        task = self._detect_task_type(task)
        logger.info(f"[Stage1] Parsed task: {task.task_id} - {task.summary} (type={task.task_type})")

        return task

    def _detect_task_type(self, task: TaskInput) -> TaskInput:
        """Detect task type from semantic content analysis (score-based).

        Driven by TASK_TYPE_RULES — add new task types there without modifying
        this method.
        """
        text = f"{task.summary} {task.description} {task.technical_notes}".lower()
        labels_text = " ".join(task.labels).lower()
        combined = f"{text} {labels_text}"
        summary_lower = task.summary.lower()

        # 1. Check build-tool migrations first (summary only → avoids false positives)
        build_migration_rules = TASK_TYPE_RULES.get("build_migration", {})
        is_build_tool_migration = any(
            pat in summary_lower
            for pat in build_migration_rules.get("summary_exclusions", [])
        )
        if is_build_tool_migration:
            task.task_type = "refactoring"
            logger.info("[Stage1] Build-tool migration detected (not version upgrade)")
            return task

        # 2. Score-based upgrade detection driven by TASK_TYPE_RULES["upgrade"]
        upgrade_rules = TASK_TYPE_RULES.get("upgrade", {})
        upgrade_score = 0

        for pat in upgrade_rules.get("strong_patterns", []):
            if pat in combined:
                upgrade_score += 3

        for pat in upgrade_rules.get("medium_patterns", []):
            if pat in combined:
                upgrade_score += 2

        has_upgrade_verb = any(w in combined for w in upgrade_rules.get("upgrade_verbs", []))
        has_framework = any(w in combined for w in upgrade_rules.get("framework_keywords", []))
        if has_upgrade_verb and has_framework:
            upgrade_score += 2
        elif has_upgrade_verb:
            upgrade_score += 1

        min_score = upgrade_rules.get("min_score", 3)
        if upgrade_score >= min_score:
            task.task_type = "upgrade"
            logger.info(f"[Stage1] Upgrade detected (score={upgrade_score})")
            return task

        # 3. Keyword-based detection for remaining types (bugfix, refactoring)
        for type_name in ("bugfix", "refactoring"):
            type_rules = TASK_TYPE_RULES.get(type_name, {})
            if any(kw in text for kw in type_rules.get("keywords", [])):
                task.task_type = type_name
                return task

        # 4. Default fallback
        task.task_type = "feature"
        return task

    def _parse_xml(self, file_path: Path) -> TaskInput:
        """Parse XML file (any format)."""
        from ..parsers.xml_parser import parse_xml

        tasks = parse_xml(file_path)

        if not tasks:
            raise ValueError("No tasks found in JIRA XML")

        # Take first task (usually one task per file)
        task_data = tasks[0]

        return TaskInput(
            task_id=task_data.get("task_id", "UNKNOWN"),
            source_file=str(file_path),
            source_format="xml",
            summary=task_data.get("summary", ""),
            description=task_data.get("description", ""),
            acceptance_criteria=task_data.get("acceptance_criteria", []),
            technical_notes=task_data.get("technical_notes", ""),
            labels=task_data.get("labels", []) + task_data.get("components", []),
            priority=task_data.get("priority", "Medium"),
            jira_type=task_data.get("jira_type", "Task"),
            linked_tasks=task_data.get("linked_tasks", []),
        )

    def _parse_docx(self, file_path: Path) -> TaskInput:
        """Parse DOCX file."""
        from ..parsers.docx_parser import parse_docx

        result = parse_docx(file_path)

        # Extract task info from DOCX structure
        task_id = file_path.stem  # Use filename as task ID
        summary = result.get("title", "")

        # Combine sections into description
        sections = result.get("sections", [])
        description = "\n\n".join(
            f"## {s['title']}\n" + "\n".join(s["content"])
            for s in sections[:5]  # First 5 sections
        )

        return TaskInput(
            task_id=task_id,
            source_file=str(file_path),
            source_format="docx",
            summary=summary,
            description=description,
            acceptance_criteria=[],
            technical_notes="",
            labels=[],
            priority="Medium",
        )

    def _parse_excel(self, file_path: Path) -> TaskInput:
        """Parse Excel file."""
        from ..parsers.excel_parser import parse_excel

        result = parse_excel(file_path)

        task_id = file_path.stem

        # Extract from first sheet
        sheets = result.get("sheets", {})
        if not sheets:
            raise ValueError("No sheets found in Excel file")

        first_sheet = next(iter(sheets.values()))
        data = first_sheet.get("data", [])

        if not data:
            raise ValueError("No data found in Excel file")

        # Assume first row is headers, second row is data
        if len(data) >= 2:
            headers = data[0]
            row = data[1]

            # Try to map columns
            summary = self._find_value(headers, row, ["Summary", "Title", "Description"])
            description = self._find_value(headers, row, ["Details", "Requirements", "Description"])
        else:
            summary = str(data[0][0]) if data[0] else ""
            description = ""

        return TaskInput(
            task_id=task_id,
            source_file=str(file_path),
            source_format="excel",
            summary=summary,
            description=description,
            acceptance_criteria=[],
            technical_notes="",
            labels=[],
            priority="Medium",
        )

    def _parse_text(self, file_path: Path) -> TaskInput:
        """Parse text/log file."""
        from ..parsers.text_parser import parse_text

        result = parse_text(file_path)

        task_id = file_path.stem

        # Extract from log entries or errors
        log_entries = result.get("log_entries", [])
        errors = result.get("errors", [])

        if errors:
            # Build description from errors
            summary = f"Fix errors in {file_path.name}"
            description = "\n\n".join(f"Error: {e['message']}\nContext: {e.get('context', '')}" for e in errors[:5])
        elif log_entries:
            summary = f"Investigate logs from {file_path.name}"
            description = "\n".join(f"[{e.get('level', 'INFO')}] {e.get('message', '')}" for e in log_entries[:10])
        else:
            summary = f"Task from {file_path.name}"
            description = file_path.read_text(encoding="utf-8")[:1000]

        return TaskInput(
            task_id=task_id,
            source_file=str(file_path),
            source_format="text",
            summary=summary,
            description=description,
            acceptance_criteria=[],
            technical_notes="",
            labels=[],
            priority="Medium",
        )

    @staticmethod
    def _find_value(headers: list, row: list, column_names: list) -> str:
        """Find value in row by matching column names."""
        for col_name in column_names:
            try:
                idx = headers.index(col_name)
                return str(row[idx]) if idx < len(row) else ""
            except (ValueError, IndexError):
                continue
        return ""
