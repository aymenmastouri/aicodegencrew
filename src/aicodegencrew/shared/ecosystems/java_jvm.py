"""Java/JVM Ecosystem — Spring, Maven, Gradle, Kotlin."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from ._utils import count_line, find_block_end
from .base import CollectorContext, EcosystemDefinition, MarkerFile

# ── Regex patterns ──────────────────────────────────────────────────────────

_JAVA_CLASS = re.compile(
    r"^\s*(?:public\s+|protected\s+|private\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+(\w+)",
    re.MULTILINE,
)
_JAVA_METHOD = re.compile(
    r"^\s*(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
    r"(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\(",
    re.MULTILINE,
)
_JAVA_ANNOTATION = re.compile(r"^\s*@(\w+(?:\.\w+)?)", re.MULTILINE)

_SPRING_ENDPOINTS = re.compile(
    r"@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"",
    re.MULTILINE,
)

_SPRING_ANNOTS = {
    "RestController", "Controller", "Service", "Repository",
    "Component", "Configuration", "Entity",
}

_JAVA_KEYWORD_SKIP = {"if", "for", "while", "switch", "catch", "return"}


class JavaJvmEcosystem(EcosystemDefinition):
    """Java/JVM ecosystem: Spring Boot, Maven, Gradle, Kotlin."""

    @property
    def id(self) -> str:
        return "java_jvm"

    @property
    def name(self) -> str:
        return "Java/JVM"

    @property
    def priority(self) -> int:
        return 10

    @property
    def source_extensions(self) -> set[str]:
        return {".java", ".kt", ".kts"}

    @property
    def exclude_extensions(self) -> set[str]:
        return {".class", ".jar", ".war", ".ear"}

    @property
    def config_extensions(self) -> set[str]:
        return {".properties", ".xml"}

    @property
    def skip_directories(self) -> set[str]:
        return {"target", ".gradle", ".mvn", "buildSrc"}

    @property
    def marker_files(self) -> list[MarkerFile]:
        return [
            MarkerFile("pom.xml", "Spring/Maven"),
            MarkerFile("build.gradle", "Spring/Gradle"),
            MarkerFile("build.gradle.kts", "Spring/Gradle-KTS"),
        ]

    @property
    def ext_to_lang(self) -> dict[str, str]:
        return {".java": "java"}

    # ── Symbol Extraction ───────────────────────────────────────────────────

    def extract_symbols(self, path, content, lines, lang, module):
        records = []

        # Classes / interfaces / enums
        for m in _JAVA_CLASS.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="class", path=path,
                line=line_no, end_line=end_line, language="java", module=module,
            ))

        # Methods
        for m in _JAVA_METHOD.finditer(content):
            name = m.group(1)
            if name in _JAVA_KEYWORD_SKIP:
                continue
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=name, kind="method", path=path,
                line=line_no, end_line=end_line, language="java", module=module,
            ))

        # Spring endpoints
        for m in _SPRING_ENDPOINTS.finditer(content):
            line_no = count_line(content, m.start())
            records.append(dict(
                symbol=m.group(1), kind="endpoint", path=path,
                line=line_no, end_line=0, language="java", module=module,
            ))

        # Key annotations (Spring stereotypes)
        for m in _JAVA_ANNOTATION.finditer(content):
            name = m.group(1)
            if name in _SPRING_ANNOTS:
                line_no = count_line(content, m.start())
                records.append(dict(
                    symbol=f"@{name}", kind="decorator", path=path,
                    line=line_no, end_line=0, language="java", module=module,
                ))

        return records

    # ── Container Detection ─────────────────────────────────────────────────

    def detect_container(self, dir_path, name, ctx):
        # Check Gradle first, then Maven
        build_gradle = dir_path / "build.gradle"
        build_gradle_kts = dir_path / "build.gradle.kts"

        if build_gradle.exists() or build_gradle_kts.exists():
            gradle_file = build_gradle if build_gradle.exists() else build_gradle_kts
            return self._detect_gradle_container(gradle_file, name, ctx)

        pom_xml = dir_path / "pom.xml"
        if pom_xml.exists():
            return self._detect_maven_container(pom_xml, name, ctx)

        return None

    def _detect_gradle_container(self, gradle_path, name, ctx):
        content = ctx.read_file_content(gradle_path)
        lines = ctx.read_file_lines(gradle_path)

        is_spring = "org.springframework.boot" in content or "spring-boot" in content.lower()
        is_batch = "spring-boot-starter-batch" in content
        has_main = self._find_spring_main_class(gradle_path.parent, ctx) is not None

        if is_spring:
            container_type = "batch" if is_batch else "backend"
            technology = "Spring Batch" if is_batch else "Spring Boot"
        else:
            container_type = "library"
            technology = "Java/Gradle"

        if ctx.is_test_directory(name):
            container_type = "test"

        spring_line = ctx.find_line_number(lines, "spring") or 1
        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(gradle_path.parent),
            "category": "application" if has_main else "library",
            "metadata": {
                "build_system": "gradle",
                "has_main_class": has_main,
            },
            "evidence": [{
                "path": ctx.relative_path(gradle_path),
                "line_start": spring_line,
                "line_end": spring_line + 10,
                "reason": f"{technology} project: {name}",
            }],
        }

    def _detect_maven_container(self, pom_path, name, ctx):
        content = ctx.read_file_content(pom_path)
        lines = ctx.read_file_lines(pom_path)

        # Skip parent POMs
        if "<modules>" in content and "<packaging>pom</packaging>" in content:
            return None

        is_spring = "spring-boot" in content.lower()
        is_batch = "spring-boot-starter-batch" in content
        has_main = self._find_spring_main_class(pom_path.parent, ctx) is not None

        if is_spring:
            container_type = "batch" if is_batch else "backend"
            technology = "Spring Batch" if is_batch else "Spring Boot"
        else:
            container_type = "library"
            technology = "Java/Maven"

        if ctx.is_test_directory(name):
            container_type = "test"

        artifact_line = ctx.find_line_number(lines, "<artifactId>") or 1
        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(pom_path.parent),
            "category": "application" if has_main else "library",
            "metadata": {
                "build_system": "maven",
                "has_main_class": has_main,
            },
            "evidence": [{
                "path": ctx.relative_path(pom_path),
                "line_start": artifact_line,
                "line_end": artifact_line + 10,
                "reason": f"{technology} project: {name}",
            }],
        }

    def _find_spring_main_class(self, root, ctx):
        """Find @SpringBootApplication class."""
        java_root = root / "src" / "main" / "java"
        if not java_root.exists():
            java_root = root

        java_files = ctx.find_files("*.java", java_root)[:100]

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
                if "@SpringBootApplication" in content:
                    file_lines = content.splitlines()
                    for i, line in enumerate(file_lines):
                        if "@SpringBootApplication" in line:
                            return {
                                "path": ctx.relative_path(java_file),
                                "line": i + 1,
                            }
            except Exception:
                continue
        return None

    # ── Version Collection ──────────────────────────────────────────────────

    def collect_versions(self, ctx):
        self._collect_gradle_versions(ctx)
        self._collect_maven_versions(ctx)
        self._collect_java_version_files(ctx)

    # --- Gradle ---

    def _collect_gradle_versions(self, ctx):
        for gradle_file in ctx.find_files("build.gradle"):
            self._parse_gradle_file(gradle_file, ctx)
        for gradle_file in ctx.find_files("build.gradle.kts"):
            self._parse_gradle_file(gradle_file, ctx)
        for wrapper_file in ctx.find_files("gradle-wrapper.properties"):
            self._parse_gradle_wrapper(wrapper_file, ctx)
        for props_file in ctx.find_files("gradle.properties"):
            self._parse_gradle_properties(props_file, ctx)
        for catalog_file in ctx.find_files("libs.versions.toml"):
            self._parse_version_catalog(catalog_file, ctx)

    def _parse_gradle_file(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)

            # Spring Boot version
            for pattern in [
                r"org\.springframework\.boot['\"]?\s*version\s*['\"]?([0-9.]+)",
                r"springBootVersion\s*=\s*['\"]([0-9.]+)['\"]",
                r"id\s*\(?['\"]org\.springframework\.boot['\"]\)?\s*version\s*['\"]([0-9.]+)",
                r"spring-boot-gradle-plugin:([0-9.]+)",
            ]:
                match = re.search(pattern, content)
                if match:
                    ctx.add_version("Spring Boot", match.group(1), rel_path, "framework")
                    break

            # Java/JDK version
            for pattern in [
                r"sourceCompatibility\s*=\s*['\"]?(\d+)['\"]?",
                r"targetCompatibility\s*=\s*['\"]?(\d+)['\"]?",
                r"JavaVersion\.VERSION_(\d+)",
                r"java\.toolchain\s*\{[^}]*languageVersion\.set\(JavaLanguageVersion\.of\((\d+)\)",
                r"jvmToolchain\((\d+)\)",
            ]:
                match = re.search(pattern, content)
                if match:
                    ctx.add_version("Java", match.group(1), rel_path, "language")
                    break

            # Kotlin version
            kotlin_match = re.search(r"kotlin\(['\"]jvm['\"]\)\s*version\s*['\"]([0-9.]+)", content)
            if not kotlin_match:
                kotlin_match = re.search(r"kotlin-gradle-plugin:([0-9.]+)", content)
            if kotlin_match:
                ctx.add_version("Kotlin", kotlin_match.group(1), rel_path, "language")
        except Exception:
            pass

    def _parse_gradle_wrapper(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)
            match = re.search(r"gradle-([0-9.]+)-", content)
            if match:
                ctx.add_version("Gradle", match.group(1), rel_path, "build_tool")
        except Exception:
            pass

    def _parse_gradle_properties(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)
            patterns = {
                "Spring Boot": (r"springBootVersion\s*=\s*([0-9.]+)", "framework"),
                "Kotlin": (r"kotlinVersion\s*=\s*([0-9.]+)", "language"),
                "Java": (r"javaVersion\s*=\s*(\d+)", "language"),
            }
            for tech, (pattern, category) in patterns.items():
                match = re.search(pattern, content)
                if match:
                    ctx.add_version(tech, match.group(1), rel_path, category)
        except Exception:
            pass

    def _parse_version_catalog(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)

            versions_match = re.search(r"\[versions\](.*?)(?:^\[|\Z)", content, re.DOTALL | re.MULTILINE)
            if not versions_match:
                return

            versions_section = versions_match.group(1)
            catalog_tech_map = {
                "springboot": ("Spring Boot", "framework"),
                "kotlin": ("Kotlin", "language"),
                "java": ("Java", "language"),
                "angular": ("Angular", "framework"),
                "node": ("Node.js", "runtime"),
                "typescript": ("TypeScript", "language"),
            }

            for line in versions_section.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, raw_value = line.partition("=")
                key = key.strip().lower().replace("-", "").replace("_", "")
                version_match = re.search(r"(\d+\.\d+(?:\.\d+)*)", raw_value)
                if not version_match:
                    continue
                version = version_match.group(1)
                if key in catalog_tech_map:
                    tech_name, category = catalog_tech_map[key]
                    ctx.add_version(tech_name, version, rel_path, category)
        except Exception:
            pass

    # --- Maven ---

    def _collect_maven_versions(self, ctx):
        for pom_file in ctx.find_files("pom.xml"):
            self._parse_pom_file(pom_file, ctx)

    def _parse_pom_file(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = ctx.relative_path(file_path)

            # Try XML parsing
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                ns = {"m": "http://maven.apache.org/POM/4.0.0"}

                parent = root.find(".//m:parent", ns) or root.find(".//parent")
                if parent is not None:
                    artifact = parent.find("m:artifactId", ns) or parent.find("artifactId")
                    version = parent.find("m:version", ns) or parent.find("version")
                    if artifact is not None and version is not None:
                        if "spring-boot" in (artifact.text or "").lower():
                            ctx.add_version("Spring Boot", version.text, rel_path, "framework")

                dep_mgmt = root.find(".//m:dependencyManagement", ns) or root.find(".//dependencyManagement")
                if dep_mgmt is not None:
                    for dep in dep_mgmt.findall(".//m:dependency", ns) or dep_mgmt.findall(".//dependency"):
                        artifact = dep.find("m:artifactId", ns) or dep.find("artifactId")
                        version = dep.find("m:version", ns) or dep.find("version")
                        if artifact is not None and version is not None:
                            artifact_text = artifact.text or ""
                            v = version.text or ""
                            if "spring-boot" in artifact_text.lower() and v and not v.startswith("${"):
                                ctx.add_version("Spring Boot", v, rel_path, "framework")
                                break

                props = root.find(".//m:properties", ns) or root.find(".//properties")
                if props is not None:
                    java_version = props.find("m:java.version", ns) or props.find("java.version")
                    if java_version is not None and java_version.text:
                        ctx.add_version("Java", java_version.text, rel_path, "language")

                    maven_compiler = props.find("m:maven.compiler.source", ns) or props.find("maven.compiler.source")
                    if maven_compiler is not None and maven_compiler.text:
                        ctx.add_version("Java", maven_compiler.text, rel_path, "language")
            except ET.ParseError:
                pass

            # Fallback: regex
            for spring_prop_pattern in [
                r"<spring-boot\.version>([0-9.]+)</spring-boot\.version>",
                r"<spring\.boot\.version>([0-9.]+)</spring\.boot\.version>",
                r"<springBootVersion>([0-9.]+)</springBootVersion>",
            ]:
                spring_match = re.search(spring_prop_pattern, content)
                if spring_match:
                    ctx.add_version("Spring Boot", spring_match.group(1), rel_path, "framework")
                    break

            java_match = re.search(r"<java\.version>([0-9.]+)</java\.version>", content)
            if java_match:
                ctx.add_version("Java", java_match.group(1), rel_path, "language")

            maven_match = re.search(r"<maven\.version>([0-9.]+)</maven\.version>", content)
            if maven_match:
                ctx.add_version("Maven", maven_match.group(1), rel_path, "build_tool")
        except Exception:
            pass

    # --- .java-version ---

    def _collect_java_version_files(self, ctx):
        for version_file in ctx.find_files(".java-version"):
            try:
                version = version_file.read_text(encoding="utf-8").strip()
                if version:
                    ctx.add_version("Java", version, ctx.relative_path(version_file), "language")
            except Exception:
                pass

    # ── Component Technologies ──────────────────────────────────────────────

    def get_component_technologies(self) -> set[str]:
        return {"Spring Boot", "Java/Gradle", "Java/Maven", "Spring Batch"}

    # ── Dimension Delegation ──────────────────────────────────────────────

    def collect_dimension(self, dimension, repo_path, container_id=""):
        dispatch = {
            "build_system": self._collect_build_system,
            "runtime": self._collect_runtime,
            "dependencies": self._collect_dependencies,
            "security_details": self._collect_security_details,
            "validation": self._collect_validation,
            "error_handling": self._collect_error_handling,
            "tests": self._collect_tests,
            "data_model": self._collect_data_model,
            "workflows": self._collect_workflows,
            "interfaces": self._collect_interfaces,
            "configuration": self._collect_configuration,
            "logging_observability": self._collect_logging,
            "communication_patterns": self._collect_communication,
        }
        handler = dispatch.get(dimension)
        return handler(repo_path, container_id) if handler else ([], [])

    def _collect_build_system(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.build_system_collector import SpringBuildSystemCollector
        output = SpringBuildSystemCollector(repo_path).collect()
        return output.facts, output.relations

    def _collect_runtime(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.runtime_collector import SpringRuntimeCollector
        output = SpringRuntimeCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_dependencies(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.dependency_collector import SpringDependencyCollector
        output = SpringDependencyCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_security_details(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.security_detail_collector import SpringSecurityDetailCollector
        output = SpringSecurityDetailCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_validation(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.validation_collector import SpringValidationCollector
        output = SpringValidationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_error_handling(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.error_collector import SpringErrorCollector
        output = SpringErrorCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_tests(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.test_collector import SpringTestCollector
        output = SpringTestCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_data_model(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.data_model_collector import SpringDataModelCollector
        output = SpringDataModelCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_workflows(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.workflow_collector import SpringWorkflowCollector
        output = SpringWorkflowCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_interfaces(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.interface_detail_collector import SpringInterfaceDetailCollector
        output = SpringInterfaceDetailCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_configuration(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.configuration_collector import SpringConfigurationCollector
        output = SpringConfigurationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_logging(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.logging_collector import SpringLoggingCollector
        output = SpringLoggingCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_communication(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.spring.communication_collector import SpringCommunicationCollector
        output = SpringCommunicationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def collect_components(self, container, repo_path):
        # Lazy import to avoid circular dependency
        from ...pipelines.architecture_facts.collectors.spring import (
            SpringRepositoryCollector,
            SpringRestCollector,
            SpringServiceCollector,
        )

        root_path = container.get("root_path", "")
        container_root = repo_path / root_path if root_path and root_path != "." else repo_path
        container_name = container.get("name", "backend")

        facts = []
        relations = []
        for CollectorClass in [SpringRestCollector, SpringServiceCollector, SpringRepositoryCollector]:
            collector = CollectorClass(container_root, container_id=container_name)
            output = collector.collect()
            facts.extend(output.facts)
            relations.extend(output.relations)
        return facts, relations
