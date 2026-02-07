"""
SpringRestCollector - Extracts REST endpoint facts.

Detects:
- @RestController classes
- @RequestMapping (class and method level)
- @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping
- Path variables, request params

Output feeds -> interfaces.json (REST endpoints)
             -> components.json (controllers)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..base import DimensionCollector, CollectorOutput, RawComponent, RawInterface, RelationHint
from .....shared.utils.logger import logger


class SpringRestCollector(DimensionCollector):
    """
    Extracts REST controller and endpoint facts from Spring Boot code.
    """
    
    DIMENSION = "spring_rest"
    
    # Patterns - detect various REST endpoint sources
    CONTROLLER_PATTERN = re.compile(
        r'@(Rest)?Controller|'           # Standard @Controller/@RestController
        r'@RequestMapping\s*\(|'         # Class/Interface with @RequestMapping
        r'@FeignClient|'                 # Feign clients
        r'(?:class|interface)\s+\w*Rest\w*|'  # Classes/Interfaces with "Rest" in name
        r'(?:class|interface)\s+\w*Resource\w*|'  # JAX-RS style Resources
        r'(?:class|interface)\s+\w*Api\w*'        # Classes ending in Api
    )
    # Match both class and interface declarations
    CLASS_PATTERN = re.compile(r'^(?:public\s+)?(?:abstract\s+)?(?:class|interface)\s+([A-Z]\w*)', re.MULTILINE)
    
    # Class-level @RequestMapping
    CLASS_MAPPING_PATTERN = re.compile(
        r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
        re.DOTALL
    )
    
    # Method-level mappings
    METHOD_MAPPING_PATTERNS = [
        # @GetMapping("/path")
        (re.compile(r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', re.DOTALL), None),
        # @GetMapping() or @GetMapping without parens
        (re.compile(r'@(Get|Post|Put|Delete|Patch)Mapping\s*(?:\(\s*\))?(?!\s*\()', re.DOTALL), ""),
        # @RequestMapping(value="/path", method=RequestMethod.GET)
        (re.compile(r'@RequestMapping\s*\([^)]*value\s*=\s*["\']([^"\']+)["\'][^)]*method\s*=\s*RequestMethod\.(\w+)', re.DOTALL), None),
    ]
    
    # Method signature after annotation
    METHOD_SIGNATURE_PATTERN = re.compile(
        r'(?:public|protected|private)?\s*(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)',
        re.DOTALL
    )
    
    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._java_root: Optional[Path] = None
    
    def collect(self) -> CollectorOutput:
        """Collect REST controller and endpoint facts."""
        self._log_start()
        
        self._java_root = self._find_java_root()
        if not self._java_root:
            logger.info("[SpringRestCollector] No Java/Kotlin source root found")
            return self.output
        
        # Process Java files
        java_files = self._find_files("*.java", self._java_root)
        logger.info(f"[SpringRestCollector] Scanning {len(java_files)} Java files")
        
        for java_file in java_files:
            self._process_java_file(java_file)
        
        # Process Kotlin files
        kotlin_files = self._find_files("*.kt", self._java_root)
        if kotlin_files:
            logger.info(f"[SpringRestCollector] Scanning {len(kotlin_files)} Kotlin files")
            for kt_file in kotlin_files:
                self._process_java_file(kt_file)  # Same annotations work
        
        self._log_end()
        return self.output
    
    def _find_java_root(self) -> Optional[Path]:
        """Find Java/Kotlin source root."""
        candidates = [
            self.repo_path / "src" / "main" / "java",
            self.repo_path / "src" / "main" / "kotlin",
            self.repo_path / "backend" / "src" / "main" / "java",
            self.repo_path / "backend" / "src" / "main" / "kotlin",
        ]
        for c in candidates:
            if c.exists():
                return c
        
        for path in self.repo_path.rglob("src/main/java"):
            if path.is_dir():
                return path
        return None
    
    def _process_java_file(self, file_path: Path):
        """Process a single Java file for REST endpoints."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        
        # Check if this file has any REST-related annotations
        has_controller_annotation = self.CONTROLLER_PATTERN.search(content)
        has_mapping_methods = re.search(r'@(Get|Post|Put|Delete|Patch|Request)Mapping', content)
        
        if not has_controller_annotation and not has_mapping_methods:
            return
        
        # Get class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return
        
        class_name = class_match.group(1)
        is_interface = re.search(r'\binterface\s+' + class_name, content) is not None
        
        # Find line number - check for both class and interface
        class_line = self._find_line_number(lines, f"interface {class_name}") if is_interface else self._find_line_number(lines, f"class {class_name}")
        if class_line == 1:  # Not found with exact match, try broader search
            class_line = self._find_line_number(lines, class_name)
        
        rel_path = self._relative_path(file_path)
        
        # Create controller/rest-interface component
        stereotype = "rest_interface" if is_interface else "controller"
        controller = RawComponent(
            name=class_name,
            stereotype=stereotype,
            container_hint=self.container_id,
            module=self._derive_module(rel_path),
            file_path=rel_path,
            layer_hint="presentation",
        )
        
        annotation_type = "REST Interface" if is_interface else "@RestController"
        controller.add_evidence(
            path=rel_path,
            line_start=max(1, class_line - 2),
            line_end=class_line + 3,
            reason=f"{annotation_type}: {class_name}"
        )
        
        self.output.add_fact(controller)
        
        # Get base path from class-level @RequestMapping
        base_path = ""
        class_mapping_match = self.CLASS_MAPPING_PATTERN.search(content)
        if class_mapping_match:
            base_path = class_mapping_match.group(1)
        
        # Extract endpoints
        self._extract_endpoints(content, lines, rel_path, class_name, base_path)
    
    def _extract_endpoints(self, content: str, lines: List[str], 
                           file_path: str, controller_name: str, base_path: str):
        """Extract REST endpoints from controller."""
        
        # Find all method mappings
        for pattern, default_path in self.METHOD_MAPPING_PATTERNS:
            for match in pattern.finditer(content):
                # Determine HTTP method and path
                groups = match.groups()
                
                if len(groups) == 2:
                    if groups[1] and groups[1].startswith('/'):
                        # @GetMapping("/path") style
                        http_method = groups[0].upper()
                        path = groups[1]
                    elif groups[1] in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH'):
                        # @RequestMapping with method= style
                        path = groups[0]
                        http_method = groups[1]
                    else:
                        http_method = groups[0].upper()
                        path = groups[1] if groups[1] else ""
                elif len(groups) == 1:
                    http_method = groups[0].upper()
                    path = default_path if default_path is not None else ""
                else:
                    continue
                
                # Combine with base path
                full_path = base_path.rstrip('/') + '/' + path.lstrip('/') if path else base_path
                if not full_path:
                    full_path = "/"
                
                # Find method name
                method_name = self._find_method_name(content, match.end())
                
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                
                # Create interface
                interface = RawInterface(
                    name=f"{http_method} {full_path}",
                    type="rest_endpoint",
                    path=full_path,
                    method=http_method,
                    implemented_by_hint=controller_name,
                    container_hint=self.container_id,
                )
                
                interface.add_evidence(
                    path=file_path,
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f"REST endpoint: {http_method} {full_path}"
                )
                
                if method_name:
                    interface.metadata["handler_method"] = method_name
                
                self.output.add_fact(interface)
    
    def _find_method_name(self, content: str, start_pos: int) -> Optional[str]:
        """Find method name after annotation."""
        # Look for method signature in next 200 chars
        search_area = content[start_pos:start_pos + 300]
        match = self.METHOD_SIGNATURE_PATTERN.search(search_area)
        return match.group(1) if match else None
