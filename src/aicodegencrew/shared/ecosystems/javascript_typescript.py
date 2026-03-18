"""JavaScript/TypeScript Ecosystem — Angular, React, Vue, Node.js."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ._utils import count_line, find_block_end
from .base import CollectorContext, EcosystemDefinition, MarkerFile

# ── Regex patterns ──────────────────────────────────────────────────────────

_TS_CLASS = re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE)
_TS_INTERFACE = re.compile(r"^\s*(?:export\s+)?interface\s+(\w+)", re.MULTILINE)
_TS_FUNCTION = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE)
_TS_METHOD = re.compile(
    r"^\s+(?:public|protected|private|readonly|static|async|abstract|\s)*(\w+)\s*\(",
    re.MULTILINE,
)
_TS_DECORATOR = re.compile(r"^\s*@(\w+)", re.MULTILINE)

_NG_DECORATORS = {"Component", "Injectable", "NgModule", "Directive", "Pipe", "Controller", "Module"}


class JavaScriptTypeScriptEcosystem(EcosystemDefinition):
    """JavaScript/TypeScript ecosystem: Angular, React, Vue, Node.js."""

    @property
    def id(self) -> str:
        return "javascript_typescript"

    @property
    def name(self) -> str:
        return "JavaScript/TypeScript"

    @property
    def priority(self) -> int:
        return 20

    @property
    def source_extensions(self) -> set[str]:
        return {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    @property
    def exclude_extensions(self) -> set[str]:
        return {".min.js", ".min.css", ".map"}

    @property
    def skip_directories(self) -> set[str]:
        return {"node_modules", ".next", ".nuxt", "dist", ".angular"}

    @property
    def marker_files(self) -> list[MarkerFile]:
        return [
            MarkerFile("angular.json", "Angular"),
            MarkerFile("package.json", "Node.js"),
        ]

    @property
    def ext_to_lang(self) -> dict[str, str]:
        return {
            ".ts": "typescript", ".tsx": "typescript",
            ".js": "javascript", ".jsx": "javascript",
            ".mjs": "javascript", ".cjs": "javascript",
        }

    # ── Symbol Extraction ───────────────────────────────────────────────────

    def extract_symbols(self, path, content, lines, lang, module):
        records = []

        # Classes
        for m in _TS_CLASS.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="class", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Interfaces
        for m in _TS_INTERFACE.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="interface", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Functions
        for m in _TS_FUNCTION.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="function", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Decorators (Angular/NestJS)
        for m in _TS_DECORATOR.finditer(content):
            name = m.group(1)
            if name in _NG_DECORATORS:
                line_no = count_line(content, m.start())
                records.append(dict(
                    symbol=f"@{name}", kind="decorator", path=path,
                    line=line_no, end_line=0, language=lang, module=module,
                ))

        return records

    # ── Container Detection ─────────────────────────────────────────────────

    def detect_container(self, dir_path, name, ctx):
        package_json = dir_path / "package.json"
        if not package_json.exists():
            return None

        try:
            content = package_json.read_text(encoding="utf-8")
            pkg = json.loads(content)
        except Exception:
            return None

        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}

        # Detect framework
        technology = None
        container_type = "frontend"

        if "@angular/core" in all_deps:
            technology = "Angular"
        elif "react" in all_deps:
            technology = "React"
        elif "vue" in all_deps:
            technology = "Vue"
        elif "cypress" in all_deps or "playwright" in all_deps or "protractor" in all_deps:
            technology = (
                "Cypress" if "cypress" in all_deps
                else "Playwright" if "playwright" in all_deps
                else "Protractor"
            )
            container_type = "test"
        else:
            technology = "Node.js"

        if ctx.is_test_directory(name):
            container_type = "test"

        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(dir_path),
            "category": "application" if container_type != "test" else "test",
            "metadata": {
                "build_system": "npm",
                "version": pkg.get("version"),
            },
            "evidence": [{
                "path": ctx.relative_path(package_json),
                "line_start": 1,
                "line_end": 20,
                "reason": f"{technology} project: {name}",
            }],
        }

    # ── Version Collection ──────────────────────────────────────────────────

    def collect_versions(self, ctx):
        self._collect_npm_versions(ctx)
        self._collect_angular_versions(ctx)
        self._collect_node_version_files(ctx)

    def _collect_npm_versions(self, ctx):
        for package_file in ctx.find_files("package.json"):
            self._parse_package_json(package_file, ctx)

    def _parse_package_json(self, file_path, ctx):
        try:
            content = file_path.read_text(encoding="utf-8")
            pkg = json.loads(content)
            rel_path = ctx.relative_path(file_path)

            deps = pkg.get("dependencies", {})
            dev_deps = pkg.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}

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
                    version_match = re.search(r"(\d+\.\d+(?:\.\d+)*)", str(version))
                    clean_version = version_match.group(1) if version_match else ""
                    if clean_version:
                        ctx.add_version(tech_name, clean_version, rel_path, category)

            # Node.js engine
            engines = pkg.get("engines", {})
            if "node" in engines:
                node_version = re.sub(r"^[\^~>=<]+", "", str(engines["node"]))
                ctx.add_version("Node.js", node_version, rel_path, "runtime")
        except Exception:
            pass

    def _collect_angular_versions(self, ctx):
        for angular_file in ctx.find_files("angular.json"):
            try:
                content = angular_file.read_text(encoding="utf-8")
                pkg = json.loads(content)
                rel_path = ctx.relative_path(angular_file)

                schema = pkg.get("$schema", "")
                schema_match = re.search(r"@angular/cli/(\d+\.\d+\.\d+)", schema)
                if schema_match:
                    ctx.add_version("Angular CLI", schema_match.group(1), rel_path, "build_tool")

                sibling_pkg = angular_file.parent / "package.json"
                if sibling_pkg.exists():
                    self._parse_package_json(sibling_pkg, ctx)
            except Exception:
                pass

    def _collect_node_version_files(self, ctx):
        for pattern in [".node-version", ".nvmrc"]:
            for version_file in ctx.find_files(pattern):
                try:
                    version = version_file.read_text(encoding="utf-8").strip()
                    if version:
                        version = version.lstrip("v")
                        ctx.add_version("Node.js", version, ctx.relative_path(version_file), "runtime")
                except Exception:
                    pass

    # ── Dimension Delegation ──────────────────────────────────────────────

    def collect_dimension(self, dimension, repo_path, container_id=""):
        dispatch = {
            "build_system": self._collect_build_system,
            "dependencies": self._collect_dependencies,
            "security_details": self._collect_security_details,
            "validation": self._collect_validation,
            "error_handling": self._collect_error_handling,
            "tests": self._collect_tests,
            "workflows": self._collect_workflows,
            "configuration": self._collect_configuration,
            "logging_observability": self._collect_logging,
            "communication_patterns": self._collect_communication,
        }
        handler = dispatch.get(dimension)
        return handler(repo_path, container_id) if handler else ([], [])

    def _collect_build_system(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.build_system_collector import AngularBuildSystemCollector
        output = AngularBuildSystemCollector(repo_path).collect()
        return output.facts, output.relations

    def _collect_dependencies(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.dependency_collector import AngularDependencyCollector
        output = AngularDependencyCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_security_details(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.security_detail_collector import AngularSecurityDetailCollector
        output = AngularSecurityDetailCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_validation(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.validation_detail_collector import AngularValidationDetailCollector
        output = AngularValidationDetailCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_error_handling(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.error_detail_collector import AngularErrorDetailCollector
        output = AngularErrorDetailCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_tests(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.test_collector import AngularTestCollector
        output = AngularTestCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_workflows(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.workflow_detail_collector import AngularWorkflowDetailCollector
        output = AngularWorkflowDetailCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_configuration(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.configuration_collector import AngularConfigurationCollector
        output = AngularConfigurationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_logging(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.logging_collector import AngularLoggingCollector
        output = AngularLoggingCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_communication(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.angular.communication_collector import AngularCommunicationCollector
        output = AngularCommunicationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    # ── Component Technologies ──────────────────────────────────────────────

    def get_component_technologies(self) -> set[str]:
        return {"Angular", "React", "Vue", "Node.js", "Node.js/TypeScript"}

    def collect_components(self, container, repo_path):
        technology = container.get("technology", "")
        root_path = container.get("root_path", "")
        container_root = repo_path / root_path if root_path and root_path != "." else repo_path
        container_name = container.get("name", "frontend")

        if technology == "Angular":
            return self._collect_angular_components(container_root, container_name)
        elif technology in ("Node.js", "Node.js/TypeScript"):
            return self._collect_node_components(container_root, container_name, repo_path)
        return [], []

    def _collect_angular_components(self, container_root, container_name):
        # Lazy import to avoid circular dependency
        from ...pipelines.architecture_facts.collectors.angular import (
            AngularComponentCollector,
            AngularModuleCollector,
            AngularServiceCollector,
        )

        facts = []
        relations = []
        for CollectorClass in [AngularModuleCollector, AngularComponentCollector, AngularServiceCollector]:
            collector = CollectorClass(container_root, container_id=container_name)
            output = collector.collect()
            facts.extend(output.facts)
            relations.extend(output.relations)
        return facts, relations

    def _collect_node_components(self, container_root, container_name, repo_path):
        # Lazy import
        from ...pipelines.architecture_facts.collectors.base import RawComponent

        import fnmatch
        import os

        skip_lower = {"node_modules", ".git", "__pycache__", "dist", "build", ".venv", "venv"}

        def find_ts_js_files(root):
            results = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d.lower() not in skip_lower]
                for fname in filenames:
                    if fnmatch.fnmatch(fname, "*.ts") or fnmatch.fnmatch(fname, "*.js"):
                        results.append(Path(dirpath) / fname)
            return results

        ts_files = find_ts_js_files(container_root)
        facts = []
        for fpath in ts_files:
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for m in re.finditer(r"export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)", content):
                name = m.group(1)
                lower = name.lower()
                if lower.endswith("service"):
                    stereo = "service"
                elif lower.endswith("controller") or lower.endswith("handler"):
                    stereo = "controller"
                elif lower.endswith("model") or lower.endswith("entity"):
                    stereo = "entity"
                elif lower.endswith("spec") or lower.endswith("test"):
                    stereo = "test"
                else:
                    stereo = "component"

                try:
                    rel_path = str(fpath.relative_to(repo_path))
                except ValueError:
                    rel_path = str(fpath)

                facts.append(RawComponent(
                    name=name,
                    stereotype=stereo,
                    container_hint=container_name,
                    file_path=rel_path,
                    metadata={
                        "source": "node_export_scan",
                        "technology": "TypeScript" if fpath.suffix == ".ts" else "JavaScript",
                        "line_number": content[: m.start()].count("\n") + 1,
                    },
                ))
        return facts, []
