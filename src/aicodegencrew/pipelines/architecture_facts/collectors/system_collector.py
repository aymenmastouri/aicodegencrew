"""
SystemCollector - Extracts system-level facts.

Detects:
- System name (from directory, pom.xml, package.json, settings.gradle)
- Bounded Contexts (from package structure - dynamically detected)
- Subsystems / Modules

Detection Strategy:
1. System name = Repository directory name (most reliable)
2. Bounded Contexts = Top-level packages under domain/feature packages
3. No hardcoded patterns - detect from actual package structure

Output -> system.json
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawFact


@dataclass
class RawSubsystem(RawFact):
    """A subsystem/module within the system."""

    type: str = ""  # module, bounded_context, subproject
    root_path: str = ""


@dataclass
class RawSystemInfo(RawFact):
    """System-level information."""

    version: str | None = None
    description: str | None = None
    group_id: str | None = None
    subsystems: list[str] = field(default_factory=list)


class SystemCollector(DimensionCollector):
    """
    Extracts system-level architecture facts.

    Key Principle: Use repository directory name as system name.
    Bounded contexts are detected dynamically from package structure.
    """

    DIMENSION = "system"

    def collect(self) -> CollectorOutput:
        """Collect system-level facts."""
        self._log_start()

        # 1. Detect system name and metadata
        system_info = self._detect_system_info()
        if system_info:
            self.output.add_fact(system_info)

        # 2. Detect bounded contexts from package structure
        contexts = self._detect_bounded_contexts()
        for context in contexts:
            self.output.add_fact(context)

        self._log_end()
        return self.output

    def _detect_system_info(self) -> RawSystemInfo:
        """
        Detect system name and metadata.

        Priority:
        1. Repository directory name (most reliable)
        2. pom.xml artifactId (if exists)
        3. package.json name (if exists)
        """
        # Use directory name as primary system name
        system_name = self.repo_path.name
        version = None
        description = None
        group_id = None

        # Try to get additional info from build files
        pom = self.repo_path / "pom.xml"
        if pom.exists():
            pom_info = self._parse_pom(pom)
            version = pom_info.get("version")
            description = pom_info.get("description")
            group_id = pom_info.get("group_id")

        package_json = self.repo_path / "package.json"
        if package_json.exists() and not version:
            pkg_info = self._parse_package_json(package_json)
            version = pkg_info.get("version")
            description = pkg_info.get("description")

        info = RawSystemInfo(
            name=system_name,
            version=version,
            description=description,
            group_id=group_id,
        )

        # Add evidence
        if pom.exists():
            info.add_evidence(path="pom.xml", line_start=1, line_end=20, reason=f"System: {system_name}")
        elif package_json.exists():
            info.add_evidence(path="package.json", line_start=1, line_end=10, reason=f"System: {system_name}")
        else:
            # Evidence from directory
            info.add_evidence(path=".", line_start=1, line_end=1, reason=f"System name from directory: {system_name}")

        return info

    def _parse_pom(self, pom_path: Path) -> dict:
        """Parse Maven pom.xml for system info."""
        try:
            content = pom_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {}

        result = {}

        # Strip <parent>...</parent> block to avoid extracting parent version/groupId
        content_no_parent = re.sub(r"<parent>.*?</parent>", "", content, flags=re.DOTALL)

        # Extract version (from project, not parent)
        version_match = re.search(r"<version>([^<]+)</version>", content_no_parent)
        if version_match:
            result["version"] = version_match.group(1)

        # Extract groupId (from project, not parent)
        group_match = re.search(r"<groupId>([^<]+)</groupId>", content_no_parent)
        if group_match:
            result["group_id"] = group_match.group(1)

        # Extract description
        desc_match = re.search(r"<description>([^<]+)</description>", content)
        if desc_match:
            result["description"] = desc_match.group(1)

        return result

    def _parse_package_json(self, pkg_path: Path) -> dict:
        """Parse package.json for system info."""
        import json

        try:
            content = pkg_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return {
                "version": data.get("version"),
                "description": data.get("description"),
            }
        except Exception:
            return {}

    def _detect_bounded_contexts(self) -> list[RawSubsystem]:
        """
        Detect bounded contexts from Java package structure.

        Strategy:
        1. Find all Java files
        2. Extract package names
        3. Find top-level domain packages (after base package)
        4. Each unique top-level package = potential bounded context

        Example:
            com.company.app.workflow.service.WorkflowService
            com.company.app.document.repository.DocumentRepository

        Detected contexts: workflow, document
        """
        contexts: dict[str, RawSubsystem] = {}

        # Find Java source directories
        java_roots = self._find_java_roots()

        for java_root in java_roots:
            # Find all Java files (use _find_files for SKIP_DIRS pruning)
            java_files = self._find_files("*.java", java_root)[:500]  # Limit for performance

            for java_file in java_files:
                # Extract package from file
                package_name = self._extract_package(java_file)
                if not package_name:
                    continue

                # Get potential context name
                context_name = self._extract_context_from_package(package_name)
                if context_name and context_name not in contexts:
                    # Validate it's a real context (has multiple classes)
                    if self._is_valid_context(java_root, package_name, context_name):
                        subsystem = RawSubsystem(
                            name=context_name,
                            type="bounded_context",
                            root_path=str(java_root.relative_to(self.repo_path)),
                        )
                        subsystem.add_evidence(
                            path=str(java_file.relative_to(self.repo_path)),
                            line_start=1,
                            line_end=5,
                            reason=f"Bounded context '{context_name}' from package {package_name}",
                        )
                        contexts[context_name] = subsystem

        return list(contexts.values())

    def _find_java_roots(self) -> list[Path]:
        """Find all Java source roots."""
        roots = []

        # Standard Maven/Gradle structure
        for pattern in ["src/main/java", "*/src/main/java"]:
            for path in self.repo_path.glob(pattern):
                if path.is_dir() and "deployment" not in str(path):
                    roots.append(path)

        return roots

    def _extract_package(self, java_file: Path) -> str | None:
        """Extract package name from Java file."""
        try:
            # Read only first few lines
            with open(java_file, encoding="utf-8", errors="ignore") as f:
                for _ in range(20):
                    line = f.readline()
                    if line.startswith("package "):
                        match = re.match(r"package\s+([\w.]+)\s*;", line)
                        if match:
                            return match.group(1)
            return None
        except Exception:
            return None

    def _extract_context_from_package(self, package_name: str) -> str | None:
        """
        Extract bounded context name from package.

        Example packages:
            com.company.app.workflow.service -> workflow
            de.example.app.document.repository -> document
            com.myapp.archive.model -> archive

        Strategy:
        1. Split package by '.'
        2. Skip common prefixes (com, de, org, at, etc.)
        3. Skip company name (2nd element usually)
        4. Skip common suffixes (service, repository, controller, model, etc.)
        5. Return first "domain-like" segment
        """
        parts = package_name.split(".")

        # Skip common prefixes
        skip_prefixes = {"com", "de", "at", "org", "net", "io", "ch"}
        skip_suffixes = {
            "service",
            "services",
            "repository",
            "repositories",
            "controller",
            "controllers",
            "model",
            "models",
            "entity",
            "entities",
            "dto",
            "dtos",
            "config",
            "configuration",
            "util",
            "utils",
            "common",
            "shared",
            "api",
            "impl",
            "internal",
            "test",
            "tests",
        }

        # Find context candidates
        for i, part in enumerate(parts):
            part_lower = part.lower()

            # Skip prefixes
            if part_lower in skip_prefixes:
                continue

            # Skip if looks like company name (2nd element, short)
            if i == 1 and len(part) <= 4:
                continue

            # Skip suffixes
            if part_lower in skip_suffixes:
                continue

            # Skip if it's the project name itself
            if part_lower == self.repo_path.name.lower():
                continue

            # This looks like a context name
            if len(part) >= 3 and part[0].islower():
                return part

        return None

    def _is_valid_context(self, java_root: Path, full_package: str, context_name: str) -> bool:
        """
        Validate that a context has multiple classes (not just one class).
        """
        # Count files in this context's package tree
        context_pattern = context_name.lower()
        count = 0

        for java_file in java_root.rglob("*.java"):
            try:
                with open(java_file, encoding="utf-8", errors="ignore") as f:
                    first_lines = f.read(500)
                    if f".{context_pattern}." in first_lines.lower():
                        count += 1
                        if count >= 3:  # At least 3 files = valid context
                            return True
            except Exception:
                continue

        return count >= 3
