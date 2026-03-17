"""
CppInterfaceCollector - Extracts C/C++ public interface facts.

Detects:
- extern "C" functions in headers
- Public API headers in include/ or api/ directories
- gRPC .proto service definitions and RPC methods
- Functions exported with __declspec(dllexport) or __attribute__((visibility("default")))

Output feeds -> interfaces.json
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawInterface

# =============================================================================
# Regex Patterns
# =============================================================================

# extern "C" function declarations
EXTERN_C_FUNCTION = re.compile(
    r'(?:extern\s+"C"\s+)?(?:__declspec\(dllexport\)\s+)?'
    r"(?:const\s+|unsigned\s+|signed\s+)*"
    r"(?:void|int|char|float|double|bool|size_t|\w+)\s*\*?\s+"
    r"(\w+)\s*\([^)]*\)\s*;",
    re.MULTILINE,
)

# extern "C" block detection
EXTERN_C_BLOCK_PATTERN = re.compile(r'extern\s+"C"\s*\{', re.MULTILINE)

# __declspec(dllexport) function
DLLEXPORT_PATTERN = re.compile(
    r"__declspec\s*\(\s*dllexport\s*\)\s+"
    r"(?:const\s+|unsigned\s+|signed\s+)*"
    r"(?:\w+[\w:*&<>\s]*)\s+"
    r"(\w+)\s*\([^)]*\)\s*[;{]",
    re.MULTILINE,
)

# __attribute__((visibility("default"))) function
VISIBILITY_DEFAULT_PATTERN = re.compile(
    r'__attribute__\s*\(\s*\(\s*visibility\s*\(\s*"default"\s*\)\s*\)\s*\)\s+'
    r"(?:const\s+|unsigned\s+|signed\s+)*"
    r"(?:\w+[\w:*&<>\s]*)\s+"
    r"(\w+)\s*\([^)]*\)\s*[;{]",
    re.MULTILINE,
)

# gRPC proto service definition
PROTO_SERVICE_PATTERN = re.compile(
    r"service\s+(\w+)\s*\{",
    re.MULTILINE,
)

# gRPC proto RPC method
PROTO_RPC_PATTERN = re.compile(
    r"rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)",
)

# Public API directories
PUBLIC_API_DIRS = {"include", "api", "public"}


class CppInterfaceCollector(DimensionCollector):
    """
    Extracts C/C++ public interface facts using regex-based heuristics.

    Detection strategy:
    1. Find headers in include/ and api/ directories as public API surfaces
    2. Find .proto files for gRPC service definitions
    3. Find extern "C" exported functions in headers
    4. Find __declspec(dllexport) and visibility("default") exports
    """

    DIMENSION = "cpp_interfaces"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._seen_functions: set[str] = set()

    def collect(self) -> CollectorOutput:
        """Collect C/C++ interface facts."""
        self._log_start()

        # 1. Public API headers in include/ and api/ directories
        self._collect_public_headers()

        # 2. gRPC proto service definitions
        self._collect_proto_services()

        # 3. Exported functions (extern "C", dllexport, visibility)
        self._collect_exported_functions()

        self._log_end()
        return self.output

    def _collect_public_headers(self):
        """Find headers in include/ and api/ directories and treat them as public API surfaces."""
        for api_dir_name in PUBLIC_API_DIRS:
            api_dir = self.repo_path / api_dir_name
            if not api_dir.is_dir():
                continue

            header_files: list[Path] = []
            for pattern in ("*.h", "*.hpp", "*.hxx"):
                header_files.extend(self._find_files(pattern, api_dir))

            if not header_files:
                continue

            logger.info(
                "[CppInterfaceCollector] Found %d public headers in %s/",
                len(header_files),
                api_dir_name,
            )

            for header in header_files:
                rel_path = self._relative_path(header)
                content = self._read_file_content(header)

                # Count declared functions as a measure of API surface
                function_count = len(EXTERN_C_FUNCTION.findall(content))

                interface = RawInterface(
                    name=header.stem,
                    type="public_api",
                    path=rel_path,
                    container_hint=self.container_id,
                )

                interface.metadata["header_file"] = rel_path
                interface.metadata["api_directory"] = api_dir_name
                if function_count > 0:
                    interface.metadata["function_count"] = function_count

                interface.add_evidence(
                    path=rel_path,
                    line_start=1,
                    line_end=min(20, max(1, function_count)),
                    reason=f"Public API header in {api_dir_name}/: {header.name}",
                )

                self.output.add_fact(interface)

    def _collect_proto_services(self):
        """Find .proto files and extract gRPC service definitions."""
        proto_files = self._find_files("*.proto")
        if not proto_files:
            return

        logger.info("[CppInterfaceCollector] Scanning %d .proto files", len(proto_files))

        for proto_file in proto_files:
            content = self._read_file_content(proto_file)
            lines = self._read_file(proto_file)
            rel_path = self._relative_path(proto_file)

            for service_match in PROTO_SERVICE_PATTERN.finditer(content):
                service_name = service_match.group(1)
                service_line = self._find_line_number(lines, f"service {service_name}")

                # Collect RPC methods within this service block
                service_start = service_match.end()
                # Find closing brace for the service block
                brace_depth = 1
                pos = service_start
                while pos < len(content) and brace_depth > 0:
                    if content[pos] == "{":
                        brace_depth += 1
                    elif content[pos] == "}":
                        brace_depth -= 1
                    pos += 1
                service_body = content[service_start:pos]

                rpc_methods = []
                for rpc_match in PROTO_RPC_PATTERN.finditer(service_body):
                    rpc_methods.append({
                        "name": rpc_match.group(1),
                        "request": rpc_match.group(2),
                        "response": rpc_match.group(3),
                    })

                interface = RawInterface(
                    name=service_name,
                    type="grpc_service",
                    container_hint=self.container_id,
                )

                if rpc_methods:
                    interface.metadata["rpc_methods"] = rpc_methods
                    interface.metadata["rpc_count"] = len(rpc_methods)

                interface.add_evidence(
                    path=rel_path,
                    line_start=service_line,
                    line_end=service_line + len(rpc_methods) + 2,
                    reason=f"gRPC service: {service_name} ({len(rpc_methods)} RPCs)",
                )

                self.output.add_fact(interface)

    def _collect_exported_functions(self):
        """Find exported functions via extern C, dllexport, or visibility attributes."""
        header_files: list[Path] = []
        for pattern in ("*.h", "*.hpp", "*.hxx"):
            header_files.extend(self._find_files(pattern))

        if not header_files:
            return

        logger.info(
            "[CppInterfaceCollector] Scanning %d header files for exported functions",
            len(header_files),
        )

        for header in header_files:
            content = self._read_file_content(header)
            rel_path = self._relative_path(header)

            has_extern_c = EXTERN_C_BLOCK_PATTERN.search(content)

            # Detect __declspec(dllexport) functions
            for match in DLLEXPORT_PATTERN.finditer(content):
                func_name = match.group(1)
                if func_name in self._seen_functions:
                    continue
                self._seen_functions.add(func_name)

                line_num = content[: match.start()].count("\n") + 1
                self._add_exported_function(
                    func_name, "public_api", rel_path, line_num, "dllexport"
                )

            # Detect __attribute__((visibility("default"))) functions
            for match in VISIBILITY_DEFAULT_PATTERN.finditer(content):
                func_name = match.group(1)
                if func_name in self._seen_functions:
                    continue
                self._seen_functions.add(func_name)

                line_num = content[: match.start()].count("\n") + 1
                self._add_exported_function(
                    func_name, "public_api", rel_path, line_num, "visibility_default"
                )

            # Detect extern "C" functions (only if file has extern "C" block)
            if has_extern_c:
                for match in EXTERN_C_FUNCTION.finditer(content):
                    func_name = match.group(1)
                    if func_name in self._seen_functions:
                        continue

                    # Skip common non-API names (include guards, macros)
                    if func_name.startswith("_") or func_name.isupper():
                        continue

                    self._seen_functions.add(func_name)

                    line_num = content[: match.start()].count("\n") + 1
                    self._add_exported_function(
                        func_name, "extern_function", rel_path, line_num, "extern_c"
                    )

    def _add_exported_function(
        self,
        func_name: str,
        interface_type: str,
        rel_path: str,
        line_num: int,
        export_mechanism: str,
    ):
        """Create a RawInterface for an exported function."""
        interface = RawInterface(
            name=func_name,
            type=interface_type,
            path=rel_path,
            container_hint=self.container_id,
        )

        interface.metadata["export_mechanism"] = export_mechanism

        interface.add_evidence(
            path=rel_path,
            line_start=line_num,
            line_end=line_num + 2,
            reason=f"Exported function ({export_mechanism}): {func_name}",
        )

        self.output.add_fact(interface)
