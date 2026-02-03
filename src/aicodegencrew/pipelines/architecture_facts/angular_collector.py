"""Angular / TypeScript collector for architecture facts.

Extracts:
- @NgModule: module components
- @Component: UI components
- @Injectable / Services: service components
- Routes: interfaces
- HttpClient usage: relations to backend
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

from .base_collector import (
    BaseCollector,
    CollectedComponent,
    CollectedInterface,
    CollectedRelation,
    CollectedEvidence,
)
from ...shared.utils.logger import logger


class AngularCollector(BaseCollector):
    """Collector for Angular / TypeScript projects."""
    
    # Decorator patterns
    MODULE_PATTERN = re.compile(r'@NgModule\s*\(')
    COMPONENT_PATTERN = re.compile(r'@Component\s*\(')
    INJECTABLE_PATTERN = re.compile(r'@Injectable\s*\(')
    DIRECTIVE_PATTERN = re.compile(r'@Directive\s*\(')
    PIPE_PATTERN = re.compile(r'@Pipe\s*\(')
    
    # Class pattern - matches real class definitions (starting with capital letter)
    # Uses MULTILINE to match at line start, avoiding matches in comments like "the class as"
    CLASS_PATTERN = re.compile(r'^(?:export\s+)?(?:abstract\s+)?class\s+([A-Z]\w*)', re.MULTILINE)
    
    # Route patterns
    ROUTE_PATTERN = re.compile(r'\{\s*path:\s*[\'"]([^\'"]+)[\'"].*?component:\s*(\w+)')
    LAZY_ROUTE_PATTERN = re.compile(r'\{\s*path:\s*[\'"]([^\'"]+)[\'"].*?loadChildren')
    
    # HttpClient usage pattern
    HTTP_CALL_PATTERN = re.compile(r'this\.http\.(get|post|put|delete|patch)\s*[<(][\'"]?([^\'")\s>]+)')
    
    def __init__(self, repo_path: Path, container_id: str = "frontend", angular_root: Optional[Path] = None):
        super().__init__(repo_path, container_id)
        self.angular_root = angular_root or self._find_angular_root()
        self._component_names: Set[str] = set()
        self._service_names: Set[str] = set()
    
    def _find_angular_root(self) -> Optional[Path]:
        """Find the Angular source root directory."""
        # Look for angular.json
        angular_json = self.repo_path / "angular.json"
        if angular_json.exists():
            return self.repo_path / "src" / "app"
        
        # Check common locations
        candidates = [
            self.repo_path / "src" / "app",
            self.repo_path / "frontend" / "src" / "app",
            self.repo_path / "client" / "src" / "app",
            self.repo_path / "web" / "src" / "app",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        # Search for app.module.ts
        for path in self.repo_path.rglob("app.module.ts"):
            return path.parent
        
        return None
    
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """Collect Angular architecture facts."""
        if not self.angular_root:
            logger.info(f"[AngularCollector] No Angular source root found in {self.repo_path}")
            return [], [], [], {}
        
        logger.info(f"[AngularCollector] Scanning {self.angular_root}")
        
        ts_files = self._find_files("*.ts", self.angular_root)
        logger.info(f"[AngularCollector] Found {len(ts_files)} TypeScript files")
        
        # First pass: collect components and services
        for ts_file in ts_files:
            if ts_file.name.endswith('.spec.ts'):
                continue
            self._process_ts_file(ts_file)
        
        # Second pass: collect routes
        for ts_file in ts_files:
            if 'routing' in ts_file.name.lower() or 'routes' in ts_file.name.lower():
                self._extract_routes(ts_file)
        
        # Third pass: collect HTTP relations
        for ts_file in ts_files:
            if ts_file.name.endswith('.service.ts'):
                self._extract_http_calls(ts_file)
        
        logger.info(f"[AngularCollector] Collected: {len(self.components)} components, {len(self.interfaces)} interfaces, {len(self.relations)} relations")
        
        return self.components, self.interfaces, self.relations, self.evidence
    
    def _process_ts_file(self, file_path: Path):
        """Process a single TypeScript file."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Find class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return
        
        class_name = class_match.group(1)
        class_line = self._find_line_number(lines, class_match.group(0))
        
        # Check for decorators
        stereotype = None
        annotation_reason = None
        
        if self.MODULE_PATTERN.search(content):
            stereotype = "module"
            annotation_reason = "@NgModule decorated class"
        elif self.COMPONENT_PATTERN.search(content):
            stereotype = "component"
            annotation_reason = "@Component decorated class"
            self._component_names.add(class_name)
        elif self.INJECTABLE_PATTERN.search(content):
            stereotype = "service"
            annotation_reason = "@Injectable decorated class"
            self._service_names.add(class_name)
        elif self.DIRECTIVE_PATTERN.search(content):
            stereotype = "directive"
            annotation_reason = "@Directive decorated class"
        elif self.PIPE_PATTERN.search(content):
            stereotype = "pipe"
            annotation_reason = "@Pipe decorated class"
        
        if stereotype:
            class_end = self._find_class_end(lines, class_line)
            
            ev_id = self._add_evidence(
                rel_path,
                class_line,
                class_end,
                annotation_reason,
                prefix=f"ev_{stereotype}"
            )
            
            # Derive module from file path (e.g., "workflow/components" -> "workflow.components")
            module = self._derive_module_from_path(rel_path)
            
            component_id = self._make_component_id(class_name, rel_path)
            self.components.append(CollectedComponent(
                id=component_id,
                container=self.container_id,
                name=class_name,
                stereotype=stereotype,
                file_path=rel_path,
                evidence_ids=[ev_id],
                module=module
            ))
    
    def _extract_routes(self, file_path: Path):
        """Extract route definitions."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Find routes
        for match in self.ROUTE_PATTERN.finditer(content):
            path = match.group(1)
            component = match.group(2)
            
            line_num = self._find_line_number(lines, match.group(0)[:30])
            ev_id = self._add_evidence(
                rel_path,
                line_num,
                line_num + 3,
                f"Route definition for path '{path}'",
                prefix="ev_route"
            )
            
            interface_id = f"route_{self._make_component_id(path.replace('/', '_') or 'root')}"
            self.interfaces.append(CollectedInterface(
                id=interface_id,
                container=self.container_id,
                type="route",
                path=f"/{path}" if not path.startswith('/') else path,
                method=None,
                implemented_by=component,
                evidence_ids=[ev_id]
            ))
        
        # Find lazy-loaded routes
        for match in self.LAZY_ROUTE_PATTERN.finditer(content):
            path = match.group(1)
            
            line_num = self._find_line_number(lines, match.group(0)[:30])
            ev_id = self._add_evidence(
                rel_path,
                line_num,
                line_num + 3,
                f"Lazy-loaded route for path '{path}'",
                prefix="ev_route"
            )
            
            interface_id = f"route_lazy_{self._make_component_id(path.replace('/', '_') or 'root')}"
            self.interfaces.append(CollectedInterface(
                id=interface_id,
                container=self.container_id,
                type="route",
                path=f"/{path}" if not path.startswith('/') else path,
                method=None,
                implemented_by="lazy-module",
                evidence_ids=[ev_id]
            ))
    
    def _extract_http_calls(self, file_path: Path):
        """Extract HTTP calls to backend APIs."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Find class name (service)
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return
        
        class_name = class_match.group(1)
        from_id = self._make_component_id(class_name)
        
        # Find HTTP calls
        for match in self.HTTP_CALL_PATTERN.finditer(content):
            http_method = match.group(1).upper()
            url = match.group(2)
            
            line_num = self._find_line_number(lines, match.group(0)[:30])
            ev_id = self._add_evidence(
                rel_path,
                line_num,
                line_num + 2,
                f"HTTP {http_method} call to {url}",
                prefix="ev_http"
            )
            
            # Create relation to backend
            self.relations.append(CollectedRelation(
                from_id=from_id,
                to_id="backend",  # Assumes backend container exists
                type="uses",
                evidence_ids=[ev_id]
            ))
    
    def _find_line_number(self, lines: List[str], search_text: str) -> int:
        """Find the line number containing search_text."""
        search_clean = search_text.replace('\n', ' ').strip()[:40]
        for i, line in enumerate(lines, 1):
            if search_clean in line:
                return i
        return 1
    
    def _find_class_end(self, lines: List[str], start_line: int) -> int:
        """Find approximate end of class."""
        brace_count = 0
        started = False
        
        for i, line in enumerate(lines[start_line - 1:], start_line):
            brace_count += line.count('{') - line.count('}')
            if '{' in line:
                started = True
            if started and brace_count == 0:
                return i
        
        return min(start_line + 100, len(lines))
    
    # =========================================================================
    # FRONTEND METADATA EXTRACTION
    # =========================================================================
    
    def extract_frontend_metadata(self) -> Dict:
        """
        Extract additional frontend-specific metadata from the Angular project.
        
        Returns dict with:
        - angular_version: Angular major version
        - routing_strategy: lazy loading, eager, etc.
        - state_management: NgRx, services, etc.
        - ui_library: Material, PrimeNG, etc.
        - i18n_config: Internationalization setup
        - build_config: Build/bundle configuration
        """
        import json
        
        metadata = {
            "angular_version": None,
            "routing_strategy": "unknown",
            "state_management": "services",  # default
            "ui_library": None,
            "i18n_config": {},
            "build_config": {},
            "environments": [],
        }
        
        # Read angular.json for project config
        angular_json = self.repo_path / "angular.json"
        if angular_json.exists():
            self._parse_angular_json(angular_json, metadata)
        
        # Read package.json for dependencies
        package_json = self.repo_path / "package.json"
        if not package_json.exists():
            package_json = self.repo_path / "frontend" / "package.json"
        
        if package_json.exists():
            self._parse_package_json_metadata(package_json, metadata)
        
        # Detect routing strategy from app-routing.module.ts
        self._detect_routing_strategy(metadata)
        
        # Detect environments
        self._detect_environments(metadata)
        
        logger.info(f"[AngularCollector] Extracted frontend metadata: Angular {metadata['angular_version']}, UI={metadata['ui_library']}")
        return metadata
    
    def _parse_angular_json(self, angular_json: Path, metadata: Dict):
        """Parse angular.json for build config."""
        import json
        try:
            with open(angular_json, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Get default project
            default_project = config.get("defaultProject")
            projects = config.get("projects", {})
            
            if default_project and default_project in projects:
                project = projects[default_project]
                architect = project.get("architect", {})
                
                # Build config
                build_config = architect.get("build", {})
                if build_config:
                    options = build_config.get("options", {})
                    metadata["build_config"]["output_path"] = options.get("outputPath")
                    metadata["build_config"]["styles"] = options.get("styles", [])
                    metadata["build_config"]["scripts"] = options.get("scripts", [])
                
                # Detect i18n
                if "i18n" in project:
                    metadata["i18n_config"]["enabled"] = True
                    metadata["i18n_config"]["locales"] = list(project["i18n"].get("locales", {}).keys())
        
        except Exception as e:
            logger.warning(f"[AngularCollector] Failed to parse angular.json: {e}")
    
    def _parse_package_json_metadata(self, package_json: Path, metadata: Dict):
        """Parse package.json for frontend metadata."""
        import json
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            
            deps = pkg.get("dependencies", {})
            
            # Angular version
            if "@angular/core" in deps:
                version = deps["@angular/core"].lstrip("^~")
                metadata["angular_version"] = version.split(".")[0]  # Major version
            
            # Detect UI library
            ui_libs = {
                "@angular/material": "Angular Material",
                "primeng": "PrimeNG",
                "ng-zorro-antd": "NG-ZORRO",
                "@ng-bootstrap/ng-bootstrap": "ng-bootstrap",
                "ngx-bootstrap": "ngx-bootstrap",
            }
            for lib, name in ui_libs.items():
                if lib in deps:
                    metadata["ui_library"] = name
                    break
            
            # Detect state management
            if "@ngrx/store" in deps:
                metadata["state_management"] = "NgRx"
            elif "ngxs" in str(deps).lower():
                metadata["state_management"] = "NGXS"
            elif "akita" in str(deps).lower():
                metadata["state_management"] = "Akita"
        
        except Exception as e:
            logger.warning(f"[AngularCollector] Failed to parse package.json: {e}")
    
    def _detect_routing_strategy(self, metadata: Dict):
        """Detect routing strategy (lazy loading, etc.)."""
        # Search for routing modules
        routing_files = list(self.repo_path.rglob("*-routing.module.ts"))
        if not routing_files:
            routing_files = list(self.repo_path.rglob("app.routes.ts"))
        
        has_lazy_loading = False
        for routing_file in routing_files:
            try:
                with open(routing_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "loadChildren" in content or "loadComponent" in content:
                    has_lazy_loading = True
                    break
            except Exception:
                continue
        
        metadata["routing_strategy"] = "lazy-loading" if has_lazy_loading else "eager"
    
    def _detect_environments(self, metadata: Dict):
        """Detect environment configurations."""
        env_dir = self.repo_path / "src" / "environments"
        if not env_dir.exists():
            env_dir = self.repo_path / "frontend" / "src" / "environments"
        
        if env_dir.exists():
            for env_file in env_dir.glob("environment*.ts"):
                env_name = env_file.stem.replace("environment.", "").replace("environment", "default")
                metadata["environments"].append(env_name)
