"""
Stage 1: Input Parser

Parses task inputs from multiple formats (JIRA XML, DOCX, Excel, logs)
and normalizes to TaskInput schema.

Duration: <1 second (deterministic)
"""

import json
from pathlib import Path
from typing import Dict, Any

from ..schemas import TaskInput
from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


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
            from ....crews.development_planning.parsers import (
                parse_jira_xml,
                parse_docx,
                parse_excel,
                parse_text,
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

        if extension == '.xml':
            task = self._parse_jira_xml(file_path)
        elif extension == '.docx':
            task = self._parse_docx(file_path)
        elif extension in ['.xlsx', '.xls']:
            task = self._parse_excel(file_path)
        elif extension in ['.txt', '.log']:
            task = self._parse_text(file_path)
        else:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported: .xml, .docx, .xlsx, .xls, .txt, .log"
            )

        logger.info(f"[Stage1] Parsed task: {task.task_id} - {task.summary}")

        return task

    def _parse_jira_xml(self, file_path: Path) -> TaskInput:
        """Parse JIRA XML export."""
        from ....crews.development_planning.parsers.jira_parser import parse_jira_xml

        tasks = parse_jira_xml(file_path)

        if not tasks:
            raise ValueError("No tasks found in JIRA XML")

        # Take first task (usually one task per file)
        task_data = tasks[0]

        return TaskInput(
            task_id=task_data.get("task_id", "UNKNOWN"),
            source_file=str(file_path),
            source_format="jira_xml",
            summary=task_data.get("summary", ""),
            description=task_data.get("description", ""),
            acceptance_criteria=task_data.get("acceptance_criteria", []),
            technical_notes=task_data.get("technical_notes", ""),
            labels=task_data.get("labels", []) + task_data.get("components", []),
            priority=task_data.get("priority", "Medium"),
        )

    def _parse_docx(self, file_path: Path) -> TaskInput:
        """Parse Confluence DOCX."""
        from ....crews.development_planning.parsers.docx_parser import parse_docx

        result = parse_docx(file_path)

        # Extract task info from DOCX structure
        task_id = file_path.stem  # Use filename as task ID
        summary = result.get("title", "")

        # Combine sections into description
        sections = result.get("sections", [])
        description = "\n\n".join(
            f"## {s['title']}\n" + "\n".join(s['content'])
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
        """Parse Excel requirements table."""
        from ....crews.development_planning.parsers.excel_parser import parse_excel

        result = parse_excel(file_path)

        task_id = file_path.stem

        # Extract from first sheet
        sheets = result.get("sheets", {})
        if not sheets:
            raise ValueError("No sheets found in Excel file")

        first_sheet = list(sheets.values())[0]
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
        from ....crews.development_planning.parsers.text_parser import parse_text

        result = parse_text(file_path)

        task_id = file_path.stem

        # Extract from log entries or errors
        log_entries = result.get("log_entries", [])
        errors = result.get("errors", [])

        if errors:
            # Build description from errors
            summary = f"Fix errors in {file_path.name}"
            description = "\n\n".join(
                f"Error: {e['message']}\nContext: {e.get('context', '')}"
                for e in errors[:5]
            )
        elif log_entries:
            summary = f"Investigate logs from {file_path.name}"
            description = "\n".join(
                f"[{e.get('level', 'INFO')}] {e.get('message', '')}"
                for e in log_entries[:10]
            )
        else:
            summary = f"Task from {file_path.name}"
            description = file_path.read_text(encoding='utf-8')[:1000]

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
