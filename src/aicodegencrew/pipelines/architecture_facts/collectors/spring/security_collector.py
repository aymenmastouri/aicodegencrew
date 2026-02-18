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

    def collect(self) -> CollectorOutput:
        """Collect security configuration facts."""
        facts: list[RawComponent] = []
        relations: list[RelationHint] = []

        # Find Java and Kotlin files
        all_files = self._find_files("*.java") + self._find_files("*.kt")

        for src_file in all_files:
            try:
                content = src_file.read_text(encoding="utf-8", errors="ignore")

                # Security Configuration classes
                if "@EnableWebSecurity" in content or "SecurityFilterChain" in content:
                    facts.extend(self._extract_security_config(src_file, content))

                # Auth providers
                if "AuthenticationProvider" in content or "UserDetailsService" in content:
                    facts.extend(self._extract_auth_providers(src_file, content))

                # Filters
                if "OncePerRequestFilter" in content or "GenericFilterBean" in content:
                    facts.extend(self._extract_filters(src_file, content))

            except Exception:
                continue

        # Check for security properties (YAML and properties)
        for props_file in (
            self._find_files("application*.yml")
            + self._find_files("application*.yaml")
            + self._find_files("application*.properties")
        ):
            try:
                content = props_file.read_text(encoding="utf-8", errors="ignore")
                if "security" in content.lower() or "oauth2" in content.lower() or "jwt" in content.lower():
                    facts.extend(self._extract_security_properties(props_file, content))
            except Exception:
                continue

        return CollectorOutput(facts=facts, relations=relations)

    def _extract_security_config(self, file_path: Path, content: str) -> list[RawComponent]:
        """Extract security configuration classes."""
        facts = []

        # Find class name
        class_match = re.search(r"class\s+(\w+)", content)
        if not class_match:
            return facts

        class_name = class_match.group(1)

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

        facts.append(
            RawComponent(
                name=class_name,
                component_type="security_config",
                file_path=file_path,
                description=f"Security configuration with: {', '.join(features)}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 50,
                    reason=f"@EnableWebSecurity or SecurityFilterChain in {class_name}",
                ),
                tags=features,
            )
        )

        return facts

    def _extract_auth_providers(self, file_path: Path, content: str) -> list[RawComponent]:
        """Extract authentication provider implementations."""
        facts = []

        # AuthenticationProvider implementations
        provider_match = re.search(r"class\s+(\w+)\s+implements\s+.*AuthenticationProvider", content)
        if provider_match:
            class_name = provider_match.group(1)
            line_num = content[: provider_match.start()].count("\n") + 1

            facts.append(
                RawComponent(
                    name=class_name,
                    component_type="auth_provider",
                    file_path=file_path,
                    description="Custom authentication provider",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 30,
                        reason=f"AuthenticationProvider implementation: {class_name}",
                    ),
                )
            )

        # UserDetailsService implementations
        uds_match = re.search(r"class\s+(\w+)\s+implements\s+.*UserDetailsService", content)
        if uds_match:
            class_name = uds_match.group(1)
            line_num = content[: uds_match.start()].count("\n") + 1

            facts.append(
                RawComponent(
                    name=class_name,
                    component_type="user_details_service",
                    file_path=file_path,
                    description="User details service for authentication",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 30,
                        reason=f"UserDetailsService implementation: {class_name}",
                    ),
                )
            )

        return facts

    def _extract_filters(self, file_path: Path, content: str) -> list[RawComponent]:
        """Extract security filter implementations."""
        facts = []

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

            facts.append(
                RawComponent(
                    name=class_name,
                    component_type=filter_type,
                    file_path=file_path,
                    description=f"Security filter: {class_name}",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 40,
                        reason=f"OncePerRequestFilter: {class_name}",
                    ),
                )
            )

        return facts

    def _extract_security_properties(self, file_path: Path, content: str) -> list[RawComponent]:
        """Extract security properties from YAML."""
        facts = []

        # OAuth2 config
        if "oauth2:" in content:
            facts.append(
                RawComponent(
                    name="oauth2_config",
                    component_type="security_property",
                    file_path=file_path,
                    description="OAuth2 configuration in application properties",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=1,
                        line_end=50,
                        reason="OAuth2 configuration in YAML",
                    ),
                    tags=["oauth2"],
                )
            )

        # JWT config
        if "jwt:" in content:
            facts.append(
                RawComponent(
                    name="jwt_config",
                    component_type="security_property",
                    file_path=file_path,
                    description="JWT configuration in application properties",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=1,
                        line_end=50,
                        reason="JWT configuration in YAML",
                    ),
                    tags=["jwt"],
                )
            )

        return facts
