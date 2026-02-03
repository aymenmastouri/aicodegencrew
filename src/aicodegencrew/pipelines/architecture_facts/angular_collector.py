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
            
            component_id = self._make_component_id(class_name, rel_path)
            self.components.append(CollectedComponent(
                id=component_id,
                container=self.container_id,
                name=class_name,
                stereotype=stereotype,
                file_path=rel_path,
                evidence_ids=[ev_id]
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
