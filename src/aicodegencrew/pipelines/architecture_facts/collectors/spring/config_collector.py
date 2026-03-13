"""
SpringConfigCollector - Extracts configuration facts.

Detects:
- @Configuration classes
- @Bean definitions
- application.yml / application.properties in multiple locations:
  - src/main/resources
  - distResources (environment-specific configs)
  - config/ directories
  - Any nested resources directories
- Spring profiles
- Property sources

Output feeds -> infrastructure.json (config components)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawComponent, RawInfraFact


class SpringConfigCollector(DimensionCollector):
    """
    Extracts Spring configuration facts from multiple locations.
    """

    DIMENSION = "spring_config"

    # Patterns
    CONFIGURATION_PATTERN = re.compile(r"@Configuration")
    BEAN_PATTERN = re.compile(r"@Bean")
    CLASS_PATTERN = re.compile(r"^(?:public\s+)?class\s+([A-Z]\w*)", re.MULTILINE)

    # Profile patterns
    PROFILE_PATTERN = re.compile(r'@Profile\s*\(\s*["\']([^"\']+)["\']')
    CONDITIONAL_PATTERN = re.compile(r"@Conditional\w+")

    # Config file search directories (relative to repo root)
    CONFIG_SEARCH_DIRS = [
        "src/main/resources",
        "src/test/resources",
        "distResources",
        "config",
        "configs",
        "configuration",
        "resources",
        "env",
        "environments",
        "profiles",
    ]

    # Skip directories
    SKIP_DIRS = DimensionCollector.SKIP_DIRS | {"generated"}

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Spring configuration facts."""
        self._log_start()

        # Collect @Configuration classes
        self._collect_configuration_classes()

        # Collect application.yml/properties
        self._collect_config_files()

        # Collect profiles
        self._collect_profiles()

        self._log_end()
        return self.output

    def _collect_configuration_classes(self):
        """Collect @Configuration annotated classes (Java and Kotlin)."""
        # Collect Java and Kotlin files
        java_files = self._find_files("*.java")
        kotlin_files = self._find_files("*.kt")
        all_files = java_files + kotlin_files

        for src_file in all_files:
            content = self._read_file_content(src_file)

            if not self.CONFIGURATION_PATTERN.search(content):
                continue

            lines = self._read_file(src_file)
            rel_path = self._relative_path(src_file)

            # Get class name
            class_match = self.CLASS_PATTERN.search(content)
            if not class_match:
                continue

            class_name = class_match.group(1)
            class_line = self._find_line_number(lines, f"class {class_name}")

            # Count @Bean methods
            bean_count = len(self.BEAN_PATTERN.findall(content))

            # Check for profile
            profile_match = self.PROFILE_PATTERN.search(content)
            profile = profile_match.group(1) if profile_match else None

            # Check for conditionals
            has_conditionals = bool(self.CONDITIONAL_PATTERN.search(content))

            config = RawComponent(
                name=class_name,
                stereotype="configuration",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="infrastructure",
            )

            config.metadata["bean_count"] = bean_count
            if profile:
                config.metadata["profile"] = profile
            if has_conditionals:
                config.metadata["conditional"] = True

            config.add_evidence(
                path=rel_path,
                line_start=max(1, class_line - 1),
                line_end=class_line + 5,
                reason=f"@Configuration: {class_name} ({bean_count} beans)",
            )

            self.output.add_fact(config)

    def _collect_config_files(self):
        """Collect application.yml/properties files from ALL possible locations."""
        config_patterns = [
            "application.yml",
            "application.yaml",
            "application.properties",
            "application-*.yml",
            "application-*.yaml",
            "application-*.properties",
            "bootstrap.yml",
            "bootstrap.yaml",
            "bootstrap-*.yml",
            "bootstrap-*.yaml",
        ]

        found_files: set[Path] = set()

        # Strategy 1: Search in known config directories (direct paths, no rglob)
        for config_dir in self.CONFIG_SEARCH_DIRS:
            search_path = self.repo_path / config_dir
            if not search_path.is_dir():
                continue

            for pattern in config_patterns:
                for config_file in search_path.glob(pattern):
                    found_files.add(config_file)

            # Also check subdirectories (e.g., distResources/dev/, distResources/prod/)
            for subdir in search_path.iterdir():
                if subdir.is_dir() and not self._should_skip_path(subdir):
                    for pattern in config_patterns:
                        for config_file in subdir.glob(pattern):
                            found_files.add(config_file)

        # Strategy 2: Global recursive search for any config files (with SKIP_DIRS pruning)
        for pattern in config_patterns:
            for config_file in self._find_files(pattern):
                found_files.add(config_file)

        logger.info(f"[SpringConfigCollector] Found {len(found_files)} config files")

        # Process all found files
        for config_file in sorted(found_files):
            self._process_config_file(config_file)

    def _should_skip_path(self, path: Path) -> bool:
        """Check if path should be skipped (path-component matching, not substring)."""
        return bool(set(p.lower() for p in path.parts) & self.SKIP_DIRS)

    def _process_config_file(self, config_file: Path):
        """Process a single config file."""
        rel_path = self._relative_path(config_file)

        # Determine profile from filename
        profile = None
        if "-" in config_file.stem:
            parts = config_file.stem.split("-", 1)
            if len(parts) > 1 and parts[0] in ("application", "bootstrap"):
                profile = parts[1]

        # Determine environment from path (e.g., distResources/dev/ -> dev)
        environment = None
        path_parts = rel_path.replace("\\", "/").split("/")
        for part in path_parts:
            if part.lower() in (
                "dev",
                "test",
                "stage",
                "staging",
                "prod",
                "production",
                "local",
                "docker",
                "kubernetes",
                "k8s",
                "integration",
                "qa",
            ):
                environment = part.lower()
                break

        config = RawInfraFact(
            name=config_file.name,
            type="config_file",
            category="configuration",
        )

        # Set metadata
        config.metadata["path"] = rel_path
        if profile:
            config.metadata["profile"] = profile
        if environment:
            config.metadata["environment"] = environment

        # Extract some key properties
        content = self._read_file_content(config_file)
        config.metadata["size_lines"] = content.count("\n")

        # Look for common properties
        props_found = []
        if "spring.datasource" in content:
            props_found.append("datasource")
        if "spring.jpa" in content:
            props_found.append("jpa")
        if "spring.security" in content:
            props_found.append("security")
        if "spring.kafka" in content or "spring.rabbitmq" in content:
            props_found.append("messaging")
        if "spring.cloud" in content:
            props_found.append("cloud")
        if "oracle" in content.lower():
            props_found.append("oracle")
        if "server.port" in content:
            props_found.append("server")

        if props_found:
            config.metadata["configures"] = props_found

        config.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(20, content.count("\n")),
            reason=f"Spring config: {config_file.name}"
            + (f" (env: {environment})" if environment else "")
            + (f" (profile: {profile})" if profile else ""),
        )

        self.output.add_fact(config)
        logger.debug(f"[SpringConfigCollector] Processed: {rel_path}")

    def _collect_profiles(self):
        """Collect Spring profiles from config files and annotations."""
        profiles_found: set[str] = set()
        environments_found: set[str] = set()

        # From application-{profile}.yml files (recursive search)
        for pattern in [
            "application-*.yml",
            "application-*.yaml",
            "application-*.properties",
            "bootstrap-*.yml",
            "bootstrap-*.yaml",
        ]:
            for f in self._find_files(pattern):
                parts = f.stem.split("-", 1)
                if len(parts) > 1:
                    profiles_found.add(parts[1])

        # From @Profile annotations
        for java_file in self._find_files("*.java"):
            content = self._read_file_content(java_file)
            for match in self.PROFILE_PATTERN.finditer(content):
                profiles_found.add(match.group(1))

        # From directory names (e.g., distResources/dev/, environments/prod/)
        env_dir_names = {
            "dev",
            "test",
            "stage",
            "staging",
            "prod",
            "production",
            "local",
            "docker",
            "kubernetes",
            "k8s",
            "integration",
            "qa",
        }
        for config_dir in self.CONFIG_SEARCH_DIRS:
            search_path = self.repo_path / config_dir
            if not search_path.is_dir():
                continue
            for subdir in search_path.iterdir():
                if subdir.is_dir() and subdir.name.lower() in env_dir_names:
                    environments_found.add(subdir.name.lower())

        # Create profile facts
        for profile in profiles_found:
            profile_fact = RawInfraFact(
                name=f"profile-{profile}",
                type="spring_profile",
                category="configuration",
                metadata={"profile_name": profile},
            )
            profile_fact.tags.append(f"profile:{profile}")
            self.output.add_fact(profile_fact)
            logger.info(f"[SpringConfigCollector] Found profile: {profile}")

        # Create environment facts
        for env in environments_found:
            env_fact = RawInfraFact(
                name=f"environment-{env}",
                type="environment",
                category="configuration",
                metadata={"environment_name": env},
            )
            env_fact.tags.append(f"env:{env}")
            self.output.add_fact(env_fact)
            logger.info(f"[SpringConfigCollector] Found environment: {env}")
