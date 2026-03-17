"""
CppComponentCollector - Extracts C/C++ component facts.

Detects:
- Classes with public methods in .hpp/.cpp/.h/.cc/.cxx/.hxx files
- Namespace-level groupings
- Naming conventions: *_service, *_handler, *_manager, *_controller
- CMake library targets (add_library)
- C structs used as major data types

Output feeds -> components.json
             -> relations (namespace groupings)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawComponent

# =============================================================================
# Regex Patterns
# =============================================================================

# C++ class declaration (with optional template and declspec)
CPP_CLASS_PATTERN = re.compile(
    r"^\s*(?:template\s*<[^>]*>\s*)?class\s+(?:__declspec\(\w+\)\s+)?(\w+)"
    r"(?:\s*:\s*(?:public|protected|private)\s+\w+)?",
    re.MULTILINE,
)

# Public method heuristic: lines inside public sections that look like method declarations
PUBLIC_METHOD_PATTERN = re.compile(
    r"^\s*(?:virtual\s+|static\s+|inline\s+)?(?:\w+[\w:*&<>\s]*)\s+(\w+)\s*\([^)]*\)"
    r"\s*(?:const\s*)?(?:override\s*)?(?:=\s*0\s*)?;",
    re.MULTILINE,
)

# Namespace detection
NAMESPACE_PATTERN = re.compile(r"^\s*namespace\s+(\w+)\s*\{", re.MULTILINE)

# C struct as component (for C projects)
C_STRUCT_PATTERN = re.compile(r"^\s*(?:typedef\s+)?struct\s+(\w+)\s*\{", re.MULTILINE)

# CMake add_library target
CMAKE_LIBRARY_PATTERN = re.compile(
    r"add_library\s*\(\s*(\w+)\s+(?:STATIC|SHARED|MODULE|OBJECT|INTERFACE)?\s*",
    re.MULTILINE,
)

# Filename-based stereotype patterns
STEREOTYPE_FILENAME_PATTERNS = {
    "service": re.compile(r"service", re.IGNORECASE),
    "handler": re.compile(r"handler", re.IGNORECASE),
    "manager": re.compile(r"manager", re.IGNORECASE),
    "controller": re.compile(r"controller", re.IGNORECASE),
}

# C/C++ source and header extensions
CPP_SOURCE_PATTERNS = ["*.cpp", "*.cc", "*.cxx"]
CPP_HEADER_PATTERNS = ["*.hpp", "*.h", "*.hxx"]
ALL_CPP_PATTERNS = CPP_HEADER_PATTERNS + CPP_SOURCE_PATTERNS


class CppComponentCollector(DimensionCollector):
    """
    Extracts C/C++ component facts using regex-based heuristics.

    Detection strategy:
    1. Scan header and source files for class declarations
    2. Count public methods to determine significance (>2 = component)
    3. Classify by filename convention (service, handler, manager, controller)
    4. Detect CMake library targets as library-level components
    5. Detect C structs in C-style codebases
    """

    DIMENSION = "cpp_components"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._seen_classes: set[str] = set()

    def collect(self) -> CollectorOutput:
        """Collect C/C++ component facts."""
        self._log_start()

        # Gather all C/C++ files
        all_files: list[Path] = []
        for pattern in ALL_CPP_PATTERNS:
            all_files.extend(self._find_files(pattern))

        if not all_files:
            logger.debug(
                "[CppComponentCollector] No C/C++ source files found in %s (skipping)",
                self.repo_path,
            )
            return self.output

        logger.info("[CppComponentCollector] Scanning %d C/C++ files", len(all_files))

        # Pass 1: Extract classes and structs from source/header files
        for source_file in all_files:
            self._process_source_file(source_file)

        # Pass 2: Detect library targets from CMakeLists.txt
        cmake_files = self._find_files("CMakeLists.txt")
        for cmake_file in cmake_files:
            self._process_cmake_file(cmake_file)

        self._log_end()
        return self.output

    def _process_source_file(self, file_path: Path):
        """Process a single C/C++ file for class and struct components."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)
        stem_lower = file_path.stem.lower()

        # Detect namespace context for module derivation
        namespace = self._extract_namespace(content)

        # Detect classes
        for match in CPP_CLASS_PATTERN.finditer(content):
            class_name = match.group(1)

            # Skip forward declarations (no opening brace nearby)
            match_end = match.end()
            lookahead = content[match_end : match_end + 50]
            if "{" not in lookahead and ";" in lookahead:
                continue

            # Skip duplicates (same class seen in header and source)
            if class_name in self._seen_classes:
                continue
            self._seen_classes.add(class_name)

            # Count public methods as significance heuristic
            public_method_count = self._count_public_methods(content, class_name)
            if public_method_count <= 2:
                continue

            # Determine stereotype from filename
            stereotype = self._classify_stereotype(stem_lower, class_name)

            # Determine line number
            class_line = self._find_line_number(lines, f"class {class_name}")

            component = RawComponent(
                name=class_name,
                stereotype=stereotype,
                container_hint=self.container_id,
                module=namespace,
                file_path=rel_path,
                layer_hint=self._infer_layer(stereotype),
            )

            component.metadata["public_methods"] = public_method_count
            if namespace:
                component.metadata["namespace"] = namespace

            component.add_evidence(
                path=rel_path,
                line_start=max(1, class_line - 2),
                line_end=class_line + 5,
                reason=f"C++ class: {class_name} ({public_method_count} public methods)",
            )

            self.output.add_fact(component)

        # Detect significant C structs (with multiple fields)
        for match in C_STRUCT_PATTERN.finditer(content):
            struct_name = match.group(1)
            if struct_name in self._seen_classes:
                continue

            # Check that struct has substance (at least a few fields)
            struct_start = match.end()
            brace_depth = 1
            pos = struct_start
            field_count = 0
            while pos < len(content) and brace_depth > 0:
                if content[pos] == "{":
                    brace_depth += 1
                elif content[pos] == "}":
                    brace_depth -= 1
                elif content[pos] == ";" and brace_depth == 1:
                    field_count += 1
                pos += 1

            if field_count < 3:
                continue

            self._seen_classes.add(struct_name)
            struct_line = self._find_line_number(lines, f"struct {struct_name}")

            component = RawComponent(
                name=struct_name,
                stereotype="class",
                container_hint=self.container_id,
                module=namespace,
                file_path=rel_path,
                layer_hint="domain",
            )

            component.metadata["kind"] = "struct"
            component.metadata["field_count"] = field_count

            component.add_evidence(
                path=rel_path,
                line_start=max(1, struct_line - 1),
                line_end=struct_line + 3,
                reason=f"C struct: {struct_name} ({field_count} fields)",
            )

            self.output.add_fact(component)

    def _process_cmake_file(self, file_path: Path):
        """Extract library targets from CMakeLists.txt."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        for match in CMAKE_LIBRARY_PATTERN.finditer(content):
            lib_name = match.group(1)

            if lib_name in self._seen_classes:
                continue
            self._seen_classes.add(lib_name)

            line_num = content[: match.start()].count("\n") + 1

            component = RawComponent(
                name=lib_name,
                stereotype="library",
                container_hint=self.container_id,
                module="",
                file_path=rel_path,
                layer_hint="infrastructure",
            )

            component.metadata["build_system"] = "cmake"

            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 3,
                reason=f"CMake library target: {lib_name}",
            )

            self.output.add_fact(component)

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _extract_namespace(content: str) -> str:
        """Extract the primary namespace from file content."""
        matches = NAMESPACE_PATTERN.findall(content)
        # Filter out anonymous/detail namespaces
        meaningful = [ns for ns in matches if ns not in ("detail", "internal", "anonymous", "")]
        return "::".join(meaningful) if meaningful else ""

    @staticmethod
    def _count_public_methods(content: str, class_name: str) -> int:
        """Count public methods in a class using heuristic regex matching.

        Looks for a 'public:' section and counts method-like declarations
        until the next access specifier or end of class.
        """
        # Find the class body start
        class_pattern = re.compile(
            r"\bclass\s+" + re.escape(class_name) + r"[^{]*\{",
            re.MULTILINE,
        )
        class_match = class_pattern.search(content)
        if not class_match:
            return 0

        class_body_start = class_match.end()

        # Find the public section
        public_pos = content.find("public:", class_body_start)
        if public_pos == -1:
            return 0

        # Determine the end of the public section (next access specifier or class end)
        next_section = len(content)
        for specifier in ("private:", "protected:", "public:"):
            pos = content.find(specifier, public_pos + len("public:"))
            if pos != -1 and pos < next_section:
                next_section = pos

        public_section = content[public_pos:next_section]
        return len(PUBLIC_METHOD_PATTERN.findall(public_section))

    @staticmethod
    def _classify_stereotype(stem_lower: str, class_name: str) -> str:
        """Classify a component by filename or class name convention."""
        check_target = stem_lower + " " + class_name.lower()
        for stereotype, pattern in STEREOTYPE_FILENAME_PATTERNS.items():
            if pattern.search(check_target):
                return stereotype
        return "class"

    @staticmethod
    def _infer_layer(stereotype: str) -> str | None:
        """Infer architectural layer from stereotype."""
        layer_map = {
            "service": "application",
            "handler": "application",
            "manager": "application",
            "controller": "presentation",
            "class": None,
            "library": "infrastructure",
        }
        return layer_map.get(stereotype)
