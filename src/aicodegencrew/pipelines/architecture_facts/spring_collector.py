"""Spring Boot / Java collector for architecture facts.

Extracts:
- @RestController: controller components + REST interfaces
- @Service: service components
- @Repository: repository components
- @Component: generic components
- Constructor injection: relations
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


class SpringCollector(BaseCollector):
    """Collector for Spring Boot / Java projects."""
    
    # Annotation patterns
    CONTROLLER_PATTERN = re.compile(r'@(Rest)?Controller')
    SERVICE_PATTERN = re.compile(r'@Service')
    REPOSITORY_PATTERN = re.compile(r'@Repository')
    COMPONENT_PATTERN = re.compile(r'@Component')
    ENTITY_PATTERN = re.compile(r'@Entity')
    
    # Request mapping patterns - improved to handle multi-line and no-value cases
    # Pattern for single path: @GetMapping, @GetMapping("/path"), @GetMapping(value = "/path", ...)
    REQUEST_MAPPING_SINGLE_PATTERN = re.compile(
        r'@(Request|Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
        re.DOTALL
    )
    # Pattern for empty mapping: @GetMapping(), @PostMapping()
    REQUEST_MAPPING_EMPTY_PATTERN = re.compile(
        r'@(Request|Get|Post|Put|Delete|Patch)Mapping\s*\(\s*\)',
        re.DOTALL
    )
    # Pattern for annotation without parameters: @GetMapping, @PostMapping (no parentheses)
    REQUEST_MAPPING_NO_PARAMS_PATTERN = re.compile(
        r'@(Get|Post|Put|Delete|Patch)Mapping(?!\s*\()',
        re.DOTALL
    )
    # Pattern for @RequestMapping with method attribute
    REQUEST_MAPPING_WITH_METHOD_PATTERN = re.compile(
        r'@RequestMapping\s*\([^)]*value\s*=\s*["\']([^"\']+)["\'][^)]*method\s*=\s*RequestMethod\.(\w+)',
        re.DOTALL
    )
    CLASS_MAPPING_PATTERN = re.compile(
        r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
        re.DOTALL
    )
    
    # Array path pattern for @GetMapping(value = {"/path1", "/path2"})
    ARRAY_PATH_PATTERN = re.compile(
        r'@(Request|Get|Post|Put|Delete|Patch)Mapping\s*\([^)]*value\s*=\s*\{([^}]+)\}',
        re.DOTALL
    )
    
    # Class definition pattern - matches real class definitions (starting with capital letter)
    # Uses MULTILINE to match at line start, avoiding matches in comments like "this class is"
    CLASS_PATTERN = re.compile(r'^(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+([A-Z]\w*)', re.MULTILINE)
    
    # Constructor injection pattern
    CONSTRUCTOR_PATTERN = re.compile(r'(?:public\s+)?(\w+)\s*\([^)]*\)')
    FIELD_INJECTION_PATTERN = re.compile(r'(?:private|protected)\s+(?:final\s+)?(\w+)\s+(\w+)\s*;')
    
    def __init__(self, repo_path: Path, container_id: str = "backend", java_root: Optional[Path] = None):
        super().__init__(repo_path, container_id)
        self.java_root = java_root or self._find_java_root()
        self._component_names: Set[str] = set()
        # Track interfaces and their REST mappings for later association
        self._interface_rest_mappings: Dict[str, List[dict]] = {}
        # Track interface -> implementation mapping (e.g., UserService -> UserServiceImpl)
        self._interface_to_impl: Dict[str, str] = {}
    
    def _find_java_root(self) -> Optional[Path]:
        """Find the Java source root directory."""
        candidates = [
            self.repo_path / "src" / "main" / "java",
            self.repo_path / "backend" / "src" / "main" / "java",
            self.repo_path / "app" / "src" / "main" / "java",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        # Search for any src/main/java
        for path in self.repo_path.rglob("src/main/java"):
            if path.is_dir():
                return path
        
        return None
    
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """Collect Spring Boot architecture facts."""
        if not self.java_root:
            logger.info(f"[SpringCollector] No Java source root found in {self.repo_path}")
            return [], [], [], {}
        
        logger.info(f"[SpringCollector] Scanning {self.java_root}")
        
        java_files = self._find_files("*.java", self.java_root)
        logger.info(f"[SpringCollector] Found {len(java_files)} Java files")
        
        # First pass: collect interface REST mappings
        for java_file in java_files:
            self._scan_interface_for_rest_mappings(java_file)
        
        # Second pass: process implementation classes
        for java_file in java_files:
            self._process_java_file(java_file)
        
        # Collect relations based on constructor/field injection
        self._collect_relations(java_files)
        
        logger.info(f"[SpringCollector] Collected: {len(self.components)} components, {len(self.interfaces)} interfaces, {len(self.relations)} relations")
        
        return self.components, self.interfaces, self.relations, self.evidence
    
    def _process_java_file(self, file_path: Path):
        """Process a single Java file."""
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
        
        # Check for stereotypes
        stereotype = None
        annotation_reason = None
        
        if self.CONTROLLER_PATTERN.search(content):
            stereotype = "controller"
            annotation_reason = "@RestController or @Controller annotated class"
        elif self.SERVICE_PATTERN.search(content):
            stereotype = "service"
            annotation_reason = "@Service annotated class"
        elif self.REPOSITORY_PATTERN.search(content):
            stereotype = "repository"
            annotation_reason = "@Repository annotated class"
        elif self.COMPONENT_PATTERN.search(content):
            stereotype = "component"
            annotation_reason = "@Component annotated class"
        elif self.ENTITY_PATTERN.search(content):
            stereotype = "entity"
            annotation_reason = "@Entity annotated class"
        
        if stereotype:
            # Find class line range (approximate)
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
                evidence_ids=[ev_id],
                module=self._derive_module_from_path(rel_path)
            ))
            self._component_names.add(class_name)
            
            # Track interface implementations for relation mapping
            implements_match = re.search(r'implements\s+([\w\s,]+)(?:\s*\{|$)', content)
            if implements_match:
                interfaces_str = implements_match.group(1)
                interface_names = [name.strip() for name in interfaces_str.split(',')]
                for interface_name in interface_names:
                    self._interface_to_impl[interface_name] = class_name
            
            # Extract REST endpoints for controllers
            if stereotype == "controller":
                # First extract from class itself
                self._extract_endpoints(content, lines, rel_path, class_name, component_id)
                
                # Then check for implemented interfaces with REST mappings
                self._extract_endpoints_from_interfaces(content, class_name)
    
    def _extract_endpoints(self, content: str, lines: List[str], rel_path: str, class_name: str, component_id: str):
        """Extract REST endpoints from controller."""
        # Get base path from class-level @RequestMapping
        base_path = ""
        class_mapping = self.CLASS_MAPPING_PATTERN.search(content)
        if class_mapping:
            base_path = class_mapping.group(1)
        
        # Track which annotations we've already processed
        processed_positions = set()
        
        # Mark class-level @RequestMapping as processed (should not create endpoint)
        if class_mapping:
            processed_positions.add((class_mapping.start(), class_mapping.end()))
        
        # First, check for array paths: @GetMapping(value = {"/path1", "/path2"})
        for array_match in self.ARRAY_PATH_PATTERN.finditer(content):
            method_type = array_match.group(1)
            paths_str = array_match.group(2)
            
            # Mark this position as processed
            processed_positions.add((array_match.start(), array_match.end()))
            
            # Extract individual paths from the array
            paths = re.findall(r'["\']([^"\']+)["\']', paths_str)
            
            for path in paths:
                self._create_interface(
                    method_type, path, base_path, content, lines, rel_path, class_name, array_match.group(0)
                )
        
        # Check for @RequestMapping with method attribute
        for match in self.REQUEST_MAPPING_WITH_METHOD_PATTERN.finditer(content):
            # Skip if already processed
            overlap = False
            for start, end in processed_positions:
                if match.start() >= start and match.end() <= end:
                    overlap = True
                    break
            if overlap:
                continue
            
            path = match.group(1)
            http_method_name = match.group(2)  # GET, POST, etc.
            
            # Convert method name to proper case for _create_interface
            method_type_map = {
                "GET": "Get",
                "POST": "Post",
                "PUT": "Put",
                "DELETE": "Delete",
                "PATCH": "Patch"
            }
            method_type = method_type_map.get(http_method_name.upper(), "Request")
            
            processed_positions.add((match.start(), match.end()))
            
            # For @RequestMapping, path is already full (no base path)
            self._create_interface_absolute(
                method_type, path, content, lines, rel_path, class_name, match.group(0)
            )
        
        # Then find single-path method-level mappings
        for match in self.REQUEST_MAPPING_SINGLE_PATTERN.finditer(content):
            # Skip if already processed
            overlap = False
            for start, end in processed_positions:
                if match.start() >= start and match.end() <= end:
                    overlap = True
                    break
            if overlap:
                continue
            
            method_type = match.group(1)
            path = match.group(2)
            
            self._create_interface(
                method_type, path, base_path, content, lines, rel_path, class_name, match.group(0)
            )
        
        # Finally, handle empty mappings: @GetMapping(), @PostMapping()
        for match in self.REQUEST_MAPPING_EMPTY_PATTERN.finditer(content):
            # Skip if already processed
            overlap = False
            for start, end in processed_positions:
                if match.start() >= start and match.end() <= end:
                    overlap = True
                    break
            if overlap:
                continue
            
            method_type = match.group(1)
            
            self._create_interface(
                method_type, "", base_path, content, lines, rel_path, class_name, match.group(0)
            )
        
        # Finally, handle annotations without parameters: @GetMapping, @PostMapping
        for match in self.REQUEST_MAPPING_NO_PARAMS_PATTERN.finditer(content):
            # Skip if already processed
            overlap = False
            for start, end in processed_positions:
                if match.start() >= start and match.end() <= end:
                    overlap = True
                    break
            if overlap:
                continue
            
            method_type = match.group(1)
            
            self._create_interface(
                method_type, "", base_path, content, lines, rel_path, class_name, match.group(0)
            )
    
    def _create_interface_absolute(self, method_type: str, path: str, content: str, 
                         lines: List[str], rel_path: str, class_name: str, match_text: str):
        """Create REST interface with absolute path (no base path combining)."""
        full_path = path if path.startswith("/") else f"/{path}"
        
        # Determine HTTP method
        http_method = "GET"
        if method_type == "Post":
            http_method = "POST"
        elif method_type == "Put":
            http_method = "PUT"
        elif method_type == "Delete":
            http_method = "DELETE"
        elif method_type == "Patch":
            http_method = "PATCH"
        
        line_num = self._find_line_number(lines, match_text)
        ev_id = self._add_evidence(
            rel_path,
            line_num,
            line_num + 5,
            f"@{method_type}Mapping endpoint",
            prefix="ev_api"
        )
        
        interface_id = f"api_{self._get_component_id_base(class_name)}_{len(self.interfaces)}"
        self.interfaces.append(CollectedInterface(
            id=interface_id,
            container=self.container_id,
            type="REST",
            path=full_path,
            method=http_method,
            implemented_by=class_name,
            evidence_ids=[ev_id]
        ))
    
    def _create_interface(self, method_type: str, path: str, base_path: str, content: str, 
                         lines: List[str], rel_path: str, class_name: str, match_text: str):
        """Create a single REST interface entry."""
        # Build full path - In Spring, paths always combine (even if method path starts with /)
        if not path:
            # @GetMapping() without path uses base path only
            full_path = base_path if base_path else "/"
        elif base_path:
            # Combine base path with method path
            # Remove trailing slash from base, leading slash from path
            base_clean = base_path.rstrip("/")
            path_clean = path.lstrip("/")
            full_path = f"{base_clean}/{path_clean}" if path_clean else base_clean
        else:
            # No base path, use method path as-is (ensure leading slash)
            full_path = path if path.startswith("/") else f"/{path}"
        
        # Determine HTTP method
        http_method = "GET"
        if method_type == "Post":
            http_method = "POST"
        elif method_type == "Put":
            http_method = "PUT"
        elif method_type == "Delete":
            http_method = "DELETE"
        elif method_type == "Patch":
            http_method = "PATCH"
        
        line_num = self._find_line_number(lines, match_text)
        ev_id = self._add_evidence(
            rel_path,
            line_num,
            line_num + 5,
            f"@{method_type}Mapping endpoint",
            prefix="ev_api"
        )
        
        interface_id = f"api_{self._get_component_id_base(class_name)}_{len(self.interfaces)}"
        self.interfaces.append(CollectedInterface(
            id=interface_id,
            container=self.container_id,
            type="REST",
            path=full_path,
            method=http_method,
            implemented_by=class_name,
                evidence_ids=[ev_id]
            ))
    
    def _collect_relations(self, java_files: List[Path]):
        """Collect relations based on dependency injection."""
        for java_file in java_files:
            lines = self._read_file_lines(java_file)
            if not lines:
                continue
            
            content = ''.join(lines)
            rel_path = str(java_file.relative_to(self.repo_path))
            
            # Find class name
            class_match = self.CLASS_PATTERN.search(content)
            if not class_match:
                continue
            
            class_name = class_match.group(1)
            from_id = self._get_component_id_base(class_name)
            
            # Check if this class is a known component
            if class_name not in self._component_names:
                continue
            
            # Track already added relations to avoid duplicates
            added_relations = set()  # (from_id, to_id) tuples
            
            # Find constructor injection - improved pattern
            # Matches: public ClassName(Type1 param1, Type2 param2) {
            constructor_pattern = re.compile(
                rf'(?:public\s+)?{re.escape(class_name)}\s*\(([^)]+)\)',
                re.DOTALL
            )
            
            for constructor_match in constructor_pattern.finditer(content):
                params_str = constructor_match.group(1).strip()
                if not params_str or params_str == '':
                    continue
                
                # Parse parameters: "Type1 param1, Type2 param2"
                # Split by comma, handle multi-line
                params_str_clean = re.sub(r'\s+', ' ', params_str)  # Normalize whitespace
                params = [p.strip() for p in params_str_clean.split(',')]
                
                for param in params:
                    # Extract type from "Type paramName" or "final Type paramName"
                    param_match = re.match(r'(?:final\s+)?(\w+)\s+\w+', param.strip())
                    if param_match:
                        param_type = param_match.group(1)
                        target_class = None
                        
                        # Check if this type is a known component (direct match)
                        if param_type in self._component_names:
                            target_class = param_type
                        # Check if this is an interface with a known implementation
                        elif param_type in self._interface_to_impl:
                            target_class = self._interface_to_impl[param_type]
                        
                        if target_class:
                            to_id = self._get_component_id_base(target_class)
                            relation_key = (from_id, to_id)
                            
                            # Skip if already added
                            if relation_key in added_relations:
                                continue
                            
                            added_relations.add(relation_key)
                            line_num = self._find_line_number(lines, constructor_match.group(0))
                            
                            ev_id = self._add_evidence(
                                rel_path,
                                line_num,
                                line_num + 2,
                                f"Constructor injection of {param_type}" + (f" (impl: {target_class})" if target_class != param_type else ""),
                                prefix="ev_rel"
                            )
                            
                            self.relations.append(CollectedRelation(
                                from_id=from_id,
                                to_id=to_id,
                                type="uses",
                                evidence_ids=[ev_id]
                            ))
            
            # Find field injections (only if not already added from constructor)
            for match in self.FIELD_INJECTION_PATTERN.finditer(content):
                field_type = match.group(1)
                target_class = None
                
                # Direct match
                if field_type in self._component_names:
                    target_class = field_type
                # Interface implementation match
                elif field_type in self._interface_to_impl:
                    target_class = self._interface_to_impl[field_type]
                
                if target_class:
                    to_id = self._get_component_id_base(target_class)
                    relation_key = (from_id, to_id)
                    
                    # Skip if already added from constructor
                    if relation_key in added_relations:
                        continue
                    
                    added_relations.add(relation_key)
                    line_num = self._find_line_number(lines, match.group(0))
                    
                    ev_id = self._add_evidence(
                        rel_path,
                        line_num,
                        line_num,
                        f"Field injection of {field_type}" + (f" (impl: {target_class})" if target_class != field_type else ""),
                        prefix="ev_rel"
                    )
                    
                    self.relations.append(CollectedRelation(
                        from_id=from_id,
                        to_id=to_id,
                        type="uses",
                        evidence_ids=[ev_id]
                    ))
    
    def _find_line_number(self, lines: List[str], search_text: str) -> int:
        """Find the line number containing search_text."""
        search_clean = search_text.replace('\n', ' ').strip()
        for i, line in enumerate(lines, 1):
            if search_clean[:30] in line:
                return i
        return 1
    
    def _find_class_end(self, lines: List[str], start_line: int) -> int:
        """Find approximate end of class (simple brace counting)."""
        brace_count = 0
        started = False
        
        for i, line in enumerate(lines[start_line - 1:], start_line):
            brace_count += line.count('{') - line.count('}')
            if '{' in line:
                started = True
            if started and brace_count == 0:
                return i
        
        return min(start_line + 100, len(lines))
    
    def _scan_interface_for_rest_mappings(self, file_path: Path):
        """Scan Java interface for REST mapping annotations."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        
        # Check if this is an interface
        if 'interface ' not in content:
            return
        
        # Find interface name
        interface_match = re.search(r'(?:public\s+)?interface\s+(\w+)', content)
        if not interface_match:
            return
        
        interface_name = interface_match.group(1)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Extract REST mappings from this interface
        rest_mappings = []
        
        # Get base path from interface-level @RequestMapping
        base_path = ""
        class_mapping = self.CLASS_MAPPING_PATTERN.search(content)
        if class_mapping:
            base_path = class_mapping.group(1)
        
        # Store mappings with their patterns (same extraction as controllers)
        # Track already processed to avoid duplicates
        processed_positions = set()
        if class_mapping:
            processed_positions.add((class_mapping.start(), class_mapping.end()))
        
        # Array paths
        for match in self.ARRAY_PATH_PATTERN.finditer(content):
            method_type = match.group(1)
            paths_str = match.group(2)
            processed_positions.add((match.start(), match.end()))
            paths = re.findall(r'["\']([^"\']+)["\']', paths_str)
            for path in paths:
                rest_mappings.append({
                    'method_type': method_type,
                    'path': path,
                    'base_path': base_path,
                    'file_path': rel_path,
                    'match_text': match.group(0),
                    'lines': lines
                })
        
        # @RequestMapping with method attribute
        for match in self.REQUEST_MAPPING_WITH_METHOD_PATTERN.finditer(content):
            if any(match.start() >= start and match.end() <= end for start, end in processed_positions):
                continue
            path = match.group(1)
            http_method = match.group(2)
            method_type_map = {"GET": "Get", "POST": "Post", "PUT": "Put", "DELETE": "Delete", "PATCH": "Patch"}
            method_type = method_type_map.get(http_method.upper(), "Request")
            processed_positions.add((match.start(), match.end()))
            rest_mappings.append({
                'method_type': method_type,
                'path': path,
                'base_path': '',  # Already absolute
                'file_path': rel_path,
                'match_text': match.group(0),
                'lines': lines,
                'absolute': True
            })
        
        # Single path mappings
        for match in self.REQUEST_MAPPING_SINGLE_PATTERN.finditer(content):
            if any(match.start() >= start and match.end() <= end for start, end in processed_positions):
                continue
            rest_mappings.append({
                'method_type': match.group(1),
                'path': match.group(2),
                'base_path': base_path,
                'file_path': rel_path,
                'match_text': match.group(0),
                'lines': lines
            })
        
        # Empty mappings
        for match in self.REQUEST_MAPPING_EMPTY_PATTERN.finditer(content):
            if any(match.start() >= start and match.end() <= end for start, end in processed_positions):
                continue
            rest_mappings.append({
                'method_type': match.group(1),
                'path': '',
                'base_path': base_path,
                'file_path': rel_path,
                'match_text': match.group(0),
                'lines': lines
            })
        
        # No-params mappings
        for match in self.REQUEST_MAPPING_NO_PARAMS_PATTERN.finditer(content):
            if any(match.start() >= start and match.end() <= end for start, end in processed_positions):
                continue
            rest_mappings.append({
                'method_type': match.group(1),
                'path': '',
                'base_path': base_path,
                'file_path': rel_path,
                'match_text': match.group(0),
                'lines': lines
            })
        
        if rest_mappings:
            self._interface_rest_mappings[interface_name] = rest_mappings
    
    def _extract_endpoints_from_interfaces(self, content: str, class_name: str):
        """Extract REST endpoints from implemented interfaces."""
        # Find implemented interfaces
        implements_match = re.search(r'implements\s+([\w\s,]+)(?:\s*\{|$)', content)
        if not implements_match:
            return
        
        # Get list of interface names
        interfaces_str = implements_match.group(1)
        interface_names = [name.strip() for name in interfaces_str.split(',')]
        
        # For each interface, check if it has REST mappings
        for interface_name in interface_names:
            if interface_name in self._interface_rest_mappings:
                # Create REST interfaces from the mappings
                for mapping in self._interface_rest_mappings[interface_name]:
                    if mapping.get('absolute'):
                        self._create_interface_absolute(
                            mapping['method_type'],
                            mapping['path'],
                            "",  # content not needed
                            mapping['lines'],
                            mapping['file_path'],
                            class_name,
                            mapping['match_text']
                        )
                    else:
                        self._create_interface(
                            mapping['method_type'],
                            mapping['path'],
                            mapping['base_path'],
                            "",  # content not needed
                            mapping['lines'],
                            mapping['file_path'],
                            class_name,
                            mapping['match_text']
                        )

    # =========================================================================
    # BACKEND METADATA EXTRACTION
    # =========================================================================
    
    def extract_backend_metadata(self) -> Dict:
        """
        Extract additional backend-specific metadata from the Spring Boot project.
        
        Returns dict with:
        - spring_profiles: List of detected Spring profiles
        - api_base_path: Base path for REST APIs
        - security_config: Detected security configuration
        - database_config: Detected database configuration
        - messaging_config: Detected messaging configuration (Kafka, RabbitMQ)
        """
        metadata = {
            "spring_profiles": [],
            "api_base_path": None,
            "security_config": {},
            "database_config": {},
            "messaging_config": {},
            "actuator_endpoints": [],
        }
        
        # Find application.yml or application.properties
        config_files = [
            self.repo_path / "src" / "main" / "resources" / "application.yml",
            self.repo_path / "src" / "main" / "resources" / "application.yaml",
            self.repo_path / "src" / "main" / "resources" / "application.properties",
            self.repo_path / "backend" / "src" / "main" / "resources" / "application.yml",
        ]
        
        for config_path in config_files:
            if config_path.exists():
                self._parse_spring_config(config_path, metadata)
                break
        
        # Find profile-specific configs (search recursively)
        resources_paths = [
            self.repo_path / "src" / "main" / "resources",
            self.repo_path / "backend" / "src" / "main" / "resources",
            self.repo_path / "backend" / "src" / "test" / "resources",
            self.repo_path / "resources",
            self.repo_path / "backend" / "resources",
            self.repo_path / "dist" / "resources",
            self.repo_path / "backend" / "dist" / "resources",
            self.repo_path / "distResources",
            self.repo_path / "backend" / "distResources",
            self.repo_path / "dist-resources",
            self.repo_path / "backend" / "dist-resources",
            self.repo_path / "src" / "main" / "distResources",
            self.repo_path / "backend" / "src" / "main" / "distResources",
            self.repo_path / "src" / "dist" / "resources",
            self.repo_path / "backend" / "src" / "dist" / "resources",
            self.repo_path / "config",
            self.repo_path / "backend" / "config",
        ]
        
        for resources_path in resources_paths:
            if resources_path.exists():
                # Search recursively with **
                for f in resources_path.glob("**/application-*.yml"):
                    profile = f.stem.replace("application-", "")
                    if profile not in metadata["spring_profiles"]:
                        metadata["spring_profiles"].append(profile)
                for f in resources_path.glob("**/application-*.yaml"):
                    profile = f.stem.replace("application-", "")
                    if profile not in metadata["spring_profiles"]:
                        metadata["spring_profiles"].append(profile)
                for f in resources_path.glob("**/application-*.properties"):
                    profile = f.stem.replace("application-", "")
                    if profile not in metadata["spring_profiles"]:
                        metadata["spring_profiles"].append(profile)
        
        # Detect security configuration
        self._detect_security_config(metadata)
        
        # Detect messaging configuration
        self._detect_messaging_config(metadata)
        
        logger.info(f"[SpringCollector] Extracted backend metadata: {len(metadata['spring_profiles'])} profiles")
        return metadata
    
    def _parse_spring_config(self, config_path: Path, metadata: Dict):
        """Parse Spring application config file."""
        try:
            content = self._read_file(config_path)
            
            # Server port
            port_match = re.search(r'server\.port\s*[=:]\s*(\d+)', content)
            if port_match:
                metadata["server_port"] = int(port_match.group(1))
            
            # Context path / API base path
            ctx_match = re.search(r'server\.servlet\.context-path\s*[=:]\s*([^\n\r]+)', content)
            if ctx_match:
                metadata["api_base_path"] = ctx_match.group(1).strip()
            
            # Database URL
            db_match = re.search(r'spring\.datasource\.url\s*[=:]\s*([^\n\r]+)', content)
            if db_match:
                db_url = db_match.group(1).strip()
                metadata["database_config"]["url"] = db_url
                # Detect database type from URL
                if "postgresql" in db_url.lower():
                    metadata["database_config"]["type"] = "PostgreSQL"
                elif "mysql" in db_url.lower():
                    metadata["database_config"]["type"] = "MySQL"
                elif "oracle" in db_url.lower():
                    metadata["database_config"]["type"] = "Oracle"
                elif "h2" in db_url.lower():
                    metadata["database_config"]["type"] = "H2"
            
            # JPA settings
            if "spring.jpa" in content:
                metadata["database_config"]["orm"] = "JPA/Hibernate"
            
            # Actuator endpoints
            if "management.endpoints" in content:
                metadata["actuator_endpoints"].append("management")
            
        except Exception as e:
            logger.warning(f"[SpringCollector] Failed to parse config: {e}")
    
    def _detect_security_config(self, metadata: Dict):
        """Detect Spring Security configuration."""
        if self.java_root:
            for java_file in self.java_root.rglob("*.java"):
                content = self._read_file(java_file)
                
                if "@EnableWebSecurity" in content:
                    metadata["security_config"]["spring_security"] = True
                    
                    # Detect OAuth2
                    if "oauth2" in content.lower():
                        metadata["security_config"]["oauth2"] = True
                    
                    # Detect JWT
                    if "jwt" in content.lower() or "JwtDecoder" in content:
                        metadata["security_config"]["jwt"] = True
                    
                    break
    
    def _detect_messaging_config(self, metadata: Dict):
        """Detect messaging configuration (Kafka, RabbitMQ)."""
        if self.java_root:
            for java_file in self.java_root.rglob("*.java"):
                content = self._read_file(java_file)
                
                if "@KafkaListener" in content:
                    metadata["messaging_config"]["kafka"] = True
                
                if "@RabbitListener" in content:
                    metadata["messaging_config"]["rabbitmq"] = True
                
                if "@JmsListener" in content:
                    metadata["messaging_config"]["jms"] = True
    
    def _read_file(self, file_path: Path) -> str:
        """Read file content."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
