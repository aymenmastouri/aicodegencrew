"""
AngularComponentCollector - Extracts Angular component facts.

Detects:
- @Component decorated classes
- Template files (inline and external)
- Styles
- Component inputs/outputs

Output feeds → components.json
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..base import DimensionCollector, CollectorOutput, RawComponent, RelationHint
from .....shared.utils.logger import logger


class AngularComponentCollector(DimensionCollector):
    """
    Extracts Angular component facts.
    """
    
    DIMENSION = "angular_components"
    
    # Patterns
    COMPONENT_PATTERN = re.compile(r'@Component\s*\(', re.DOTALL)
    DIRECTIVE_PATTERN = re.compile(r'@Directive\s*\(', re.DOTALL)
    PIPE_PATTERN = re.compile(r'@Pipe\s*\(', re.DOTALL)
    CLASS_PATTERN = re.compile(r'^(?:export\s+)?class\s+([A-Z]\w*)', re.MULTILINE)
    
    # Component metadata
    SELECTOR_PATTERN = re.compile(r'selector\s*:\s*[\'"]([^\'"]+)[\'"]')
    TEMPLATE_URL_PATTERN = re.compile(r'templateUrl\s*:\s*[\'"]([^\'"]+)[\'"]')
    STYLE_URLS_PATTERN = re.compile(r'styleUrls\s*:\s*\[([^\]]+)\]')
    STANDALONE_PATTERN = re.compile(r'standalone\s*:\s*true')
    
    # Input/Output patterns
    INPUT_PATTERN = re.compile(r'@Input\s*\(\s*(?:[\'"]([^\'"]+)[\'"])?\s*\)')
    OUTPUT_PATTERN = re.compile(r'@Output\s*\(\s*(?:[\'"]([^\'"]+)[\'"])?\s*\)')
    
    def __init__(self, repo_path: Path, container_id: str = "frontend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._angular_root: Optional[Path] = None
    
    def collect(self) -> CollectorOutput:
        """Collect Angular component facts."""
        self._log_start()
        
        self._angular_root = self._find_angular_root()
        if not self._angular_root:
            logger.info("[AngularComponentCollector] No Angular source root found")
            return self.output
        
        ts_files = self._find_files("*.ts", self._angular_root)
        
        for ts_file in ts_files:
            if ts_file.name.endswith('.spec.ts'):
                continue
            self._process_ts_file(ts_file)
        
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
        
        for path in self.repo_path.rglob("app.module.ts"):
            return path.parent
        
        return None
    
    def _process_ts_file(self, file_path: Path):
        """Process a TypeScript file for components."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)
        
        # Determine type
        if self.COMPONENT_PATTERN.search(content):
            stereotype = "component"
        elif self.DIRECTIVE_PATTERN.search(content):
            stereotype = "directive"
        elif self.PIPE_PATTERN.search(content):
            stereotype = "pipe"
        else:
            return
        
        # Get class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return
        
        class_name = class_match.group(1)
        class_line = self._find_line_number(lines, f"class {class_name}")
        
        # Extract metadata
        selector_match = self.SELECTOR_PATTERN.search(content)
        selector = selector_match.group(1) if selector_match else None
        
        template_match = self.TEMPLATE_URL_PATTERN.search(content)
        template_url = template_match.group(1) if template_match else None
        
        is_standalone = bool(self.STANDALONE_PATTERN.search(content))
        
        # Count inputs/outputs
        inputs = len(self.INPUT_PATTERN.findall(content))
        outputs = len(self.OUTPUT_PATTERN.findall(content))
        
        # Create component
        component = RawComponent(
            name=class_name,
            stereotype=stereotype,
            container_hint=self.container_id,
            module=self._derive_module(rel_path),
            file_path=rel_path,
            layer_hint="presentation",
        )
        
        if selector:
            component.metadata["selector"] = selector
        if template_url:
            component.metadata["template"] = template_url
        if is_standalone:
            component.metadata["standalone"] = True
            component.tags.append("standalone")
        if inputs > 0:
            component.metadata["inputs"] = inputs
        if outputs > 0:
            component.metadata["outputs"] = outputs
        
        component.add_evidence(
            path=rel_path,
            line_start=class_line - 5,
            line_end=class_line + 3,
            reason=f"@{stereotype.title()}: {class_name}" + (f" ({selector})" if selector else "")
        )
        
        self.output.add_fact(component)
