"""
Oracle View Collector - Extracts database view facts.

Detects:
- CREATE VIEW
- CREATE MATERIALIZED VIEW
- View columns
- View dependencies

Output: View facts for data_model.json
"""

import re
from pathlib import Path

from ..base import DimensionCollector, RawEntity, RelationHint


class OracleViewCollector(DimensionCollector):
    """Extracts Oracle view facts."""

    DIMENSION = "database_views"

    def collect(self):
        """Collect view facts from SQL files."""
        self._log_start()

        # Find SQL files (using _find_files for SKIP_DIRS pruning)
        sql_files = []
        for pattern in ["*.sql", "*.ddl", "*.vw"]:
            sql_files.extend(self._find_files(pattern))

        for sql_file in sql_files:
            try:
                content = self._read_file_content(sql_file)
                rel_path = self._relative_path(sql_file)

                # Regular views
                for fact in self._extract_views(rel_path, content):
                    self.output.add_fact(fact)

                # Materialized views
                for fact in self._extract_materialized_views(rel_path, content):
                    self.output.add_fact(fact)

                # Extract view-table dependencies
                for rel in self._extract_view_dependencies(rel_path, content):
                    self.output.add_relation(rel)

            except Exception:
                continue

        self._log_end()
        return self.output

    def _extract_views(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract regular view definitions."""
        facts = []

        view_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?VIEW\s+"
            r"(?:(\w+)\.)?(\w+)\s*"
            r"(?:\([^)]+\))?\s*AS\s*"
            r"(SELECT\s+.+?)(?:;|$)",
            re.IGNORECASE | re.DOTALL,
        )

        for match in view_pattern.finditer(content):
            schema = match.group(1) or ""
            view_name = match.group(2)
            select_stmt = match.group(3)[:200]
            line_num = content[: match.start()].count("\n") + 1
            line_end = content[: match.end()].count("\n") + 1

            # Extract columns from SELECT as list[dict]
            columns = [{"name": col} for col in self._extract_view_columns(select_stmt)]

            entity = RawEntity(
                name=view_name, type="view", schema=schema, columns=columns,
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=min(line_end, line_num + 30),
                reason=f"CREATE VIEW {view_name}",
            )
            facts.append(entity)

        return facts

    def _extract_materialized_views(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract materialized view definitions."""
        facts = []

        mv_pattern = re.compile(
            r"CREATE\s+MATERIALIZED\s+VIEW\s+"
            r"(?:(\w+)\.)?(\w+)\s*"
            r"(?:BUILD\s+(?:IMMEDIATE|DEFERRED)\s*)?"
            r"(?:REFRESH\s+(?:FAST|COMPLETE|FORCE)\s*(?:ON\s+(?:DEMAND|COMMIT))?\s*)?"
            r"AS\s*(SELECT\s+.+?)(?:;|$)",
            re.IGNORECASE | re.DOTALL,
        )

        for match in mv_pattern.finditer(content):
            schema = match.group(1) or ""
            mv_name = match.group(2)
            line_num = content[: match.start()].count("\n") + 1
            line_end = content[: match.end()].count("\n") + 1

            # Detect refresh type
            refresh_type = "unknown"
            match_text = content[match.start() : match.end()].upper()
            if "REFRESH FAST" in match_text:
                refresh_type = "fast"
            elif "REFRESH COMPLETE" in match_text:
                refresh_type = "complete"

            entity = RawEntity(
                name=mv_name, type="materialized_view", schema=schema,
                tags=[f"refresh_{refresh_type}"],
                metadata={"refresh_type": refresh_type},
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=min(line_end, line_num + 40),
                reason=f"CREATE MATERIALIZED VIEW {mv_name}",
            )
            facts.append(entity)

        return facts

    def _extract_view_columns(self, select_stmt: str) -> list[str]:
        """Extract column names from SELECT statement."""
        columns = []

        select_match = re.search(r"SELECT\s+(.+?)\s+FROM", select_stmt, re.IGNORECASE | re.DOTALL)

        if select_match:
            column_part = select_match.group(1)
            for col in column_part.split(","):
                col = col.strip()
                alias_match = re.search(r"(?:AS\s+)?(\w+)\s*$", col, re.IGNORECASE)
                if alias_match:
                    columns.append(alias_match.group(1))

        return columns[:20]

    def _extract_view_dependencies(self, rel_path: str, content: str) -> list[RelationHint]:
        """Extract which tables a view depends on."""
        relations = []

        view_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:MATERIALIZED\s+)?VIEW\s+"
            r"(?:\w+\.)?(\w+)\s*.+?AS\s*SELECT.+?FROM\s+(.+?)(?:WHERE|GROUP|ORDER|;|$)",
            re.IGNORECASE | re.DOTALL,
        )

        for match in view_pattern.finditer(content):
            view_name = match.group(1)
            from_clause = match.group(2)

            table_matches = re.finditer(r"(?:FROM|JOIN)\s+(?:(\w+)\.)?(\w+)(?:\s+(\w+))?", from_clause, re.IGNORECASE)

            for tm in table_matches:
                table_name = tm.group(2)
                if table_name.upper() in ("SELECT", "WHERE", "AND", "OR", "ON", "AS"):
                    continue

                line_num = content[: match.start()].count("\n") + 1
                line_end = content[: match.end()].count("\n") + 1
                hint = RelationHint(
                    from_name=view_name,
                    to_name=table_name,
                    type="view_depends_on",
                )
                hint.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_end,
                    reason=f"View {view_name} references table {table_name}",
                )
                relations.append(hint)

        return relations
