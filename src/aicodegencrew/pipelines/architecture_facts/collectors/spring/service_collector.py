"""
SpringServiceCollector - Extracts service layer facts.

Detects:
- @Service classes
- Interface + Implementation mappings (UserService -> UserServiceImpl)
- Dependencies between services

Output feeds -> components.json (services)
             -> relations (service dependencies)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawComponent, RelationHint


class SpringServiceCollector(DimensionCollector):
    """
    Extracts service layer facts from Spring Boot code.
    """

    DIMENSION = "spring_services"

    # Patterns
    SERVICE_PATTERN = re.compile(r"@Service")
    CLASS_PATTERN = re.compile(r"^(?:public\s+)?(?:abstract\s+)?class\s+([A-Z]\w*)", re.MULTILINE)
    INTERFACE_PATTERN = re.compile(r"^(?:public\s+)?interface\s+([A-Z]\w*)", re.MULTILINE)
    IMPLEMENTS_PATTERN = re.compile(r"class\s+(\w+)\s+implements\s+(\w+(?:\s*,\s*\w+)*)")

    # Constructor injection
    CONSTRUCTOR_PARAM_PATTERN = re.compile(r"(?:private|protected)\s+(?:final\s+)?(\w+)\s+(\w+)\s*[;,)]")

    # Field injection (@Autowired or @Inject on fields)
    FIELD_INJECTION_PATTERN = re.compile(
        r"@(?:Autowired|Inject)\s+(?:private|protected)\s+(?:final\s+)?(\w+)\s+(\w+)\s*;"
    )

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._java_root: Path | None = None
        self._service_names: set[str] = set()
        self._interface_to_impl: dict[str, str] = {}

    def collect(self) -> CollectorOutput:
        """Collect service layer facts."""
        self._log_start()

        self._java_root = self._find_java_root()
        if not self._java_root:
            logger.debug("[SpringServiceCollector] No Java/Kotlin source root in %s (skipping)", self.repo_path)
            return self.output

        # Collect Java and Kotlin files
        java_files = self._find_files("*.java", self._java_root)
        kotlin_files = self._find_files("*.kt", self._java_root)
        all_files = java_files + kotlin_files

        # First pass: identify all interfaces and services
        for src_file in all_files:
            self._identify_service(src_file)

        # Second pass: extract dependencies
        for src_file in all_files:
            self._extract_dependencies(src_file)

        self._log_end()
        return self.output

    def _find_java_root(self) -> Path | None:
        """Find Java/Kotlin source root."""
        candidates = [
            self.repo_path / "src" / "main" / "java",
            self.repo_path / "src" / "main" / "kotlin",
            self.repo_path / "backend" / "src" / "main" / "java",
            self.repo_path / "backend" / "src" / "main" / "kotlin",
        ]
        for c in candidates:
            if c.exists():
                return c

        for path in self._find_files("src"):
            java_path = path.parent / "main" / "java"
            if java_path.is_dir():
                return java_path
        return None

    def _identify_service(self, file_path: Path):
        """Identify services and interface mappings."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        # Check for @Service
        if not self.SERVICE_PATTERN.search(content):
            # Might still be a service interface
            if self.INTERFACE_PATTERN.search(content) and "Service" in file_path.stem:
                interface_match = self.INTERFACE_PATTERN.search(content)
                if interface_match:
                    interface_name = interface_match.group(1)
                    # Don't create component for interface, just track it
                    self._service_names.add(interface_name)
            return

        # Get class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return

        class_name = class_match.group(1)
        class_line = self._find_line_number(lines, f"class {class_name}")

        self._service_names.add(class_name)

        # Check for interface implementation
        impl_match = self.IMPLEMENTS_PATTERN.search(content)
        if impl_match:
            impl_class = impl_match.group(1)
            interfaces = [i.strip() for i in impl_match.group(2).split(",")]
            for iface in interfaces:
                if "Service" in iface:
                    self._interface_to_impl[iface] = impl_class

        # Create service component
        service = RawComponent(
            name=class_name,
            stereotype="service",
            container_hint=self.container_id,
            module=self._derive_module(rel_path),
            file_path=rel_path,
            layer_hint="application",
        )

        service.add_evidence(
            path=rel_path, line_start=class_line - 1, line_end=class_line + 3, reason=f"@Service: {class_name}"
        )

        # Add interface info if present
        if impl_match:
            service.metadata["implements"] = interfaces

        self.output.add_fact(service)

    def _extract_dependencies(self, file_path: Path):
        """Extract service dependencies via constructor injection."""
        content = self._read_file_content(file_path)
        self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        # Get class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return

        class_name = class_match.group(1)

        # Only process if it's a known service
        if class_name not in self._service_names:
            return

        # Find constructor injected dependencies
        for match in self.CONSTRUCTOR_PARAM_PATTERN.finditer(content):
            dep_type = match.group(1)
            match.group(2)

            # Check if dependency is a known service
            actual_impl = self._interface_to_impl.get(dep_type, dep_type)

            if actual_impl in self._service_names or dep_type in self._service_names:
                line_num = content[: match.start()].count("\n") + 1

                relation = RelationHint(
                    from_name=class_name,
                    to_name=dep_type,
                    type="uses",
                    from_stereotype_hint="service",
                    to_stereotype_hint="service",
                    from_file_hint=str(rel_path),
                )

                relation.evidence.append(
                    self._create_evidence(
                        file_path, line_num, line_num + 1, f"Constructor injection: {class_name} -> {dep_type}"
                    )
                )

                self.output.add_relation(relation)

        # Also detect field injection (@Autowired / @Inject)
        for match in self.FIELD_INJECTION_PATTERN.finditer(content):
            dep_type = match.group(1)
            match.group(2)

            actual_impl = self._interface_to_impl.get(dep_type, dep_type)

            if actual_impl in self._service_names or dep_type in self._service_names:
                line_num = content[: match.start()].count("\n") + 1

                relation = RelationHint(
                    from_name=class_name,
                    to_name=dep_type,
                    type="uses",
                    from_stereotype_hint="service",
                    to_stereotype_hint="service",
                    from_file_hint=str(rel_path),
                )

                relation.evidence.append(
                    self._create_evidence(
                        file_path, line_num, line_num + 1, f"Field injection: {class_name} -> {dep_type}"
                    )
                )

                self.output.add_relation(relation)
