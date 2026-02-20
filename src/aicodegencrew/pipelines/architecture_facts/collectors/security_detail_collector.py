"""
SecurityDetailCollector - Extracts method-level security, CSRF/CORS configuration.

Extends the existing spring/security_collector.py (which only returns RawComponent).
This collector extracts DETAILED security facts:
- @PreAuthorize("hasRole('...')"), @Secured, @RolesAllowed with roles
- Method-level security mapping: Controller method -> required role
- CSRF/CORS configuration from SecurityConfig
- Angular route guards

Output -> security_details dimension
"""

import re
from pathlib import Path

from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawSecurityDetail


class SecurityDetailCollector(DimensionCollector):
    """Collects detailed security facts beyond structural security components."""

    DIMENSION = "security_details"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # Java/Spring patterns
    PRE_AUTHORIZE_PATTERN = re.compile(r'@PreAuthorize\s*\(\s*"([^"]+)"\s*\)', re.MULTILINE)
    SECURED_PATTERN = re.compile(r'@Secured\s*\(\s*\{?\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*\s*\}?\s*\)', re.MULTILINE)
    ROLES_ALLOWED_PATTERN = re.compile(
        r'@RolesAllowed\s*\(\s*\{?\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*\s*\}?\s*\)', re.MULTILINE
    )
    HAS_ROLE_PATTERN = re.compile(r"hasRole\s*\(\s*'([^']+)'\s*\)")
    HAS_AUTHORITY_PATTERN = re.compile(r"hasAuthority\s*\(\s*'([^']+)'\s*\)")

    # Method before annotation
    METHOD_PATTERN = re.compile(r"(?:public|protected|private)\s+\w+\s+(\w+)\s*\(", re.MULTILINE)
    CLASS_PATTERN = re.compile(r"class\s+(\w+)")

    # CSRF/CORS
    CSRF_PATTERN = re.compile(r"\.csrf\s*\(\s*\)\s*\.\s*(\w+)")
    CORS_PATTERN = re.compile(r"\.cors\s*\(|CorsConfiguration|@CrossOrigin")
    CORS_ALLOWED_ORIGINS_PATTERN = re.compile(r'allowedOrigins?\s*\(\s*"([^"]+)"')

    # Angular guards
    ANGULAR_GUARD_PATTERN = re.compile(r"canActivate|canDeactivate|canLoad|CanActivateFn")
    ANGULAR_ROLE_CHECK_PATTERN = re.compile(r"role[s]?\s*[=:]\s*\[([^\]]+)\]", re.IGNORECASE)

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect all security detail facts."""
        self._log_start()

        # Java/Kotlin files
        self._collect_java_security()

        # TypeScript (Angular guards)
        self._collect_angular_security()

        self._log_end()
        return self.output

    def _collect_java_security(self):
        """Collect method-level security from Java/Kotlin files."""
        java_files = self._find_files("*.java") + self._find_files("*.kt")

        logger.info(f"[SecurityDetailCollector] Scanning {len(java_files)} Java/Kotlin files")

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            class_match = self.CLASS_PATTERN.search(content)
            class_name = class_match.group(1) if class_match else java_file.stem

            # @PreAuthorize
            for match in self.PRE_AUTHORIZE_PATTERN.finditer(content):
                expr = match.group(1)
                roles = self.HAS_ROLE_PATTERN.findall(expr) + self.HAS_AUTHORITY_PATTERN.findall(expr)
                method_name = self._find_next_method(content, match.end())
                line_num = content[: match.start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}.{method_name}" if method_name else class_name,
                    security_type="pre_authorize",
                    roles=roles,
                    method=method_name or "",
                    class_name=class_name,
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f'@PreAuthorize("{expr}")',
                    snippet=f'@PreAuthorize("{expr}")',
                )
                self.output.add_fact(fact)

            # @Secured
            for match in self.SECURED_PATTERN.finditer(content):
                roles = [r for r in match.groups() if r]
                method_name = self._find_next_method(content, match.end())
                line_num = content[: match.start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}.{method_name}" if method_name else class_name,
                    security_type="secured",
                    roles=roles,
                    method=method_name or "",
                    class_name=class_name,
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f"@Secured with roles: {roles}",
                )
                self.output.add_fact(fact)

            # @RolesAllowed
            for match in self.ROLES_ALLOWED_PATTERN.finditer(content):
                roles = [r for r in match.groups() if r]
                method_name = self._find_next_method(content, match.end())
                line_num = content[: match.start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}.{method_name}" if method_name else class_name,
                    security_type="roles_allowed",
                    roles=roles,
                    method=method_name or "",
                    class_name=class_name,
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f"@RolesAllowed with roles: {roles}",
                )
                self.output.add_fact(fact)

            # CSRF configuration
            for match in self.CSRF_PATTERN.finditer(content):
                csrf_action = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}_csrf",
                    security_type="csrf",
                    roles=[],
                    method="",
                    class_name=class_name,
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                    metadata={"csrf_action": csrf_action},
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 3,
                    reason=f"CSRF configuration: {csrf_action}",
                )
                self.output.add_fact(fact)

            # CORS configuration
            if self.CORS_PATTERN.search(content):
                origins = self.CORS_ALLOWED_ORIGINS_PATTERN.findall(content)
                line_num = content[: self.CORS_PATTERN.search(content).start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}_cors",
                    security_type="cors",
                    roles=[],
                    method="",
                    class_name=class_name,
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                    metadata={"allowed_origins": origins},
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 10,
                    reason=f"CORS configuration in {class_name}",
                )
                self.output.add_fact(fact)

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

    def _find_next_method(self, content: str, pos: int) -> str | None:
        """Find the next method declaration after a given position."""
        remaining = content[pos : pos + 200]
        match = self.METHOD_PATTERN.search(remaining)
        return match.group(1) if match else None

    def _should_skip(self, path: Path) -> bool:
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
