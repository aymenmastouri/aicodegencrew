"""
BuildSystemCollector - Extracts build system facts.

Detects:
- Gradle multi-module structure, plugins, tasks, wrappers
- Maven modules, plugins, profiles, wrappers
- npm scripts and workspaces
- Angular project architect targets

Output -> build_system.json
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawFact


@dataclass
class RawBuildFact(RawFact):
    """A build system fact."""

    build_tool: str = ""
    module: str = ""
    module_path: str = ""
    tasks: list[str] = field(default_factory=list)
    source_dirs: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    wrapper_path: str | None = None
    parent_module: str | None = None
    build_file: str = ""
    properties: dict[str, str] = field(default_factory=dict)


class BuildSystemCollector(DimensionCollector):
    """
    Extracts build system facts from Gradle, Maven, npm, and Angular configs.

    Essential for Phase 5 (Implement) to know HOW to compile, test, and run
    the target repo.
    """

    DIMENSION = "build_system"

    SKIP_DIRS = {
        "node_modules",
        ".git",
        "__pycache__",
        "dist",
        "build",
        "target",
        ".venv",
        "venv",
        ".idea",
        ".gradle",
        "out",
    }

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        """Collect build system facts from all detected build tools."""
        self._log_start()

        self._collect_gradle()
        self._collect_maven()
        self._collect_npm()
        self._collect_angular()

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

    # =========================================================================
    # npm
    # =========================================================================

    def _collect_npm(self) -> None:
        """Extract npm build system facts from package.json files."""
        pkg_files = self._find_files("package.json")
        if not pkg_files:
            return

        logger.info(f"  [npm] Found {len(pkg_files)} package.json file(s)...")

        for pkg_file in pkg_files:
            self._extract_npm_module(pkg_file)

    def _extract_npm_module(self, pkg_file: Path) -> None:
        """Extract facts from a single package.json."""
        try:
            with open(pkg_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        name = data.get("name", pkg_file.parent.name)
        scripts = data.get("scripts", {})
        rel_pkg = self._relative_path(pkg_file)
        module_path = self._relative_path(pkg_file.parent)
        lines = self._read_file(pkg_file)

        # Classify scripts
        tasks = list(scripts.keys())

        # Detect source dirs
        source_dirs = self._detect_source_dirs(pkg_file.parent)

        # Key properties
        properties: dict[str, str] = {}
        if data.get("version"):
            properties["version"] = data["version"]
        if data.get("engines"):
            for eng_key, eng_val in data["engines"].items():
                properties[f"engine.{eng_key}"] = eng_val

        fact = RawBuildFact(
            name=f"npm:{name}",
            build_tool="npm",
            module=name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=source_dirs,
            plugins=[],
            wrapper_path=None,
            build_file=rel_pkg,
            properties=properties,
            metadata={"scripts": scripts},
        )
        fact.add_evidence(
            path=rel_pkg,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"npm package.json for '{name}'",
        )
        self.output.add_fact(fact)

    # =========================================================================
    # Angular
    # =========================================================================

    def _collect_angular(self) -> None:
        """Extract Angular build system facts from angular.json."""
        angular_files = self._find_files("angular.json")
        if not angular_files:
            return

        logger.info(f"  [Angular] Found {len(angular_files)} angular.json file(s)...")

        for angular_file in angular_files:
            self._extract_angular_projects(angular_file)

        # Also scan tsconfig for build-relevant path mappings
        tsconfig_files = self._find_files("tsconfig.json")
        tsconfig_files.extend(self._find_files("tsconfig.app.json"))
        for tsconfig_file in tsconfig_files:
            self._extract_tsconfig_paths(tsconfig_file)

    def _extract_angular_projects(self, angular_file: Path) -> None:
        """Extract architect targets per Angular project."""
        try:
            with open(angular_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        projects = data.get("projects", {})
        rel_file = self._relative_path(angular_file)
        lines = self._read_file(angular_file)

        for proj_name, proj_config in projects.items():
            architect = proj_config.get("architect", {})
            targets = list(architect.keys())
            root = proj_config.get("root", "")
            source_root = proj_config.get("sourceRoot", "")

            source_dirs = [source_root] if source_root else []

            fact = RawBuildFact(
                name=f"angular:{proj_name}",
                build_tool="angular",
                module=proj_name,
                module_path=root,
                tasks=targets,
                source_dirs=source_dirs,
                plugins=[],
                wrapper_path=None,
                build_file=rel_file,
                properties={},
            )
            fact.add_evidence(
                path=rel_file,
                line_start=1,
                line_end=min(len(lines), 10),
                reason=f"Angular project '{proj_name}' with targets: {', '.join(targets)}",
            )
            self.output.add_fact(fact)

    def _extract_tsconfig_paths(self, tsconfig_file: Path) -> None:
        """Extract build-relevant path mappings from tsconfig."""
        try:
            content = self._read_file_content(tsconfig_file)
            # Strip comments (tsconfig allows them)
            content = re.sub(r"//.*?\n", "\n", content)
            content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
            data = json.loads(content)
        except (json.JSONDecodeError, OSError):
            return

        compiler_opts = data.get("compilerOptions", {})
        paths = compiler_opts.get("paths", {})
        if not paths:
            return

        rel_file = self._relative_path(tsconfig_file)
        lines = self._read_file(tsconfig_file)

        fact = RawBuildFact(
            name=f"tsconfig:{tsconfig_file.stem}",
            build_tool="angular",
            module=tsconfig_file.stem,
            module_path=self._relative_path(tsconfig_file.parent),
            tasks=[],
            source_dirs=[],
            plugins=[],
            wrapper_path=None,
            build_file=rel_file,
            properties={},
            metadata={"path_mappings": paths},
        )
        fact.add_evidence(
            path=rel_file,
            line_start=1,
            line_end=min(len(lines), 10),
            reason=f"TypeScript path mappings: {len(paths)} entries",
        )
        self.output.add_fact(fact)

    # =========================================================================
    # Shared Helpers
    # =========================================================================

    def _detect_source_dirs(self, module_root: Path) -> list[str]:
        """Detect conventional source directories relative to module root."""
        candidates = [
            "src/main/java",
            "src/main/kotlin",
            "src/main/resources",
            "src/test/java",
            "src/test/kotlin",
            "src/test/resources",
            "src",
            "lib",
            "app",
        ]
        found = []
        for candidate in candidates:
            if (module_root / candidate).is_dir():
                found.append(candidate)
        return found
