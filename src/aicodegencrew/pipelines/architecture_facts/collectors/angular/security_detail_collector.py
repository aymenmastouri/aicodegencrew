"""Angular Security Detail Specialist — Extracts Angular route guard facts.

Detects:
- Angular route guards (canActivate, canDeactivate, canLoad, CanActivateFn)
- Role checks within guards
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawSecurityDetail


class AngularSecurityDetailCollector(DimensionCollector):
    """Extracts Angular route guard security facts."""

    DIMENSION = "security_details"

    # Angular guards
    ANGULAR_GUARD_PATTERN = re.compile(r"canActivate|canDeactivate|canLoad|CanActivateFn")
    ANGULAR_ROLE_CHECK_PATTERN = re.compile(r"role[s]?\s*[=:]\s*\[([^\]]+)\]", re.IGNORECASE)

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Angular route guard facts."""
        self._log_start()
        self._collect_angular_security()
        self._log_end()
        return self.output

    def _collect_angular_security(self):
        """Collect Angular route guard facts."""
        ts_files = [f for f in self._find_files("*.ts") if "guard" in str(f).lower() or "auth" in str(f).lower()]

        for ts_file in ts_files:
            try:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if not self.ANGULAR_GUARD_PATTERN.search(content):
                continue

            class_match = re.search(r"(?:class|const)\s+(\w+)", content)
            guard_name = class_match.group(1) if class_match else ts_file.stem

            # Extract role checks
            roles = []
            for match in self.ANGULAR_ROLE_CHECK_PATTERN.finditer(content):
                raw_roles = match.group(1)
                roles.extend(re.findall(r"'([^']+)'", raw_roles))

            line_num = 1
            guard_match = self.ANGULAR_GUARD_PATTERN.search(content)
            if guard_match:
                line_num = content[: guard_match.start()].count("\n") + 1

            fact = RawSecurityDetail(
                name=guard_name,
                security_type="angular_guard",
                roles=roles,
                method="canActivate",
                class_name=guard_name,
                file_path=self._relative_path(ts_file),
                container_hint="frontend",
            )
            fact.add_evidence(
                path=self._relative_path(ts_file),
                line_start=line_num,
                line_end=line_num + 30,
                reason=f"Angular route guard: {guard_name}",
            )
            self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
