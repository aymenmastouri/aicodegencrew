"""
PythonInterfaceCollector - Extracts Python HTTP endpoint and route facts.

Detects:
- Flask: @app.route('/path', methods=['GET']), @blueprint.route('/path')
- FastAPI: @router.get('/path'), @app.post('/path')
- Django: path('url/', view), re_path(), url() in urls.py files
- gRPC: Classes ending in Servicer (e.g., class GreeterServicer)

Output feeds -> interfaces.json (REST endpoints, routes, gRPC services)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawInterface

# =============================================================================
# Regex Patterns
# =============================================================================

# Flask routes
FLASK_ROUTE_PATTERN = re.compile(
    r"@(\w+)\.route\s*\(\s*['\"]([^'\"]+)['\"]"
    r"(?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?"
)

# FastAPI routes
FASTAPI_ROUTE_PATTERN = re.compile(
    r"@(\w+)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"]([^'\"]+)['\"]"
)

# Django URL patterns
DJANGO_PATH_PATTERN = re.compile(
    r"(?:path|re_path|url)\s*\(\s*['\"]([^'\"]+)['\"]"
)

# gRPC servicers
GRPC_SERVICER_PATTERN = re.compile(r"class\s+(\w+Servicer)\s*\(")


class PythonInterfaceCollector(DimensionCollector):
    """
    Extracts Python HTTP endpoints, URL routes, and gRPC service
    definitions using regex-based detection.
    """

    DIMENSION = "python_interfaces"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python interface facts."""
        self._log_start()

        py_files = self._find_files("*.py")
        if not py_files:
            logger.debug(
                "[PythonInterfaceCollector] No Python files in %s (skipping)",
                self.repo_path,
            )
            return self.output

        logger.info(
            "[PythonInterfaceCollector] Scanning %d Python files", len(py_files)
        )

        for py_file in py_files:
            self._process_file(py_file)

        self._log_end()
        return self.output

    # =========================================================================
    # File Processing
    # =========================================================================

    def _process_file(self, file_path: Path):
        """Process a single Python file for interface definitions."""
        content = self._read_file_content(file_path)
        if not content.strip():
            return

        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        self._detect_flask_routes(content, lines, rel_path)
        self._detect_fastapi_routes(content, lines, rel_path)
        self._detect_django_urls(content, lines, rel_path, file_path)
        self._detect_grpc_servicers(content, lines, rel_path)

    # =========================================================================
    # Flask Route Detection
    # =========================================================================

    def _detect_flask_routes(
        self, content: str, lines: list[str], rel_path: str
    ):
        """Detect Flask @app.route / @blueprint.route endpoints."""
        for match in FLASK_ROUTE_PATTERN.finditer(content):
            variable_name = match.group(1)
            route_path = match.group(2)
            methods_raw = match.group(3)

            # Parse methods list, default to GET
            if methods_raw:
                methods = [
                    m.strip().strip("'\"").upper()
                    for m in methods_raw.split(",")
                ]
            else:
                methods = ["GET"]

            line_num = content[: match.start()].count("\n") + 1

            for method in methods:
                interface = RawInterface(
                    name=f"{method} {route_path}",
                    type="rest_endpoint",
                    path=route_path,
                    method=method,
                    implemented_by_hint=variable_name,
                    container_hint=self.container_id,
                )
                interface.metadata["framework"] = "flask"
                interface.add_evidence(
                    path=rel_path,
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f"Flask route: {method} {route_path}",
                )
                self.output.add_fact(interface)

    # =========================================================================
    # FastAPI Route Detection
    # =========================================================================

    def _detect_fastapi_routes(
        self, content: str, lines: list[str], rel_path: str
    ):
        """Detect FastAPI @router.get/post/... endpoints."""
        for match in FASTAPI_ROUTE_PATTERN.finditer(content):
            variable_name = match.group(1)
            http_method = match.group(2).upper()
            route_path = match.group(3)

            line_num = content[: match.start()].count("\n") + 1

            interface = RawInterface(
                name=f"{http_method} {route_path}",
                type="rest_endpoint",
                path=route_path,
                method=http_method,
                implemented_by_hint=variable_name,
                container_hint=self.container_id,
            )
            interface.metadata["framework"] = "fastapi"
            interface.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"FastAPI route: {http_method} {route_path}",
            )
            self.output.add_fact(interface)

    # =========================================================================
    # Django URL Detection
    # =========================================================================

    def _detect_django_urls(
        self,
        content: str,
        lines: list[str],
        rel_path: str,
        file_path: Path,
    ):
        """Detect Django path(), re_path(), url() patterns in urls.py files."""
        # Only process files that are likely URL configuration
        if not file_path.name.endswith("urls.py"):
            # Also accept files that import path/re_path/url from django
            if not re.search(
                r"from\s+django\.(?:urls|conf\.urls)\s+import", content
            ):
                return

        for match in DJANGO_PATH_PATTERN.finditer(content):
            url_pattern = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            # Normalise the URL to start with /
            display_path = url_pattern if url_pattern.startswith("/") else f"/{url_pattern}"

            interface = RawInterface(
                name=display_path,
                type="route",
                path=display_path,
                method=None,
                implemented_by_hint="",
                container_hint=self.container_id,
            )
            interface.metadata["framework"] = "django"
            interface.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 3,
                reason=f"Django URL pattern: {display_path}",
            )
            self.output.add_fact(interface)

    # =========================================================================
    # gRPC Servicer Detection
    # =========================================================================

    def _detect_grpc_servicers(
        self, content: str, lines: list[str], rel_path: str
    ):
        """Detect gRPC servicer class definitions."""
        for match in GRPC_SERVICER_PATTERN.finditer(content):
            servicer_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            interface = RawInterface(
                name=servicer_name,
                type="grpc_service",
                path=None,
                method=None,
                implemented_by_hint=servicer_name,
                container_hint=self.container_id,
            )
            interface.metadata["framework"] = "grpc"
            interface.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"gRPC servicer: {servicer_name}",
            )
            self.output.add_fact(interface)
