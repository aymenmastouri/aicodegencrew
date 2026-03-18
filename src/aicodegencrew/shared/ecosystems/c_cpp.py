"""C/C++ Ecosystem — CMake, Make, Autotools, Meson, Conan, vcpkg."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ._utils import count_line, find_block_end
from .base import CollectorContext, EcosystemDefinition, MarkerFile

# ── Regex patterns ──────────────────────────────────────────────────────────

_C_FUNCTION = re.compile(
    r"^\s*(?:static\s+|inline\s+|extern\s+|const\s+)*"
    r"(?:unsigned\s+|signed\s+|long\s+|short\s+)*"
    r"(?:void|int|char|float|double|long|short|unsigned|signed|bool|size_t|ssize_t|uint\d+_t|int\d+_t|\w+_t|\w+)\s*\*?\s+"
    r"(\w+)\s*\([^)]*\)\s*\{",
    re.MULTILINE,
)
_C_STRUCT = re.compile(r"^\s*(?:typedef\s+)?struct\s+(\w+)\s*\{", re.MULTILINE)
_C_UNION = re.compile(r"^\s*(?:typedef\s+)?union\s+(\w+)\s*\{", re.MULTILINE)
_C_ENUM = re.compile(r"^\s*(?:typedef\s+)?enum\s+(?:class\s+)?(\w+)\s*\{", re.MULTILINE)
_C_TYPEDEF = re.compile(r"^\s*typedef\s+.+?\s+(\w+)\s*;", re.MULTILINE)
_C_MACRO = re.compile(r"^\s*#\s*define\s+(\w+)(?:\s*\(|\s+)", re.MULTILINE)

_CPP_CLASS = re.compile(
    r"^\s*(?:template\s*<[^>]*>\s*)?class\s+(\w+)(?:\s*:\s*(?:public|protected|private)\s+\w+)?",
    re.MULTILINE,
)
_CPP_NAMESPACE = re.compile(r"^\s*namespace\s+(\w+)", re.MULTILINE)
_CPP_METHOD = re.compile(
    r"^\s*(?:virtual\s+|static\s+|inline\s+|explicit\s+|const\s+)*"
    r"(?:\w+(?:::\w+)*\s*\*?\s+)"
    r"(\w+)\s*::\s*(\w+)\s*\(",
    re.MULTILINE,
)

_C_KEYWORD_SKIP = {"if", "for", "while", "switch", "return", "sizeof", "typeof", "alignof"}


class CCppEcosystem(EcosystemDefinition):
    """C/C++ ecosystem: CMake, Make, Autotools, Meson, Conan, vcpkg."""

    @property
    def id(self) -> str:
        return "c_cpp"

    @property
    def name(self) -> str:
        return "C/C++"

    @property
    def priority(self) -> int:
        return 30

    @property
    def source_extensions(self) -> set[str]:
        return {".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"}

    @property
    def exclude_extensions(self) -> set[str]:
        return {".o", ".obj", ".a", ".lib", ".so", ".dll", ".dylib", ".exe"}

    @property
    def skip_directories(self) -> set[str]:
        return {"build", "cmake-build-debug", "cmake-build-release"}

    @property
    def marker_files(self) -> list[MarkerFile]:
        return [
            MarkerFile("CMakeLists.txt", "C/C++ (CMake)"),
            MarkerFile("Makefile", "C/C++ (Make)"),
            MarkerFile("configure.ac", "C/C++ (Autotools)"),
            MarkerFile("configure.in", "C/C++ (Autotools)"),
            MarkerFile("meson.build", "C/C++ (Meson)"),
            MarkerFile("SConstruct", "C/C++ (SCons)"),
            MarkerFile("conanfile.txt", "C/C++ (Conan)"),
            MarkerFile("conanfile.py", "C/C++ (Conan)"),
            MarkerFile("vcpkg.json", "C/C++ (vcpkg)"),
        ]

    @property
    def ext_to_lang(self) -> dict[str, str]:
        return {
            ".c": "c", ".h": "c",
            ".cpp": "cpp", ".hpp": "cpp",
            ".cc": "cpp", ".hh": "cpp",
            ".cxx": "cpp", ".hxx": "cpp",
        }

    # ── Symbol Extraction ───────────────────────────────────────────────────

    def extract_symbols(self, path, content, lines, lang, module):
        records = []

        # C++ classes (only for C++ files)
        if lang == "cpp":
            for m in _CPP_CLASS.finditer(content):
                line_no = count_line(content, m.start())
                end_line = find_block_end(lines, line_no - 1)
                records.append(dict(
                    symbol=m.group(1), kind="class", path=path,
                    line=line_no, end_line=end_line, language=lang, module=module,
                ))

            # Namespaces
            for m in _CPP_NAMESPACE.finditer(content):
                name = m.group(1)
                if name in ("std", "detail", "internal"):
                    continue
                line_no = count_line(content, m.start())
                records.append(dict(
                    symbol=name, kind="namespace", path=path,
                    line=line_no, end_line=0, language=lang, module=module,
                ))

        # Structs
        for m in _C_STRUCT.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="struct", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Unions
        for m in _C_UNION.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="union", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Enums
        for m in _C_ENUM.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="enum", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Functions (C and C++)
        for m in _C_FUNCTION.finditer(content):
            name = m.group(1)
            if name in _C_KEYWORD_SKIP:
                continue
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            # Skip if already captured as struct/union/enum name on same line
            if any(r["symbol"] == name and r["line"] == line_no for r in records):
                continue
            records.append(dict(
                symbol=name, kind="function", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Macros (only significant ones)
        for m in _C_MACRO.finditer(content):
            name = m.group(1)
            if name.startswith("_") or name.endswith("_H") or name.endswith("_H_") or name.endswith("_HPP"):
                continue
            line_no = count_line(content, m.start())
            records.append(dict(
                symbol=name, kind="macro", path=path,
                line=line_no, end_line=0, language=lang, module=module,
            ))

        # Typedefs (not already captured by struct/union/enum typedef)
        already_captured = {r["symbol"] for r in records}
        for m in _C_TYPEDEF.finditer(content):
            name = m.group(1)
            if name in already_captured:
                continue
            line_no = count_line(content, m.start())
            records.append(dict(
                symbol=name, kind="typedef", path=path,
                line=line_no, end_line=0, language=lang, module=module,
            ))

        return records

    # ── Container Detection ─────────────────────────────────────────────────

    def detect_container(self, dir_path, name, ctx):
        # Check in priority order: CMake, Makefile, Meson, Autotools
        cmake_lists = dir_path / "CMakeLists.txt"
        if cmake_lists.exists():
            return self._detect_cmake_container(cmake_lists, name, ctx)

        makefile = dir_path / "Makefile"
        if makefile.exists():
            return self._detect_make_container(makefile, name, ctx)

        meson_build = dir_path / "meson.build"
        if meson_build.exists():
            return self._detect_meson_container(meson_build, name, ctx)

        configure_ac = dir_path / "configure.ac"
        if not configure_ac.exists():
            configure_ac = dir_path / "configure.in"
        if configure_ac.exists():
            return self._detect_autotools_container(configure_ac, name, ctx)

        return None

    def _detect_cmake_container(self, cmake_path, name, ctx):
        content = ctx.read_file_content(cmake_path)
        lines = ctx.read_file_lines(cmake_path)

        has_executable = bool(re.search(r"add_executable\s*\(", content))
        has_library = bool(re.search(r"add_library\s*\(", content))

        is_cpp = bool(re.search(r"(?:CXX|c\+\+|cpp)", content, re.IGNORECASE))
        language = "C++" if is_cpp else "C"

        framework_hints = []
        for pkg, label in [
            ("Qt", "Qt"), ("Boost", "Boost"), ("OpenCV", "OpenCV"),
            ("GTest|GoogleTest", "GoogleTest"), ("OpenSSL", "OpenSSL"),
            ("CURL", "libcurl"), ("Protobuf|gRPC", "gRPC/Protobuf"),
            ("SDL2", "SDL2"), ("OpenGL|GLEW", "OpenGL"),
        ]:
            if re.search(rf"find_package\s*\(\s*(?:{pkg})", content):
                framework_hints.append(label)

        technology = f"{language}/CMake"
        if framework_hints:
            technology += f" ({', '.join(framework_hints[:3])})"

        container_type = "backend" if has_executable else "library"
        if ctx.is_test_directory(name):
            container_type = "test"

        project_line = ctx.find_line_number(lines, "project") or 1
        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(cmake_path.parent),
            "category": "application" if has_executable else "library",
            "metadata": {
                "build_system": "cmake",
                "has_executable": has_executable,
                "has_library": has_library,
                "frameworks": framework_hints,
            },
            "evidence": [{
                "path": ctx.relative_path(cmake_path),
                "line_start": project_line,
                "line_end": project_line + 10,
                "reason": f"{technology} project: {name}",
            }],
        }

    def _detect_make_container(self, makefile_path, name, ctx):
        content = ctx.read_file_content(makefile_path)

        is_cpp = bool(re.search(r"(?:CXX|g\+\+|clang\+\+|\.cpp|\.cxx|\.cc)", content))
        language = "C++" if is_cpp else "C"

        has_executable = bool(
            re.search(r"^\w+\s*:.*\$\(CC\)|\$\(CXX\)|gcc|g\+\+|clang", content, re.MULTILINE)
        )

        container_type = "backend" if has_executable else "library"
        if ctx.is_test_directory(name):
            container_type = "test"

        technology = f"{language}/Make"
        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(makefile_path.parent),
            "category": "application" if has_executable else "library",
            "metadata": {"build_system": "make"},
            "evidence": [{
                "path": ctx.relative_path(makefile_path),
                "line_start": 1,
                "line_end": 20,
                "reason": f"{technology} project: {name}",
            }],
        }

    def _detect_meson_container(self, meson_path, name, ctx):
        content = ctx.read_file_content(meson_path)
        lines = ctx.read_file_lines(meson_path)

        is_cpp = bool(re.search(r"'cpp'|\"cpp\"", content))
        language = "C++" if is_cpp else "C"

        has_executable = bool(re.search(r"executable\s*\(", content))
        has_library = bool(re.search(r"(?:shared_library|static_library|library)\s*\(", content))

        container_type = "backend" if has_executable else "library"
        if ctx.is_test_directory(name):
            container_type = "test"

        technology = f"{language}/Meson"
        project_line = ctx.find_line_number(lines, "project") or 1
        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(meson_path.parent),
            "category": "application" if has_executable else "library",
            "metadata": {
                "build_system": "meson",
                "has_executable": has_executable,
                "has_library": has_library,
            },
            "evidence": [{
                "path": ctx.relative_path(meson_path),
                "line_start": project_line,
                "line_end": project_line + 10,
                "reason": f"{technology} project: {name}",
            }],
        }

    def _detect_autotools_container(self, configure_path, name, ctx):
        content = ctx.read_file_content(configure_path)
        lines = ctx.read_file_lines(configure_path)

        is_cpp = bool(re.search(r"AC_PROG_CXX|AC_LANG\(\[C\+\+\]\)", content))
        language = "C++" if is_cpp else "C"

        container_type = "backend"
        if ctx.is_test_directory(name):
            container_type = "test"

        technology = f"{language}/Autotools"
        init_line = ctx.find_line_number(lines, "AC_INIT") or 1
        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(configure_path.parent),
            "category": "application",
            "metadata": {"build_system": "autotools"},
            "evidence": [{
                "path": ctx.relative_path(configure_path),
                "line_start": init_line,
                "line_end": init_line + 10,
                "reason": f"{technology} project: {name}",
            }],
        }

    # ── Version Collection ──────────────────────────────────────────────────

    def collect_versions(self, ctx):
        self._collect_cmake_versions(ctx)
        self._collect_makefile_versions(ctx)

    def _collect_cmake_versions(self, ctx):
        for cmake_file in ctx.find_files("CMakeLists.txt"):
            self._parse_cmake_file(cmake_file, ctx)
        for conan_file in ctx.find_files("conanfile.txt"):
            self._parse_conan_file(conan_file, ctx)
        for vcpkg_file in ctx.find_files("vcpkg.json"):
            self._parse_vcpkg_file(vcpkg_file, ctx)

    def _parse_cmake_file(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)

            cmake_ver = re.search(
                r"cmake_minimum_required\s*\(\s*VERSION\s+([0-9.]+)", content, re.IGNORECASE
            )
            if cmake_ver:
                ctx.add_version("CMake", cmake_ver.group(1), rel_path, "build_tool")

            c_std = re.search(r"CMAKE_C_STANDARD\s+(\d+)", content)
            if c_std:
                ctx.add_version("C Standard", f"C{c_std.group(1)}", rel_path, "language")

            cxx_std = re.search(r"CMAKE_CXX_STANDARD\s+(\d+)", content)
            if cxx_std:
                ctx.add_version("C++ Standard", f"C++{cxx_std.group(1)}", rel_path, "language")

            proj_ver = re.search(r"project\s*\([^)]*VERSION\s+([0-9.]+)", content, re.IGNORECASE)
            if proj_ver:
                ctx.add_version("Project", proj_ver.group(1), rel_path, "project")

            lib_patterns = {
                "Qt": ("Qt", "framework"),
                "Boost": ("Boost", "framework"),
                "OpenCV": ("OpenCV", "framework"),
                "GTest": ("GoogleTest", "library"),
                "GoogleTest": ("GoogleTest", "library"),
                "Protobuf": ("Protobuf", "library"),
                "gRPC": ("gRPC", "library"),
                "OpenSSL": ("OpenSSL", "library"),
                "CURL": ("libcurl", "library"),
                "SDL2": ("SDL2", "library"),
            }
            for pkg, (tech, category) in lib_patterns.items():
                pkg_match = re.search(rf"find_package\s*\(\s*{pkg}\s+([0-9.]+)", content)
                if pkg_match:
                    ctx.add_version(tech, pkg_match.group(1), rel_path, category)
        except Exception:
            pass

    def _parse_conan_file(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)

            in_requires = False
            for line in content.splitlines():
                line = line.strip()
                if line == "[requires]":
                    in_requires = True
                    continue
                if line.startswith("[") and line.endswith("]"):
                    in_requires = False
                    continue
                if in_requires and "/" in line:
                    parts = line.split("/", 1)
                    if len(parts) == 2:
                        lib_name = parts[0].strip()
                        lib_version = parts[1].strip().split("@")[0].strip()
                        if lib_version:
                            ctx.add_version(lib_name, lib_version, rel_path, "library")
        except Exception:
            pass

    def _parse_vcpkg_file(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8")
            pkg = json.loads(content)
            rel_path = ctx.relative_path(file_path)

            for dep in pkg.get("dependencies", []):
                if isinstance(dep, dict):
                    dep_name = dep.get("name", "")
                    dep_version = dep.get("version>=", dep.get("version", ""))
                    if dep_name and dep_version:
                        ctx.add_version(dep_name, str(dep_version), rel_path, "library")

            for override in pkg.get("overrides", []):
                if isinstance(override, dict):
                    dep_name = override.get("name", "")
                    dep_version = override.get("version", "")
                    if dep_name and dep_version:
                        ctx.add_version(dep_name, str(dep_version), rel_path, "library")
        except Exception:
            pass

    # ── Dimension Delegation ──────────────────────────────────────────────

    def collect_dimension(self, dimension, repo_path, container_id=""):
        dispatch = {
            "build_system": self._collect_build_system,
            "dependencies": self._collect_dependencies,
            "tests": self._collect_tests,
            "workflows": self._collect_workflows,
            "configuration": self._collect_configuration,
            "logging_observability": self._collect_logging,
            "communication_patterns": self._collect_communication,
        }
        handler = dispatch.get(dimension)
        return handler(repo_path, container_id) if handler else ([], [])

    def _collect_build_system(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.build_system_collector import CppBuildSystemCollector
        output = CppBuildSystemCollector(repo_path).collect()
        return output.facts, output.relations

    def _collect_dependencies(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.dependency_collector import CppDependencyCollector
        output = CppDependencyCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_tests(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.test_collector import CppTestCollector
        output = CppTestCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_workflows(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.workflow_collector import CppWorkflowCollector
        output = CppWorkflowCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_configuration(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.configuration_collector import CppConfigurationCollector
        output = CppConfigurationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_logging(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.logging_collector import CppLoggingCollector
        output = CppLoggingCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_communication(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.cpp.communication_collector import CppCommunicationCollector
        output = CppCommunicationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    # ── Component Technologies ──────────────────────────────────────────────

    def get_component_technologies(self) -> set[str]:
        return {
            "C/C++", "C/C++ (CMake)", "C++/CMake", "C/CMake",
            "C++/Make", "C/Make", "C++/Meson", "C/Meson",
            "C++/Autotools", "C/Autotools",
        }

    # ── Component Collection ───────────────────────────────────────────────

    def collect_components(self, container, repo_path):
        # Lazy import to avoid circular dependency
        from ...pipelines.architecture_facts.collectors.cpp import (
            CppComponentCollector,
            CppInterfaceCollector,
        )

        root_path = container.get("root_path", "")
        container_root = repo_path / root_path if root_path and root_path != "." else repo_path
        container_name = container.get("name", "backend")

        facts = []
        relations = []
        for CollectorClass in [CppComponentCollector, CppInterfaceCollector]:
            collector = CollectorClass(container_root, container_id=container_name)
            output = collector.collect()
            facts.extend(output.facts)
            relations.extend(output.relations)
        return facts, relations

    def _collect_makefile_versions(self, ctx):
        for makefile in ctx.find_files("Makefile"):
            try:
                content = makefile.read_text(encoding="utf-8", errors="ignore")
                rel_path = ctx.relative_path(makefile)

                std_match = re.search(r"-std=(c\+\+\d+|gnu\+\+\d+|c\d+|gnu\d+)", content)
                if std_match:
                    std_val = std_match.group(1)
                    if "c++" in std_val or "gnu++" in std_val:
                        version = std_val.replace("gnu++", "C++").replace("c++", "C++")
                        ctx.add_version("C++ Standard", version, rel_path, "language")
                    else:
                        version = std_val.replace("gnu", "C").replace("c", "C")
                        ctx.add_version("C Standard", version, rel_path, "language")
            except Exception:
                pass
