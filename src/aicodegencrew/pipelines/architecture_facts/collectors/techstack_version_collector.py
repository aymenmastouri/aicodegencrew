"""
TechStackVersionCollector - Extracts technology versions for upgrade planning.

Detects versions from:
- build.gradle / build.gradle.kts (Spring Boot, Java, Gradle plugins)
- pom.xml (Maven, Spring Boot, Java)
- package.json (Node.js, Angular, React, TypeScript)
- angular.json (Angular CLI version)
- .java-version, .node-version, .nvmrc
- gradle.properties, gradle-wrapper.properties
- Dockerfile (base images)

Output -> tech_versions in system.json
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET
from dataclasses import dataclass, field

from .base import DimensionCollector, CollectorOutput, RawFact
from ....shared.utils.logger import logger


@dataclass
class TechVersion(RawFact):
    """A technology version fact."""
    technology: str = ""
    version: str = ""
    source_file: str = ""
    category: str = ""  # language, framework, build_tool, library, runtime


class TechStackVersionCollector(DimensionCollector):
    """
    Collects technology versions from build files and config files.

    Essential for upgrade planning (e.g., Angular upgrade, Java upgrade).
    """

    DIMENSION = "tech_versions"

    # Skip directories
    SKIP_DIRS = {'node_modules', 'dist', 'build', 'target', '.git', 'bin', 'generated'}

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self.versions: Dict[str, TechVersion] = {}

    def collect(self) -> CollectorOutput:
        """Collect all technology version facts."""
        self._log_start()

        # Java/JVM ecosystem
        self._collect_gradle_versions()
        self._collect_maven_versions()
        self._collect_java_version_files()

        # JavaScript/TypeScript ecosystem
        self._collect_npm_versions()
        self._collect_angular_versions()
        self._collect_node_version_files()

        # Docker/Container
        self._collect_dockerfile_versions()

        # Add all to output
        for version in self.versions.values():
            self.output.add_fact(version)

        logger.info(f"[TechStackVersionCollector] Found {len(self.versions)} technology versions")
        self._log_end()
        return self.output

    def _add_version(self, technology: str, version: str, source_file: str, category: str):
        """Add a version fact if not already present or if version is more specific."""
        key = f"{technology}:{category}"

        # Clean version string
        version = version.strip().strip('"').strip("'")
        if not version:
            return

        # Skip if already have this tech with same or better version
        if key in self.versions:
            existing = self.versions[key]
            if len(existing.version) >= len(version):
                return

        fact = TechVersion(
            name=f"{technology} {version}",
            technology=technology,
            version=version,
            source_file=source_file,
            category=category,
        )
        fact.add_evidence(
            path=source_file,
            line_start=1,
            line_end=10,
            reason=f"{technology} version: {version}"
        )
        self.versions[key] = fact
        logger.debug(f"[TechStackVersionCollector] {technology}: {version} ({source_file})")

    # =========================================================================
    # Gradle
    # =========================================================================

    def _collect_gradle_versions(self):
        """Collect versions from Gradle files."""
        # build.gradle and build.gradle.kts
        for pattern in ["build.gradle", "build.gradle.kts"]:
            for gradle_file in self.repo_path.rglob(pattern):
                if self._should_skip(gradle_file):
                    continue
                self._parse_gradle_file(gradle_file)

        # gradle-wrapper.properties
        for wrapper_file in self.repo_path.rglob("gradle-wrapper.properties"):
            if self._should_skip(wrapper_file):
                continue
            self._parse_gradle_wrapper(wrapper_file)

        # gradle.properties
        for props_file in self.repo_path.rglob("gradle.properties"):
            if self._should_skip(props_file):
                continue
            self._parse_gradle_properties(props_file)

    def _parse_gradle_file(self, file_path: Path):
        """Parse build.gradle for versions."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # Spring Boot version
            for pattern in [
                r"org\.springframework\.boot['\"]?\s*version\s*['\"]?([0-9.]+)",
                r"springBootVersion\s*=\s*['\"]([0-9.]+)['\"]",
                r"id\s*\(?['\"]org\.springframework\.boot['\"]\)?\s*version\s*['\"]([0-9.]+)",
                r"spring-boot-gradle-plugin:([0-9.]+)",
            ]:
                match = re.search(pattern, content)
                if match:
                    self._add_version("Spring Boot", match.group(1), rel_path, "framework")
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
                    java_version = match.group(1)
                    self._add_version("Java", java_version, rel_path, "language")
                    break

            # Kotlin version
            kotlin_match = re.search(r"kotlin\(['\"]jvm['\"]\)\s*version\s*['\"]([0-9.]+)", content)
            if not kotlin_match:
                kotlin_match = re.search(r"kotlin-gradle-plugin:([0-9.]+)", content)
            if kotlin_match:
                self._add_version("Kotlin", kotlin_match.group(1), rel_path, "language")

        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    def _parse_gradle_wrapper(self, file_path: Path):
        """Parse gradle-wrapper.properties for Gradle version."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # distributionUrl=https\://services.gradle.org/distributions/gradle-8.5-bin.zip
            match = re.search(r"gradle-([0-9.]+)-", content)
            if match:
                self._add_version("Gradle", match.group(1), rel_path, "build_tool")

        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    def _parse_gradle_properties(self, file_path: Path):
        """Parse gradle.properties for versions."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # Common version properties
            patterns = {
                "Spring Boot": r"springBootVersion\s*=\s*([0-9.]+)",
                "Kotlin": r"kotlinVersion\s*=\s*([0-9.]+)",
                "Java": r"javaVersion\s*=\s*(\d+)",
            }

            for tech, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    category = "framework" if tech == "Spring Boot" else "language"
                    self._add_version(tech, match.group(1), rel_path, category)

        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    # =========================================================================
    # Maven
    # =========================================================================

    def _collect_maven_versions(self):
        """Collect versions from Maven pom.xml files."""
        for pom_file in self.repo_path.rglob("pom.xml"):
            if self._should_skip(pom_file):
                continue
            self._parse_pom_file(pom_file)

    def _parse_pom_file(self, file_path: Path):
        """Parse pom.xml for versions."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # Try XML parsing
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

                # Spring Boot parent version
                parent = root.find('.//m:parent', ns) or root.find('.//parent')
                if parent is not None:
                    artifact = parent.find('m:artifactId', ns) or parent.find('artifactId')
                    version = parent.find('m:version', ns) or parent.find('version')
                    if artifact is not None and version is not None:
                        if 'spring-boot' in (artifact.text or '').lower():
                            self._add_version("Spring Boot", version.text, rel_path, "framework")

                # Java version from properties
                props = root.find('.//m:properties', ns) or root.find('.//properties')
                if props is not None:
                    java_version = props.find('m:java.version', ns) or props.find('java.version')
                    if java_version is not None and java_version.text:
                        self._add_version("Java", java_version.text, rel_path, "language")

                    maven_compiler = props.find('m:maven.compiler.source', ns) or props.find('maven.compiler.source')
                    if maven_compiler is not None and maven_compiler.text:
                        self._add_version("Java", maven_compiler.text, rel_path, "language")

            except ET.ParseError:
                pass

            # Fallback: regex parsing
            spring_match = re.search(r"<spring-boot\.version>([0-9.]+)</spring-boot\.version>", content)
            if spring_match:
                self._add_version("Spring Boot", spring_match.group(1), rel_path, "framework")

            java_match = re.search(r"<java\.version>([0-9.]+)</java\.version>", content)
            if java_match:
                self._add_version("Java", java_match.group(1), rel_path, "language")

            # Maven wrapper version
            maven_match = re.search(r"<maven\.version>([0-9.]+)</maven\.version>", content)
            if maven_match:
                self._add_version("Maven", maven_match.group(1), rel_path, "build_tool")

        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    def _collect_java_version_files(self):
        """Collect Java version from .java-version files."""
        for version_file in self.repo_path.rglob(".java-version"):
            if self._should_skip(version_file):
                continue
            try:
                version = version_file.read_text(encoding='utf-8').strip()
                if version:
                    self._add_version("Java", version, self._relative_path(version_file), "language")
            except Exception:
                pass

    # =========================================================================
    # NPM / Node.js
    # =========================================================================

    def _collect_npm_versions(self):
        """Collect versions from package.json files."""
        for package_file in self.repo_path.rglob("package.json"):
            if self._should_skip(package_file):
                continue
            self._parse_package_json(package_file)

    def _parse_package_json(self, file_path: Path):
        """Parse package.json for versions."""
        try:
            content = file_path.read_text(encoding='utf-8')
            pkg = json.loads(content)
            rel_path = self._relative_path(file_path)

            deps = pkg.get("dependencies", {})
            dev_deps = pkg.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}

            # Key frameworks/libraries
            version_map = {
                "@angular/core": ("Angular", "framework"),
                "@angular/cli": ("Angular CLI", "build_tool"),
                "react": ("React", "framework"),
                "react-dom": ("React DOM", "framework"),
                "vue": ("Vue", "framework"),
                "typescript": ("TypeScript", "language"),
                "rxjs": ("RxJS", "library"),
                "@ngrx/store": ("NgRx", "library"),
                "webpack": ("Webpack", "build_tool"),
                "vite": ("Vite", "build_tool"),
                "jest": ("Jest", "library"),
                "karma": ("Karma", "library"),
                "playwright": ("Playwright", "library"),
                "cypress": ("Cypress", "library"),
            }

            for dep_name, (tech_name, category) in version_map.items():
                if dep_name in all_deps:
                    version = all_deps[dep_name]
                    # Clean version (remove ^, ~, v prefix, extract major version)
                    clean_version = re.sub(r'^[\^~>=<v]+', '', str(version))
                    # Extract major version: "18.2.13" -> "18", "18-lts" -> "18"
                    match = re.match(r'^(\d+)', clean_version)
                    if match:
                        clean_version = match.group(1)
                    self._add_version(tech_name, clean_version, rel_path, category)

            # Node.js engine
            engines = pkg.get("engines", {})
            if "node" in engines:
                node_version = re.sub(r'^[\^~>=<]+', '', str(engines["node"]))
                self._add_version("Node.js", node_version, rel_path, "runtime")

        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    def _collect_angular_versions(self):
        """Collect Angular CLI version from angular.json."""
        for angular_file in self.repo_path.rglob("angular.json"):
            if self._should_skip(angular_file):
                continue
            try:
                content = angular_file.read_text(encoding='utf-8')
                pkg = json.loads(content)
                rel_path = self._relative_path(angular_file)

                # CLI version from $schema or version field
                schema = pkg.get("$schema", "")
                version_match = re.search(r"@angular/cli/([0-9.]+)", schema)
                if version_match:
                    self._add_version("Angular CLI", version_match.group(1), rel_path, "build_tool")

            except Exception as e:
                logger.debug(f"[TechStackVersionCollector] Failed to parse {angular_file}: {e}")

    def _collect_node_version_files(self):
        """Collect Node.js version from version files."""
        for pattern in [".node-version", ".nvmrc"]:
            for version_file in self.repo_path.rglob(pattern):
                if self._should_skip(version_file):
                    continue
                try:
                    version = version_file.read_text(encoding='utf-8').strip()
                    if version:
                        # Remove 'v' prefix if present
                        version = version.lstrip('v')
                        self._add_version("Node.js", version, self._relative_path(version_file), "runtime")
                except Exception:
                    pass

    # =========================================================================
    # Docker
    # =========================================================================

    def _collect_dockerfile_versions(self):
        """Collect base image versions from Dockerfiles."""
        for dockerfile in self.repo_path.rglob("Dockerfile*"):
            if self._should_skip(dockerfile):
                continue
            self._parse_dockerfile(dockerfile)

    def _parse_dockerfile(self, file_path: Path):
        """Parse Dockerfile for base image versions."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # FROM image:version
            for match in re.finditer(r'^FROM\s+([^:\s]+):([^\s]+)', content, re.MULTILINE):
                image = match.group(1)
                version = match.group(2)

                # Map common images
                if 'openjdk' in image.lower() or 'eclipse-temurin' in image.lower():
                    self._add_version("Java (Docker)", version, rel_path, "runtime")
                elif 'node' in image.lower():
                    self._add_version("Node.js (Docker)", version, rel_path, "runtime")
                elif 'nginx' in image.lower():
                    self._add_version("Nginx (Docker)", version, rel_path, "runtime")
                elif 'postgres' in image.lower():
                    self._add_version("PostgreSQL (Docker)", version, rel_path, "database")
                elif 'oracle' in image.lower():
                    self._add_version("Oracle (Docker)", version, rel_path, "database")

        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)

    def _relative_path(self, file_path: Path) -> str:
        """Get relative path from repo root."""
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
