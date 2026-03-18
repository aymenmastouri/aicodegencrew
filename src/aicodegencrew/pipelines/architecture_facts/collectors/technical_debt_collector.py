"""Technical Debt Collector — TODO/FIXME/HACK comments, deprecated usage, suppressed warnings.

Cross-cutting collector that scans all source files for technical debt indicators.
No ecosystem delegation needed — patterns are language-agnostic.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawTechDebtFact


class TechnicalDebtCollector(DimensionCollector):
    DIMENSION = "technical_debt"

    # TODO/FIXME/HACK/XXX markers in comments
    DEBT_MARKER_PATTERN = re.compile(
        r"(?:#|//|/\*|\*|--)\s*(TODO|FIXME|HACK|XXX|BUG|WORKAROUND)\b[:\s]*(.*)",
        re.IGNORECASE,
    )

    # Deprecated annotations/decorators
    DEPRECATED_PATTERNS = [
        re.compile(r"@Deprecated\b"),  # Java
        re.compile(r"@deprecated\b", re.IGNORECASE),  # General
        re.compile(r"\[\[deprecated\]\]"),  # C++17
        re.compile(r"warnings\.warn\(.*DeprecationWarning"),  # Python
        re.compile(r"@typing\.deprecated"),  # Python 3.13+
    ]

    # Suppressed warnings
    SUPPRESSION_PATTERNS = [
        (re.compile(r'@SuppressWarnings\s*\(\s*"([^"]+)"'), "java_suppress"),
        (re.compile(r"#\s*noqa\b(?::?\s*(\S+))?"), "python_noqa"),
        (re.compile(r"//\s*eslint-disable(?:-next-line)?(?:\s+(.+))?"), "eslint_disable"),
        (re.compile(r"//\s*nolint(?::(\w+))?"), "go_nolint"),
        (re.compile(r"#pragma\s+warning\s*\(\s*disable"), "cpp_pragma"),
        (re.compile(r"// @ts-ignore|// @ts-expect-error"), "ts_ignore"),
        (re.compile(r"#\s*type:\s*ignore"), "mypy_ignore"),
    ]

    # File patterns to scan (source code only)
    SOURCE_PATTERNS = ["*.java", "*.kt", "*.py", "*.ts", "*.js", "*.tsx", "*.jsx",
                       "*.cpp", "*.c", "*.h", "*.hpp", "*.cs", "*.go", "*.rs",
                       "*.rb", "*.scala", "*.xml", "*.yml", "*.yaml"]

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_debt_markers()
        self._collect_deprecated_usage()
        self._collect_suppressed_warnings()
        self._log_end()
        return self.output

    def _collect_debt_markers(self):
        """Scan all source files for TODO/FIXME/HACK/XXX markers."""
        for file_pattern in self.SOURCE_PATTERNS:
            for path in self._find_files(file_pattern):
                lines = self._read_file(path)
                rel = self._relative_path(path)
                for i, line in enumerate(lines, 1):
                    m = self.DEBT_MARKER_PATTERN.search(line)
                    if m:
                        marker_type = m.group(1).upper()
                        message = m.group(2).strip()[:200]  # Cap message length
                        severity = "high" if marker_type in ("FIXME", "BUG") else "medium" if marker_type in ("HACK", "WORKAROUND", "XXX") else "low"

                        fact = RawTechDebtFact(
                            name=f"{marker_type.lower()}:{rel}:{i}",
                            debt_type=marker_type.lower(),
                            message=message,
                            file_path=rel,
                            line_number=i,
                            severity=severity,
                        )
                        fact.add_evidence(rel, i, i, f"{marker_type}: {message[:80]}")
                        self.output.add_fact(fact)

    def _collect_deprecated_usage(self):
        """Scan for @Deprecated annotations and similar patterns."""
        for file_pattern in self.SOURCE_PATTERNS:
            for path in self._find_files(file_pattern):
                content = self._read_file_content(path)
                rel = self._relative_path(path)
                lines = content.splitlines()
                for pattern in self.DEPRECATED_PATTERNS:
                    for m in pattern.finditer(content):
                        line_num = content[:m.start()].count("\n") + 1
                        context = lines[line_num - 1].strip()[:150] if line_num <= len(lines) else ""
                        fact = RawTechDebtFact(
                            name=f"deprecated:{rel}:{line_num}",
                            debt_type="deprecated_usage",
                            message=context,
                            file_path=rel,
                            line_number=line_num,
                            severity="medium",
                        )
                        fact.add_evidence(rel, line_num, line_num + 2, f"Deprecated: {context[:80]}")
                        self.output.add_fact(fact)

    def _collect_suppressed_warnings(self):
        """Scan for suppressed warnings (@SuppressWarnings, # noqa, eslint-disable, etc.)."""
        for file_pattern in self.SOURCE_PATTERNS:
            for path in self._find_files(file_pattern):
                content = self._read_file_content(path)
                rel = self._relative_path(path)
                lines = content.splitlines()
                for pattern, suppression_type in self.SUPPRESSION_PATTERNS:
                    for m in pattern.finditer(content):
                        line_num = content[:m.start()].count("\n") + 1
                        detail = m.group(1) if m.lastindex and m.group(1) else suppression_type
                        context = lines[line_num - 1].strip()[:150] if line_num <= len(lines) else ""
                        fact = RawTechDebtFact(
                            name=f"suppressed:{rel}:{line_num}",
                            debt_type="suppressed_warning",
                            message=f"{suppression_type}: {detail}",
                            file_path=rel,
                            line_number=line_num,
                            severity="low",
                        )
                        fact.add_evidence(rel, line_num, line_num, f"Warning suppressed: {context[:80]}")
                        self.output.add_fact(fact)
