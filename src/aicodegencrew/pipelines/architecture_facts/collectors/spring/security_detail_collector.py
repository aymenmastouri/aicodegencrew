"""Spring Security Detail Specialist — Extracts Java/Kotlin method-level security facts.

Detects:
- @PreAuthorize("hasRole('...')"), @Secured, @RolesAllowed with roles
- Method-level security mapping: Controller method -> required role
- CSRF/CORS configuration from SecurityConfig
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawSecurityDetail


class SpringSecurityDetailCollector(DimensionCollector):
    """Extracts detailed security facts from Java/Kotlin sources."""

    DIMENSION = "security_details"

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

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect method-level security from Java/Kotlin files."""
        self._log_start()
        self._collect_java_security()
        self._log_end()
        return self.output

    def _collect_java_security(self):
        """Collect method-level security from Java/Kotlin files."""
        java_files = self._find_files("*.java") + self._find_files("*.kt")

        from .....shared.utils.logger import logger
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

            # @Secured — extract all quoted role strings from the annotation
            for match in self.SECURED_PATTERN.finditer(content):
                roles = re.findall(r'"([^"]+)"', match.group(0))
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

            # @RolesAllowed — extract all quoted role strings from the annotation
            for match in self.ROLES_ALLOWED_PATTERN.finditer(content):
                roles = re.findall(r'"([^"]+)"', match.group(0))
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

    def _find_next_method(self, content: str, pos: int) -> str | None:
        """Find the next method declaration after a given position."""
        remaining = content[pos : pos + 200]
        match = self.METHOD_PATTERN.search(remaining)
        return match.group(1) if match else None

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
