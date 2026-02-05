"""
AngularModuleCollector - Extracts NgModule facts.

Detects:
- @NgModule declarations
- Lazy loaded modules
- Feature modules
- Shared modules
- Module dependencies (imports)

Output feeds → components.json (modules)
             → relations (module imports)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..base import DimensionCollector, CollectorOutput, RawComponent, RelationHint
from .....shared.utils.logger import logger


class AngularModuleCollector(DimensionCollector):
    """
    Extracts Angular module facts.
    """
    
    DIMENSION = "angular_modules"
    
    # Patterns
    MODULE_PATTERN = re.compile(r'@NgModule\s*\(', re.DOTALL)
    CLASS_PATTERN = re.compile(r'^(?:export\s+)?class\s+([A-Z]\w*)', re.MULTILINE)
    
    # Module metadata patterns
    IMPORTS_PATTERN = re.compile(r'imports\s*:\s*\[([^\]]+)\]', re.DOTALL)
    DECLARATIONS_PATTERN = re.compile(r'declarations\s*:\s*\[([^\]]+)\]', re.DOTALL)
    EXPORTS_PATTERN = re.compile(r'exports\s*:\s*\[([^\]]+)\]', re.DOTALL)
    PROVIDERS_PATTERN = re.compile(r'providers\s*:\s*\[([^\]]+)\]', re.DOTALL)
    
    # Lazy loading pattern
    LAZY_LOAD_PATTERN = re.compile(
        r'loadChildren\s*:\s*\(\)\s*=>\s*import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
    )
    
    def __init__(self, repo_path: Path, container_id: str = "frontend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._angular_root: Optional[Path] = None
    
    def collect(self) -> CollectorOutput:
        """Collect Angular module facts."""
        self._log_start()
        
        self._angular_root = self._find_angular_root()
        if not self._angular_root:
            logger.info("[AngularModuleCollector] No Angular source root found")
            return self.output
        
        ts_files = self._find_files("*.module.ts", self._angular_root)
        logger.info(f"[AngularModuleCollector] Found {len(ts_files)} module files")
        
        for ts_file in ts_files:
            self._process_module_file(ts_file)
        
        self._log_end()
        return self.output
    
    def _find_angular_root(self) -> Optional[Path]:
        """Find Angular source root."""
        # Look for angular.json
        if (self.repo_path / "angular.json").exists():
            if (self.repo_path / "src" / "app").exists():
                return self.repo_path / "src" / "app"
        
        # Common locations
        candidates = [
            self.repo_path / "src" / "app",
            self.repo_path / "frontend" / "src" / "app",
            self.repo_path / "client" / "src" / "app",
        ]
        for c in candidates:
            if c.exists():
                return c
        
        # Search for app.module.ts
        for path in self.repo_path.rglob("app.module.ts"):
            return path.parent
        
        return None
    
    def _process_module_file(self, file_path: Path):
        """Process an Angular module file."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)
        
        if not self.MODULE_PATTERN.search(content):
            return
        
        # Get class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return
        
        module_name = class_match.group(1)
        class_line = self._find_line_number(lines, f"class {module_name}")
        
        # Determine module type
        module_type = self._determine_module_type(module_name, file_path, content)
        
        # Extract module metadata
        imports = self._extract_array(content, self.IMPORTS_PATTERN)
        declarations = self._extract_array(content, self.DECLARATIONS_PATTERN)
        exports = self._extract_array(content, self.EXPORTS_PATTERN)
        providers = self._extract_array(content, self.PROVIDERS_PATTERN)
        
        # Create module component
        module = RawComponent(
            name=module_name,
            stereotype="module",
            container_hint=self.container_id,
            module=self._derive_module(rel_path),
            file_path=rel_path,
            layer_hint="presentation",
        )
        
        module.tags.append(f"module_type:{module_type}")
        module.metadata["module_type"] = module_type
        module.metadata["declarations_count"] = len(declarations)
        module.metadata["imports_count"] = len(imports)
        
        if exports:
            module.metadata["exports"] = exports[:10]  # Limit for size
        if providers:
            module.metadata["providers"] = providers[:10]
        
        module.add_evidence(
            path=rel_path,
            line_start=class_line - 5,
            line_end=class_line + 3,
            reason=f"@NgModule: {module_name} ({module_type})"
        )
        
        self.output.add_fact(module)
        
        # Create relations for imports
        for imported in imports:
            if imported.endswith('Module') and imported != module_name:
                relation = RelationHint(
                    from_name=module_name,
                    to_name=imported,
                    type="imports",
                    from_stereotype_hint="module",
                    to_stereotype_hint="module",
                )
                self.output.add_relation(relation)
    
    def _determine_module_type(self, name: str, path: Path, content: str) -> str:
        """Determine the type of Angular module."""
        name_lower = name.lower()
        path_str = str(path).lower()
        
        if name == "AppModule" or "app.module" in path_str:
            return "root"
        elif "routing" in name_lower or "routing" in path_str:
            return "routing"
        elif "shared" in name_lower or "shared" in path_str:
            return "shared"
        elif "core" in name_lower or "core" in path_str:
            return "core"
        elif self.LAZY_LOAD_PATTERN.search(content):
            return "lazy"
        else:
            return "feature"
    
    def _extract_array(self, content: str, pattern: re.Pattern) -> List[str]:
        """Extract array items from @NgModule metadata."""
        match = pattern.search(content)
        if not match:
            return []
        
        array_content = match.group(1)
        # Clean up and split
        items = []
        for item in array_content.split(','):
            item = item.strip()
            # Remove comments and whitespace
            item = re.sub(r'//.*$', '', item, flags=re.MULTILINE)
            item = re.sub(r'/\*.*?\*/', '', item, flags=re.DOTALL)
            item = item.strip()
            if item and not item.startswith('...'):
                # Get just the identifier
                match = re.match(r'([A-Z]\w+)', item)
                if match:
                    items.append(match.group(1))
        
        return items
