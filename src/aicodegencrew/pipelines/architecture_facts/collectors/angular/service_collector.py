"""
AngularServiceCollector - Extracts Angular service facts.

Detects:
- @Injectable services
- HTTP client usage
- Service dependencies
- Native JavaScript API Endpoints (e.g., embedded/native JS bridges)

Output feeds -> components.json (services)
             -> interfaces.json (JS API endpoints)
             -> relations (service dependencies, HTTP calls)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawComponent, RawInterface, RelationHint


class AngularServiceCollector(DimensionCollector):
    """
    Extracts Angular service facts.
    """

    DIMENSION = "angular_services"

    # Patterns
    INJECTABLE_PATTERN = re.compile(r"@Injectable\s*\(")
    CLASS_PATTERN = re.compile(r"^(?:export\s+)?class\s+([A-Z]\w*)", re.MULTILINE)

    # HTTP patterns
    HTTP_CALL_PATTERN = re.compile(r'this\.http\s*\.\s*(get|post|put|delete|patch)\s*[<(]\s*[\'"]?([^\'")\s,>]+)')
    HTTP_GENERIC_PATTERN = re.compile(
        r'this\.http\s*\.\s*(get|post|put|delete|patch)\s*<[^>]+>\s*\(\s*[\'"]([^\'"]+)[\'"]'
    )

    # OpenAPI generated path patterns (e.g., static readonly GetStatusPath = '/api/v1/action/{id}')
    OPENAPI_PATH_PATTERN = re.compile(r'static\s+readonly\s+(\w+Path)\s*=\s*[\'"]([^\'"]+)[\'"]')

    # API endpoint from URL patterns (e.g., this.request('/api/users'))
    REQUEST_URL_PATTERN = re.compile(
        r'(?:this\.request|this\.api\w*|fetch)\s*(?:<[^>]+>)?\s*\(\s*[\'"`]([^\'"` ]+)[\'"`]'
    )

    # Native JavaScript API Endpoint pattern (e.g., static ENDPOINT = 'documentsEndpoint')
    JS_API_ENDPOINT_PATTERN = re.compile(r'static\s+ENDPOINT\s*=\s*[\'"](\w+)[\'"]')

    # Dependency injection
    CONSTRUCTOR_PATTERN = re.compile(r"constructor\s*\([^)]*\)", re.DOTALL)
    PARAM_PATTERN = re.compile(r"(?:private|protected|public|readonly)\s+(?:readonly\s+)?(\w+)\s*:\s*(\w+)")

    # providedIn
    PROVIDED_IN_PATTERN = re.compile(r'providedIn\s*:\s*[\'"](\w+)[\'"]')

    def __init__(self, repo_path: Path, container_id: str = "frontend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._angular_root: Path | None = None
        self._service_names: set[str] = set()

    def collect(self) -> CollectorOutput:
        """Collect Angular service facts."""
        self._log_start()

        self._angular_root = self._find_angular_root()
        if not self._angular_root:
            logger.info("[AngularServiceCollector] No Angular source root found")
            return self.output

        # Find service files
        ts_files = self._find_files("*.service.ts", self._angular_root)

        # Also find Endpoint files (adapter pattern)
        for endpoint_file in self._find_files("*Endpoint.ts", self._angular_root):
            if endpoint_file not in ts_files and not endpoint_file.name.endswith(".spec.ts"):
                ts_files.append(endpoint_file)

        # Also check files with @Injectable
        for ts_file in self._find_files("*.ts", self._angular_root):
            if ts_file not in ts_files and not ts_file.name.endswith(".spec.ts"):
                content = self._read_file_content(ts_file)
                if self.INJECTABLE_PATTERN.search(content):
                    ts_files.append(ts_file)

        # Remove duplicates
        ts_files = list(set(ts_files))
        logger.info(f"[AngularServiceCollector] Found {len(ts_files)} service files")

        # First pass: identify services
        for ts_file in ts_files:
            self._identify_service(ts_file)

        # Second pass: extract details and relations
        for ts_file in ts_files:
            self._process_service_file(ts_file)

        self._log_end()
        return self.output

    def _find_angular_root(self) -> Path | None:
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

    def _identify_service(self, file_path: Path):
        """Identify service names."""
        content = self._read_file_content(file_path)

        class_match = self.CLASS_PATTERN.search(content)
        if class_match:
            self._service_names.add(class_match.group(1))

    def _process_service_file(self, file_path: Path):
        """Process a service file."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        if not self.INJECTABLE_PATTERN.search(content):
            return

        # Get class name
        class_match = self.CLASS_PATTERN.search(content)
        if not class_match:
            return

        service_name = class_match.group(1)
        class_line = self._find_line_number(lines, f"class {service_name}")

        # Determine stereotype based on class name pattern
        if "Endpoint" in service_name:
            stereotype = "adapter"
            layer_hint = "infrastructure"
        elif "Adapter" in service_name:
            stereotype = "adapter"
            layer_hint = "infrastructure"
        elif "Guard" in service_name:
            stereotype = "guard"
            layer_hint = "presentation"
        elif "Interceptor" in service_name:
            stereotype = "interceptor"
            layer_hint = "infrastructure"
        elif "Resolver" in service_name:
            stereotype = "resolver"
            layer_hint = "presentation"
        else:
            stereotype = "service"
            layer_hint = "application"

        # Check providedIn
        provided_match = self.PROVIDED_IN_PATTERN.search(content)
        provided_in = provided_match.group(1) if provided_match else None

        # Extract HTTP calls
        http_calls = self._extract_http_calls(content)

        # Extract dependencies
        dependencies = self._extract_dependencies(content)

        # Create service component
        service = RawComponent(
            name=service_name,
            stereotype=stereotype,
            container_hint=self.container_id,
            module=self._derive_module(rel_path),
            file_path=rel_path,
            layer_hint=layer_hint,
        )

        if provided_in:
            service.metadata["provided_in"] = provided_in

        if http_calls:
            service.metadata["http_calls"] = http_calls[:10]  # Limit
            service.tags.append("uses-http")

        if dependencies:
            service.metadata["dependencies"] = dependencies

        service.add_evidence(
            path=rel_path, line_start=class_line - 3, line_end=class_line + 3, reason=f"@Injectable: {service_name}"
        )

        self.output.add_fact(service)

        # Check for JavaScript API Endpoint (e.g., static ENDPOINT = 'documentsEndpoint')
        # Common pattern for native/embedded JS API wrappers
        js_api_match = self.JS_API_ENDPOINT_PATTERN.search(content)
        if js_api_match:
            endpoint_name = js_api_match.group(1)  # e.g., 'documentsEndpoint'
            endpoint_line = content[: js_api_match.start()].count("\n") + 1

            # Create interface for the JS API
            js_interface = RawInterface(
                name=endpoint_name,
                type="js_api",
                path=f"native.{endpoint_name}",
                implemented_by_hint=service_name,
                container_hint=self.container_id,
            )
            js_interface.metadata["wrapper_class"] = service_name
            js_interface.metadata["api_type"] = "native_js"

            js_interface.add_evidence(
                path=rel_path,
                line_start=endpoint_line,
                line_end=endpoint_line + 1,
                reason=f"JavaScript API Endpoint: {endpoint_name}",
            )

            self.output.add_fact(js_interface)

        # Create relations for dependencies
        for dep in dependencies:
            if dep in self._service_names:
                relation = RelationHint(
                    from_name=service_name,
                    to_name=dep,
                    type="uses",
                    from_stereotype_hint="service",
                    to_stereotype_hint="service",
                )
                self.output.add_relation(relation)

        # Create relations for HTTP calls (to backend)
        for call in http_calls:
            if call.get("url", "").startswith("/api"):
                relation = RelationHint(
                    from_name=service_name,
                    to_name=f"API:{call.get('url', '')}",
                    type="calls",
                    from_stereotype_hint="service",
                )
                relation.evidence.append(
                    self._create_evidence(
                        file_path, 1, 1, f"HTTP {call.get('method', 'GET')} call to {call.get('url', '')}"
                    )
                )
                self.output.add_relation(relation)

    def _extract_http_calls(self, content: str) -> list[dict]:
        """Extract HTTP client calls and API endpoint paths."""
        calls = []
        seen_urls = set()

        # 1. Direct HTTP calls (this.http.get, post, etc.)
        for pattern in [self.HTTP_CALL_PATTERN, self.HTTP_GENERIC_PATTERN]:
            for match in pattern.finditer(content):
                method = match.group(1).upper()
                url = match.group(2)

                # Skip template strings and variables
                if "${" in url or url.startswith("this."):
                    continue

                if url not in seen_urls:
                    calls.append(
                        {
                            "method": method,
                            "url": url,
                        }
                    )
                    seen_urls.add(url)

        # 2. OpenAPI generated path constants (static readonly XxxPath = '/api/...')
        for match in self.OPENAPI_PATH_PATTERN.finditer(content):
            path_name = match.group(1)  # e.g., "GetStatusPath"
            url = match.group(2)  # e.g., "/api/v1/action/{id}"

            # Infer HTTP method from path name
            method = "GET"
            if "Post" in path_name or "Create" in path_name:
                method = "POST"
            elif "Put" in path_name or "Update" in path_name:
                method = "PUT"
            elif "Delete" in path_name or "Remove" in path_name:
                method = "DELETE"
            elif "Patch" in path_name:
                method = "PATCH"

            if url not in seen_urls:
                calls.append(
                    {
                        "method": method,
                        "url": url,
                        "openapi": True,  # Mark as OpenAPI generated
                    }
                )
                seen_urls.add(url)

        # 3. Generic request patterns (this.request('/api/...'))
        for match in self.REQUEST_URL_PATTERN.finditer(content):
            url = match.group(1)
            if url.startswith("/") and url not in seen_urls:
                calls.append(
                    {
                        "method": "UNKNOWN",
                        "url": url,
                    }
                )
                seen_urls.add(url)

        return calls

    def _extract_dependencies(self, content: str) -> list[str]:
        """Extract constructor dependencies."""
        deps = []

        constructor_match = self.CONSTRUCTOR_PATTERN.search(content)
        if constructor_match:
            constructor_content = constructor_match.group(0)

            for param_match in self.PARAM_PATTERN.finditer(constructor_content):
                dep_type = param_match.group(2)
                # Filter out Angular built-ins
                if dep_type not in ("HttpClient", "Router", "ActivatedRoute", "FormBuilder", "NgZone", "Renderer2"):
                    deps.append(dep_type)

        return deps
