"""Spring Build System Specialist — Extracts Gradle and Maven build facts.

Detects:
- Gradle multi-module structure, plugins, tasks, wrappers
- Maven modules, plugins, profiles, wrappers
"""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..build_system_collector import RawBuildFact


class SpringBuildSystemCollector(DimensionCollector):
    """Extracts Gradle and Maven build system facts."""

    DIMENSION = "build_system"

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        """Collect Gradle and Maven build system facts."""
        self._log_start()

        self._collect_gradle()
        self._collect_maven()

        self._log_end()
        return self.output

    # =========================================================================
    # Gradle
    # =========================================================================

    def _collect_gradle(self) -> None:
        """Extract Gradle build system facts."""
        # Find settings.gradle (root indicator)
        settings_files = self._find_files("settings.gradle")
        settings_files.extend(self._find_files("settings.gradle.kts"))

        if not settings_files:
            return

        logger.info("  [Gradle] Found settings file(s), extracting modules...")

        # Detect wrapper
        wrapper_path = self._detect_gradle_wrapper()

        for settings_file in settings_files:
            settings_root = settings_file.parent

            # Parse include directives to find modules
            modules = self._parse_gradle_settings(settings_file)

            # Root module
            root_build = self._find_gradle_build_file(settings_root)
            if root_build:
                self._extract_gradle_module(
                    build_file=root_build,
                    module_name="root",
                    module_path=".",
                    parent_module=None,
                    wrapper_path=wrapper_path,
                )

            # Sub-modules
            for mod_name in modules:
                mod_path = mod_name.replace(":", "/")
                mod_dir = settings_root / mod_path
                build_file = self._find_gradle_build_file(mod_dir)
                if build_file:
                    self._extract_gradle_module(
                        build_file=build_file,
                        module_name=mod_name,
                        module_path=mod_path,
                        parent_module="root",
                        wrapper_path=wrapper_path,
                    )

            # Scan gradle/*.gradle custom script files
            gradle_dir = settings_root / "gradle"
            if gradle_dir.is_dir():
                for gf in sorted(gradle_dir.iterdir()):
                    if gf.suffix in (".gradle", ".kts") and gf.is_file():
                        content = self._read_file_content(gf)
                        extra_tasks = self._parse_gradle_tasks(content)
                        if extra_tasks:
                            logger.info(f"  [Gradle] Custom script {gf.name}: {len(extra_tasks)} tasks")

    def _detect_gradle_wrapper(self) -> str | None:
        """Detect gradlew / gradlew.bat wrapper."""
        for name in ("gradlew", "gradlew.bat"):
            wrapper = self.repo_path / name
            if wrapper.exists():
                return self._relative_path(wrapper)
        return None

    def _find_gradle_build_file(self, directory: Path) -> Path | None:
        """Find build.gradle or build.gradle.kts in a directory."""
        for name in ("build.gradle.kts", "build.gradle"):
            candidate = directory / name
            if candidate.exists():
                return candidate
        return None

    def _parse_gradle_settings(self, settings_file: Path) -> list[str]:
        """Parse settings.gradle for include directives."""
        content = self._read_file_content(settings_file)
        modules = []

        # Parenthesised form (Kotlin DSL, single or multi-line):
        # include(":mod1", ":mod2") or include(\n    ":mod1",\n    ":mod2"\n)
        for match in re.finditer(r"""include\s*\(([^)]+)\)""", content, re.DOTALL):
            raw = match.group(1)
            for quoted in re.findall(r"""['"]([^'"]+)['"]""", raw):
                mod = quoted.lstrip(":")
                if mod not in modules:
                    modules.append(mod)

        # Groovy shorthand (no parens): include ':mod1', ':mod2'
        for match in re.finditer(r"""^include\s+([^(\n][^\n]*)""", content, re.MULTILINE):
            raw = match.group(1)
            for quoted in re.findall(r"""['"]([^'"]+)['"]""", raw):
                mod = quoted.lstrip(":")
                if mod not in modules:
                    modules.append(mod)

        return modules

    def _extract_gradle_module(
        self,
        build_file: Path,
        module_name: str,
        module_path: str,
        parent_module: str | None,
        wrapper_path: str | None,
    ) -> None:
        """Extract facts from a single Gradle build file."""
        content = self._read_file_content(build_file)
        rel_build = self._relative_path(build_file)
        lines = self._read_file(build_file)

        plugins = self._parse_gradle_plugins(content)
        tasks = self._parse_gradle_tasks(content)
        source_dirs = self._detect_source_dirs(build_file.parent)
        properties = self._parse_gradle_properties(content)

        fact = RawBuildFact(
            name=f"gradle:{module_name}",
            build_tool="gradle",
            module=module_name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=source_dirs,
            plugins=plugins,
            wrapper_path=wrapper_path,
            parent_module=parent_module,
            build_file=rel_build,
            properties=properties,
        )
        fact.add_evidence(
            path=rel_build,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"Gradle build file for module '{module_name}'",
        )
        self.output.add_fact(fact)

    def _parse_gradle_plugins(self, content: str) -> list[str]:
        """Parse plugins from plugins {} block and apply plugin statements."""
        plugins = []
        # plugins { id 'xxx' } or id("xxx")
        plugins_block = re.search(r"plugins\s*\{([^}]+)\}", content, re.DOTALL)
        if plugins_block:
            block = plugins_block.group(1)
            for m in re.finditer(r"""id\s*\(?['"]([^'"]+)['"]""", block):
                plugins.append(m.group(1))

        # apply plugin: 'xxx'
        for m in re.finditer(r"""apply\s+plugin:\s*['"]([^'"]+)['"]""", content):
            p = m.group(1)
            if p not in plugins:
                plugins.append(p)

        return plugins

    def _parse_gradle_tasks(self, content: str) -> list[str]:
        """Parse custom task definitions."""
        tasks = []
        # task taskName(type: ...) or task 'taskName'
        for m in re.finditer(r"""task\s+['"]?(\w+)['"]?""", content):
            tasks.append(m.group(1))
        # tasks.register("taskName")
        for m in re.finditer(r"""tasks\.register\s*\(\s*['"](\w+)['"]""", content):
            t = m.group(1)
            if t not in tasks:
                tasks.append(t)
        return tasks

    def _parse_gradle_properties(self, content: str) -> dict[str, str]:
        """Extract key build properties from Gradle build file."""
        props: dict[str, str] = {}
        for key in ("sourceCompatibility", "targetCompatibility", "group", "version"):
            m = re.search(rf"""{key}\s*=\s*['"]?([^'"\s]+)['"]?""", content)
            if m:
                props[key] = m.group(1)
        return props

    # =========================================================================
    # Maven
    # =========================================================================

    def _collect_maven(self) -> None:
        """Extract Maven build system facts."""
        root_pom = self.repo_path / "pom.xml"
        if not root_pom.exists():
            return

        logger.info("  [Maven] Found pom.xml, extracting modules...")

        wrapper_path = self._detect_maven_wrapper()
        self._extract_maven_module(root_pom, parent_module=None, wrapper_path=wrapper_path)

    def _detect_maven_wrapper(self) -> str | None:
        """Detect mvnw / mvnw.cmd wrapper."""
        for name in ("mvnw", "mvnw.cmd"):
            wrapper = self.repo_path / name
            if wrapper.exists():
                return self._relative_path(wrapper)
        return None

    def _extract_maven_module(
        self,
        pom_file: Path,
        parent_module: str | None,
        wrapper_path: str | None,
    ) -> None:
        """Extract facts from a single pom.xml, then recurse into child modules."""
        try:
            tree = ET.parse(pom_file)
        except ET.ParseError:
            logger.warning(f"  [Maven] Failed to parse {pom_file}")
            return

        root = tree.getroot()
        ns = ""
        # Detect Maven namespace
        ns_match = re.match(r"\{(.+)\}", root.tag)
        if ns_match:
            ns = ns_match.group(1)

        def _tag(tag: str) -> str:
            return f"{{{ns}}}{tag}" if ns else tag

        artifact_id = root.findtext(_tag("artifactId")) or pom_file.parent.name
        rel_pom = self._relative_path(pom_file)
        module_path = self._relative_path(pom_file.parent)
        lines = self._read_file(pom_file)

        # Modules
        modules_el = root.find(_tag("modules"))
        child_modules = []
        if modules_el is not None:
            child_modules = [m.text for m in modules_el.findall(_tag("module")) if m.text]

        # Plugins
        plugins = []
        for plugin_el in root.iter(_tag("plugin")):
            gid = plugin_el.findtext(_tag("groupId")) or ""
            aid = plugin_el.findtext(_tag("artifactId")) or ""
            plugins.append(f"{gid}:{aid}" if gid else aid)

        # Profiles
        profiles = []
        for profile_el in root.iter(_tag("profile")):
            pid = profile_el.findtext(_tag("id"))
            if pid:
                profiles.append(pid)

        # Properties
        properties: dict[str, str] = {}
        props_el = root.find(_tag("properties"))
        if props_el is not None:
            for prop in props_el:
                local_tag = prop.tag.split("}")[-1] if "}" in prop.tag else prop.tag
                if prop.text:
                    properties[local_tag] = prop.text

        source_dirs = self._detect_source_dirs(pom_file.parent)

        fact = RawBuildFact(
            name=f"maven:{artifact_id}",
            build_tool="maven",
            module=artifact_id,
            module_path=module_path,
            tasks=profiles,  # Maven profiles as "tasks"
            source_dirs=source_dirs,
            plugins=plugins,
            wrapper_path=wrapper_path,
            parent_module=parent_module,
            build_file=rel_pom,
            properties=properties,
        )
        fact.add_evidence(
            path=rel_pom,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"Maven POM for module '{artifact_id}'",
        )
        self.output.add_fact(fact)

        # Recurse into child modules
        for child in child_modules:
            child_pom = pom_file.parent / child / "pom.xml"
            if child_pom.exists():
                self._extract_maven_module(child_pom, parent_module=artifact_id, wrapper_path=wrapper_path)
