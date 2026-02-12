"""
Live code scanner for upgrade pattern detection.

Scans actual source files with regex patterns from upgrade rules.
Duration: 2-5 seconds (no LLM).
"""

import re
from pathlib import Path

from ....shared.utils.logger import setup_logger
from .base import CodePattern, UpgradeImpact, UpgradeRule, UpgradeRuleSet

logger = setup_logger(__name__)


class UpgradeCodeScanner:
    """Scans source code for upgrade-relevant patterns."""

    SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".cache"}

    def __init__(self, repo_path: str, frontend_root: str = "frontend"):
        self.repo_path = Path(repo_path)
        self.frontend_root = self.repo_path / frontend_root

        if not self.frontend_root.exists():
            if (self.repo_path / "angular.json").exists():
                self.frontend_root = self.repo_path

    def scan_rules(self, rule_set: UpgradeRuleSet) -> list[UpgradeImpact]:
        """Scan codebase for all rules in a rule set."""
        impacts = []
        for rule in rule_set.rules:
            impact = self._scan_rule(rule)
            impacts.append(impact)
            if impact.occurrences > 0:
                logger.info(
                    f"[Scanner] {rule.id}: {impact.occurrences} occurrences in {len(impact.affected_files)} files"
                )
        return impacts

    def _scan_rule(self, rule: UpgradeRule) -> UpgradeImpact:
        """Scan codebase for a single rule's patterns."""
        total_occurrences = 0
        all_affected_files = []
        details = {}

        for pattern in rule.detection_patterns:
            count, files = self._scan_pattern(pattern)
            total_occurrences += count
            all_affected_files.extend(files)
            details[pattern.name] = {"count": count, "files": files[:10]}

        unique_files = list(set(all_affected_files))

        return UpgradeImpact(
            rule=rule,
            occurrences=total_occurrences,
            affected_files=unique_files,
            estimated_effort_minutes=total_occurrences * rule.effort_per_occurrence,
            details=details,
        )

    def _scan_pattern(self, pattern: CodePattern) -> tuple[int, list[str]]:
        """Scan for a single code pattern."""
        count = 0
        affected_files = []
        search_root = self.frontend_root

        # Single-file patterns (package.json, angular.json, karma.conf.js)
        if pattern.file_glob in ("package.json", "angular.json", "karma.conf.js"):
            target = search_root / pattern.file_glob
            if target.exists():
                matches = self._count_in_file(target, pattern.regex)
                if matches > 0:
                    count += matches
                    affected_files.append(self._rel_path(target))
            return count, affected_files

        # Recursive glob patterns
        for fpath in search_root.rglob(pattern.file_glob):
            if self._should_skip(fpath):
                continue
            # Skip test files for non-test patterns
            if fpath.name.endswith(".spec.ts"):
                continue

            matches = self._count_in_file(fpath, pattern.regex)
            if matches > 0:
                count += matches
                affected_files.append(self._rel_path(fpath))

        return count, affected_files

    def _count_in_file(self, file_path: Path, regex: str) -> int:
        """Count regex matches in a file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return len(re.findall(regex, content))
        except Exception:
            return 0

    def _rel_path(self, path: Path) -> str:
        """Get path relative to repo root."""
        try:
            return str(path.relative_to(self.repo_path))
        except ValueError:
            return str(path)

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        parts = set(path.parts)
        return bool(parts & self.SKIP_DIRS)
