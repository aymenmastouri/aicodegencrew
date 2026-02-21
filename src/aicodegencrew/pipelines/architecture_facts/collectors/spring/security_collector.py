"""
Spring Security Collector - Extracts security configuration facts.

Detects:
- @EnableWebSecurity
- SecurityFilterChain beans
- Authentication configuration
- Authorization rules
- OAuth2/JWT config

Output: Security components for components.json
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawComponent, RawEvidence, RelationHint


class SpringSecurityCollector(DimensionCollector):
    """Extracts Spring Security configuration facts."""

    DIMENSION = "spring_security"

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect security configuration facts."""
        self._log_start()

        # Find Java and Kotlin files
        all_files = self._find_files("*.java") + self._find_files("*.kt")

        for src_file in all_files:
            try:
                content = self._read_file_content(src_file)

                # Security Configuration classes
                if "@EnableWebSecurity" in content or "SecurityFilterChain" in content:
                    self._extract_security_config(src_file, content)

                # Auth providers
                if "AuthenticationProvider" in content or "UserDetailsService" in content:
                    self._extract_auth_providers(src_file, content)

                # Filters
                if "OncePerRequestFilter" in content or "GenericFilterBean" in content:
                    self._extract_filters(src_file, content)

            except Exception:
                continue

        # Check for security properties (YAML and properties)
        for props_file in (
            self._find_files("application*.yml")
            + self._find_files("application*.yaml")
            + self._find_files("application*.properties")
        ):
            try:
                content = self._read_file_content(props_file)
                if "security" in content.lower() or "oauth2" in content.lower() or "jwt" in content.lower():
                    self._extract_security_properties(props_file, content)
            except Exception:
                continue

        self._log_end()
        return self.output

    def _extract_security_config(self, file_path: Path, content: str) -> None:
        """Extract security configuration classes."""
        # Find class name
        class_match = re.search(r"class\s+(\w+)", content)
        if not class_match:
            return

        class_name = class_match.group(1)
        rel_path = self._relative_path(file_path)

        # Detect security features
        features = []
        if "csrf()" in content or "csrf." in content:
            features.append("csrf")
        if "cors()" in content or "cors." in content:
            features.append("cors")
        if "oauth2Login" in content or "oauth2ResourceServer" in content:
            features.append("oauth2")
        if "jwt" in content.lower():
            features.append("jwt")
        if "httpBasic" in content:
            features.append("http_basic")
        if "formLogin" in content:
            features.append("form_login")
        if "authorizeRequests" in content or "authorizeHttpRequests" in content:
            features.append("authorization")

        # Find line number
        line_num = 1
        for i, line in enumerate(content.split("\n"), 1):
            if "class " + class_name in line:
                line_num = i
                break

        comp = RawComponent(
            name=class_name,
            stereotype="security_config",
            file_path=rel_path,
            container_hint=self.container_id,
            tags=features,
            metadata={"features": features},
        )
        comp.add_evidence(
            path=rel_path,
            line_start=line_num,
            line_end=line_num + 50,
            reason=f"@EnableWebSecurity or SecurityFilterChain in {class_name}",
        )
        self.output.add_fact(comp)

    def _extract_auth_providers(self, file_path: Path, content: str) -> None:
        """Extract authentication provider implementations."""
        rel_path = self._relative_path(file_path)

        # AuthenticationProvider implementations
        provider_match = re.search(r"class\s+(\w+)\s+implements\s+.*AuthenticationProvider", content)
        if provider_match:
            class_name = provider_match.group(1)
            line_num = content[: provider_match.start()].count("\n") + 1

            comp = RawComponent(
                name=class_name,
                stereotype="auth_provider",
                file_path=rel_path,
                container_hint=self.container_id,
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 30,
                reason=f"AuthenticationProvider implementation: {class_name}",
            )
            self.output.add_fact(comp)

        # UserDetailsService implementations
        uds_match = re.search(r"class\s+(\w+)\s+implements\s+.*UserDetailsService", content)
        if uds_match:
            class_name = uds_match.group(1)
            line_num = content[: uds_match.start()].count("\n") + 1

            comp = RawComponent(
                name=class_name,
                stereotype="user_details_service",
                file_path=rel_path,
                container_hint=self.container_id,
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 30,
                reason=f"UserDetailsService implementation: {class_name}",
            )
            self.output.add_fact(comp)

    def _extract_filters(self, file_path: Path, content: str) -> None:
        """Extract security filter implementations."""
        rel_path = self._relative_path(file_path)

        # OncePerRequestFilter
        filter_match = re.search(r"class\s+(\w+)\s+extends\s+OncePerRequestFilter", content)
        if filter_match:
            class_name = filter_match.group(1)
            line_num = content[: filter_match.start()].count("\n") + 1

            # Detect filter type
            filter_type = "security_filter"
            if "jwt" in class_name.lower() or "jwt" in content.lower():
                filter_type = "jwt_filter"
            elif "auth" in class_name.lower():
                filter_type = "auth_filter"

            comp = RawComponent(
                name=class_name,
                stereotype=filter_type,
                file_path=rel_path,
                container_hint=self.container_id,
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 40,
                reason=f"OncePerRequestFilter: {class_name}",
            )
            self.output.add_fact(comp)

    def _extract_security_properties(self, file_path: Path, content: str) -> None:
        """Extract security properties from YAML."""
        rel_path = self._relative_path(file_path)

        # OAuth2 config
        if "oauth2:" in content:
            comp = RawComponent(
                name="oauth2_config",
                stereotype="security_property",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["oauth2"],
            )
            comp.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=50,
                reason="OAuth2 configuration in YAML",
            )
            self.output.add_fact(comp)

        # JWT config
        if "jwt:" in content:
            comp = RawComponent(
                name="jwt_config",
                stereotype="security_property",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["jwt"],
            )
            comp.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=50,
                reason="JWT configuration in YAML",
            )
            self.output.add_fact(comp)
