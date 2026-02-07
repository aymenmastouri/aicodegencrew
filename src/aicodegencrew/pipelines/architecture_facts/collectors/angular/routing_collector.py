"""
AngularRoutingCollector - Extracts routing facts.

Detects:
- Route definitions
- Route guards (CanActivate, CanDeactivate)
- Lazy loaded routes
- Route parameters

Output feeds -> interfaces.json (routes)
             -> relations (route -> component)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..base import DimensionCollector, CollectorOutput, RawInterface, RelationHint
from .....shared.utils.logger import logger


class AngularRoutingCollector(DimensionCollector):
    """
    Extracts Angular routing facts.
    """
    
    DIMENSION = "angular_routing"
    
    # Patterns
    ROUTE_PATTERN = re.compile(
        r'\{\s*path\s*:\s*[\'"]([^\'"]*)[\'"]'
        r'(?:[^}]*?component\s*:\s*(\w+))?'
        r'(?:[^}]*?loadChildren)?',
        re.DOTALL
    )
    
    LAZY_ROUTE_PATTERN = re.compile(
        r'path\s*:\s*[\'"]([^\'"]+)[\'"]'
        r'[^}]*loadChildren\s*:\s*\(\)\s*=>\s*import\s*\(\s*[\'"]([^\'"]+)[\'"]'
    )
    
    GUARD_PATTERN = re.compile(
        r'(canActivate|canDeactivate|canLoad|canActivateChild)\s*:\s*\[([^\]]+)\]'
    )
    
    ROUTER_MODULE_PATTERN = re.compile(r'RouterModule\.forRoot|RouterModule\.forChild')
    
    def __init__(self, repo_path: Path, container_id: str = "frontend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._angular_root: Optional[Path] = None
    
    def collect(self) -> CollectorOutput:
        """Collect Angular routing facts."""
        self._log_start()
        
        self._angular_root = self._find_angular_root()
        if not self._angular_root:
            logger.info("[AngularRoutingCollector] No Angular source root found")
            return self.output
        
        # Find routing files
        routing_files = []
        for ts_file in self._find_files("*.ts", self._angular_root):
            if 'routing' in ts_file.name.lower() or 'routes' in ts_file.name.lower():
                routing_files.append(ts_file)
            else:
                # Check content for RouterModule
                content = self._read_file_content(ts_file)
                if self.ROUTER_MODULE_PATTERN.search(content):
                    routing_files.append(ts_file)
        
        logger.info(f"[AngularRoutingCollector] Found {len(routing_files)} routing files")
        
        for routing_file in routing_files:
            self._process_routing_file(routing_file)
        
        self._log_end()
        return self.output
    
    def _find_angular_root(self) -> Optional[Path]:
        """Find Angular source root."""
        if (self.repo_path / "angular.json").exists():
            if (self.repo_path / "src" / "app").exists():
                return self.repo_path / "src" / "app"
        
        candidates = [
            self.repo_path / "src" / "app",
            self.repo_path / "frontend" / "src" / "app",
        ]
        for c in candidates:
            if c.exists():
                return c
        
        return None
    
    def _process_routing_file(self, file_path: Path):
        """Process a routing file."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)
        
        # Extract regular routes
        for match in self.ROUTE_PATTERN.finditer(content):
            path = match.group(1)
            component = match.group(2)
            
            line_num = content[:match.start()].count('\n') + 1
            
            route = RawInterface(
                name=f"/{path}" if path else "/",
                type="route",
                path=f"/{path}" if path else "/",
                method=None,
                implemented_by_hint=component or "",
                container_hint=self.container_id,
            )
            
            route.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"Angular route: /{path}"
            )
            
            if component:
                route.metadata["component"] = component
            
            self.output.add_fact(route)
            
            # Create relation to component
            if component:
                relation = RelationHint(
                    from_name=f"route:/{path}",
                    to_name=component,
                    type="renders",
                    to_stereotype_hint="component",
                )
                self.output.add_relation(relation)
        
        # Extract lazy routes
        for match in self.LAZY_ROUTE_PATTERN.finditer(content):
            path = match.group(1)
            module_path = match.group(2)
            
            line_num = content[:match.start()].count('\n') + 1
            
            route = RawInterface(
                name=f"/{path}",
                type="route",
                path=f"/{path}",
                method=None,
                implemented_by_hint="",
                container_hint=self.container_id,
            )
            
            route.metadata["lazy"] = True
            route.metadata["module_path"] = module_path
            route.tags.append("lazy-loaded")
            
            route.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 3,
                reason=f"Lazy loaded route: /{path}"
            )
            
            self.output.add_fact(route)
        
        # Extract guards
        self._extract_guards(content, rel_path)
    
    def _extract_guards(self, content: str, file_path: str):
        """Extract route guards."""
        for match in self.GUARD_PATTERN.finditer(content):
            guard_type = match.group(1)
            guards_list = match.group(2)
            
            # Parse guard names
            for guard in guards_list.split(','):
                guard = guard.strip()
                if guard and not guard.startswith('...'):
                    guard_match = re.match(r'([A-Z]\w+)', guard)
                    if guard_match:
                        guard_name = guard_match.group(1)
                        
                        guard_fact = RawInterface(
                            name=guard_name,
                            type="route_guard",
                            path=None,
                            method=None,
                            implemented_by_hint=guard_name,
                            container_hint=self.container_id,
                        )
                        
                        guard_fact.metadata["guard_type"] = guard_type
                        
                        line_num = content[:match.start()].count('\n') + 1
                        guard_fact.add_evidence(
                            path=file_path,
                            line_start=line_num,
                            line_end=line_num + 1,
                            reason=f"Route guard: {guard_name} ({guard_type})"
                        )
                        
                        self.output.add_fact(guard_fact)
