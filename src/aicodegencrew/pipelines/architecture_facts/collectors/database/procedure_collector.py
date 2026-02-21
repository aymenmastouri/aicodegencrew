"""
Oracle Procedure Collector - Extracts stored procedure and package facts.

Detects:
- CREATE PROCEDURE
- CREATE FUNCTION
- CREATE PACKAGE
- CREATE PACKAGE BODY
- CREATE TRIGGER

Output: Procedure/package facts for data_model.json
"""

import re
from pathlib import Path

from ..base import DimensionCollector, RawEntity, RelationHint


class OracleProcedureCollector(DimensionCollector):
    """Extracts Oracle stored procedure and package facts."""

    DIMENSION = "database_procedures"

    def collect(self):
        """Collect procedure/package facts from SQL files."""
        self._log_start()

        # Find SQL files (using _find_files for SKIP_DIRS pruning)
        sql_files = []
        for pattern in ["*.sql", "*.pls", "*.pkb", "*.pks", "*.prc", "*.fnc", "*.trg"]:
            sql_files.extend(self._find_files(pattern))

        for sql_file in sql_files:
            try:
                content = self._read_file_content(sql_file)
                rel_path = self._relative_path(sql_file)

                # Procedures
                for fact in self._extract_procedures(rel_path, content):
                    self.output.add_fact(fact)

                # Functions
                for fact in self._extract_functions(rel_path, content):
                    self.output.add_fact(fact)

                # Packages
                for fact in self._extract_packages(rel_path, content):
                    self.output.add_fact(fact)

                # Triggers
                for fact in self._extract_triggers(rel_path, content):
                    self.output.add_fact(fact)

                # Dependencies
                for rel in self._extract_dependencies(rel_path, content):
                    self.output.add_relation(rel)

            except Exception:
                continue

        self._log_end()
        return self.output

    def _extract_procedures(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract procedure definitions."""
        facts = []

        proc_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+"
            r"(?:(\w+)\.)?(\w+)\s*"
            r"(\([^)]*\))?\s*"
            r"(?:IS|AS)",
            re.IGNORECASE,
        )

        for match in proc_pattern.finditer(content):
            schema = match.group(1) or ""
            proc_name = match.group(2)
            params = match.group(3) or "()"
            line_num = content[: match.start()].count("\n") + 1
            param_count = params.count(",") + 1 if params.strip() != "()" else 0

            entity = RawEntity(
                name=proc_name, type="procedure", schema=schema,
                metadata={"param_count": param_count},
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 50,
                reason=f"CREATE PROCEDURE {proc_name}",
            )
            facts.append(entity)

        return facts

    def _extract_functions(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract function definitions."""
        facts = []

        func_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+"
            r"(?:(\w+)\.)?(\w+)\s*"
            r"(\([^)]*\))?\s*"
            r"RETURN\s+(\w+(?:\([^)]*\))?)",
            re.IGNORECASE,
        )

        for match in func_pattern.finditer(content):
            schema = match.group(1) or ""
            func_name = match.group(2)
            return_type = match.group(4)
            line_num = content[: match.start()].count("\n") + 1

            entity = RawEntity(
                name=func_name, type="function", schema=schema,
                tags=[f"returns_{return_type.lower()}"],
                metadata={"return_type": return_type},
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 50,
                reason=f"CREATE FUNCTION {func_name}",
            )
            facts.append(entity)

        return facts

    def _extract_packages(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract package definitions."""
        facts = []

        pkg_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(BODY\s+)?"
            r"(?:(\w+)\.)?(\w+)\s*"
            r"(?:IS|AS)",
            re.IGNORECASE,
        )

        for match in pkg_pattern.finditer(content):
            is_body = bool(match.group(1))
            schema = match.group(2) or ""
            pkg_name = match.group(3)
            line_num = content[: match.start()].count("\n") + 1

            entity_type = "package_body" if is_body else "package_spec"

            # Count procedures/functions in package
            pkg_end = content.find("END " + pkg_name, match.end())
            if pkg_end == -1:
                pkg_end = len(content)

            pkg_content = content[match.end() : pkg_end]
            proc_count = len(re.findall(r"PROCEDURE\s+\w+", pkg_content, re.IGNORECASE))
            func_count = len(re.findall(r"FUNCTION\s+\w+", pkg_content, re.IGNORECASE))

            entity = RawEntity(
                name=pkg_name, type=entity_type, schema=schema,
                tags=[f"{proc_count}_procedures", f"{func_count}_functions"],
                metadata={"proc_count": proc_count, "func_count": func_count},
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 100,
                reason=f"CREATE PACKAGE {'BODY ' if is_body else ''}{pkg_name}",
            )
            facts.append(entity)

        return facts

    def _extract_triggers(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract trigger definitions."""
        facts = []

        trigger_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+"
            r"(?:(\w+)\.)?(\w+)\s+"
            r"(BEFORE|AFTER|INSTEAD\s+OF)\s+"
            r"(INSERT|UPDATE|DELETE)(?:\s+OR\s+(?:INSERT|UPDATE|DELETE))*\s+"
            r"ON\s+(?:(\w+)\.)?(\w+)",
            re.IGNORECASE,
        )

        for match in trigger_pattern.finditer(content):
            schema = match.group(1) or ""
            trigger_name = match.group(2)
            timing = match.group(3)
            event = match.group(4)
            table_name = match.group(6)
            line_num = content[: match.start()].count("\n") + 1

            entity = RawEntity(
                name=trigger_name, type="trigger", schema=schema,
                tags=[timing.lower(), event.lower(), f"on_{table_name.lower()}"],
                metadata={"table": table_name, "timing": timing, "event": event},
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 30,
                reason=f"CREATE TRIGGER {trigger_name} ON {table_name}",
            )
            facts.append(entity)

        return facts

    def _extract_dependencies(self, rel_path: str, content: str) -> list[RelationHint]:
        """Extract procedure/package dependencies."""
        relations = []

        # Collect all defined procedure/function names
        defined = set()
        for match in re.finditer(r"(?:PROCEDURE|FUNCTION)\s+(\w+)", content, re.IGNORECASE):
            defined.add(match.group(1).upper())

        # Find calls within procedure bodies
        current_proc = None
        for match in re.finditer(
            r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+(?:\w+\.)?(\w+))|"
            r"(\w+)\s*\(",
            content,
            re.IGNORECASE,
        ):
            if match.group(1):
                current_proc = match.group(1)
            elif match.group(2) and current_proc:
                called = match.group(2).upper()
                if called in defined and called != current_proc.upper():
                    line_num = content[: match.start()].count("\n") + 1
                    hint = RelationHint(
                        from_name=current_proc,
                        to_name=called,
                        type="calls",
                    )
                    hint.add_evidence(
                        path=rel_path, line_start=line_num, line_end=line_num,
                        reason=f"{current_proc} calls {called}",
                    )
                    relations.append(hint)

        return relations
