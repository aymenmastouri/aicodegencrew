"""
PythonComponentCollector - Extracts Python component facts.

Detects:
- Flask: @app.route view functions, Blueprint() instances
- FastAPI: APIRouter() instances, @router.get/post/... handler classes
- Django: Class-based views (View, APIView, ViewSet, etc.), Django models
- Generic: Service classes, repository classes, handler classes, manager classes

Output feeds -> components.json
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawComponent

# =============================================================================
# Regex Patterns
# =============================================================================

# Django patterns
DJANGO_VIEW_PATTERN = re.compile(
    r"class\s+(\w+)\s*\([^)]*(?:View|APIView|ViewSet|ModelViewSet|"
    r"GenericAPIView|CreateView|UpdateView|DeleteView|ListView|"
    r"DetailView|TemplateView|FormView)[^)]*\)"
)
DJANGO_MODEL_PATTERN = re.compile(
    r"class\s+(\w+)\s*\(\s*(?:models\.Model|Model)\s*\)"
)

# Flask patterns
FLASK_BLUEPRINT_PATTERN = re.compile(r"(\w+)\s*=\s*Blueprint\s*\(")
FLASK_APP_ROUTE = re.compile(r"@(?:app|blueprint|\w+)\.route\s*\(")

# FastAPI patterns
FASTAPI_ROUTER_PATTERN = re.compile(r"(\w+)\s*=\s*APIRouter\s*\(")

# Generic class pattern (for services, repositories, etc.)
CLASS_PATTERN = re.compile(r"^class\s+(\w+)\s*(?:\([^)]*\))?\s*:", re.MULTILINE)

# File-name patterns that indicate a service-like role
SERVICE_FILE_INDICATORS = {"service", "repository", "handler", "manager"}


class PythonComponentCollector(DimensionCollector):
    """
    Extracts Python component facts from Flask, FastAPI, Django,
    and generic service-layer code using regex-based detection.
    """

    DIMENSION = "python_components"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python component facts."""
        self._log_start()

        py_files = self._find_files("*.py")
        if not py_files:
            logger.debug(
                "[PythonComponentCollector] No Python files in %s (skipping)",
                self.repo_path,
            )
            return self.output

        logger.info(
            "[PythonComponentCollector] Scanning %d Python files", len(py_files)
        )

        for py_file in py_files:
            self._process_file(py_file)

        self._log_end()
        return self.output

    # =========================================================================
    # File Processing
    # =========================================================================

    def _process_file(self, file_path: Path):
        """Process a single Python file for components."""
        content = self._read_file_content(file_path)
        if not content.strip():
            return

        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        # Try each framework detector in order of specificity
        found_django = self._detect_django_components(content, lines, rel_path)
        found_flask = self._detect_flask_components(content, lines, rel_path)
        found_fastapi = self._detect_fastapi_components(content, lines, rel_path)

        # If no framework was detected, try generic service-class detection
        if not (found_django or found_flask or found_fastapi):
            self._detect_generic_components(content, lines, rel_path, file_path)

    # =========================================================================
    # Django Detection
    # =========================================================================

    def _detect_django_components(
        self, content: str, lines: list[str], rel_path: str
    ) -> bool:
        """Detect Django class-based views and models."""
        found = False

        # Django views
        for match in DJANGO_VIEW_PATTERN.finditer(content):
            class_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            component = RawComponent(
                name=class_name,
                stereotype="controller",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="presentation",
            )
            component.metadata["framework"] = "django"
            component.metadata["kind"] = "class_based_view"
            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"Django view: {class_name}",
            )
            self.output.add_fact(component)
            found = True

        # Django models
        for match in DJANGO_MODEL_PATTERN.finditer(content):
            class_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            component = RawComponent(
                name=class_name,
                stereotype="model",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="domain",
            )
            component.metadata["framework"] = "django"
            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"Django model: {class_name}",
            )
            self.output.add_fact(component)
            found = True

        return found

    # =========================================================================
    # Flask Detection
    # =========================================================================

    def _detect_flask_components(
        self, content: str, lines: list[str], rel_path: str
    ) -> bool:
        """Detect Flask blueprints and route-decorated view functions."""
        found = False

        # Blueprints
        for match in FLASK_BLUEPRINT_PATTERN.finditer(content):
            bp_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            component = RawComponent(
                name=bp_name,
                stereotype="router",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="presentation",
            )
            component.metadata["framework"] = "flask"
            component.metadata["type"] = "blueprint"
            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 3,
                reason=f"Flask Blueprint: {bp_name}",
            )
            self.output.add_fact(component)
            found = True

        # @app.route view functions — collect the function name below each decorator
        if FLASK_APP_ROUTE.search(content):
            func_after_route = re.compile(
                r"@(?:app|blueprint|\w+)\.route\s*\([^)]*\)\s*\n"
                r"(?:@\w+[^\n]*\n)*"  # skip stacked decorators
                r"def\s+(\w+)\s*\(",
                re.MULTILINE,
            )
            for match in func_after_route.finditer(content):
                func_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                component = RawComponent(
                    name=func_name,
                    stereotype="controller",
                    container_hint=self.container_id,
                    module=self._derive_module(rel_path),
                    file_path=rel_path,
                    layer_hint="presentation",
                )
                component.metadata["framework"] = "flask"
                component.metadata["type"] = "route_handler"
                component.add_evidence(
                    path=rel_path,
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f"Flask route handler: {func_name}",
                )
                self.output.add_fact(component)
                found = True

        return found

    # =========================================================================
    # FastAPI Detection
    # =========================================================================

    def _detect_fastapi_components(
        self, content: str, lines: list[str], rel_path: str
    ) -> bool:
        """Detect FastAPI routers and decorated handler functions."""
        found = False

        # APIRouter instances
        for match in FASTAPI_ROUTER_PATTERN.finditer(content):
            router_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            component = RawComponent(
                name=router_name,
                stereotype="router",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="presentation",
            )
            component.metadata["framework"] = "fastapi"
            component.metadata["type"] = "api_router"
            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 3,
                reason=f"FastAPI APIRouter: {router_name}",
            )
            self.output.add_fact(component)
            found = True

        # @router.get/post/... handler functions
        fastapi_handler = re.compile(
            r"@(\w+)\.(get|post|put|delete|patch|options|head)\s*\([^)]*\)\s*\n"
            r"(?:@\w+[^\n]*\n)*"  # skip stacked decorators
            r"(?:async\s+)?def\s+(\w+)\s*\(",
            re.MULTILINE,
        )
        for match in fastapi_handler.finditer(content):
            func_name = match.group(3)
            line_num = content[: match.start()].count("\n") + 1

            component = RawComponent(
                name=func_name,
                stereotype="controller",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="presentation",
            )
            component.metadata["framework"] = "fastapi"
            component.metadata["type"] = "route_handler"
            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"FastAPI route handler: {func_name}",
            )
            self.output.add_fact(component)
            found = True

        return found

    # =========================================================================
    # Generic Service-Class Detection
    # =========================================================================

    def _detect_generic_components(
        self,
        content: str,
        lines: list[str],
        rel_path: str,
        file_path: Path,
    ):
        """
        Detect generic Python service-layer classes based on filename
        patterns (service, repository, handler, manager).
        """
        filename_lower = file_path.stem.lower()

        # Only process files whose name contains a service-like indicator
        matched_indicator = None
        for indicator in SERVICE_FILE_INDICATORS:
            if indicator in filename_lower:
                matched_indicator = indicator
                break

        if matched_indicator is None:
            return

        stereotype = self._stereotype_from_indicator(matched_indicator)

        for match in CLASS_PATTERN.finditer(content):
            class_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            layer = self._layer_from_stereotype(stereotype)

            component = RawComponent(
                name=class_name,
                stereotype=stereotype,
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint=layer,
            )
            component.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"Python {stereotype}: {class_name}",
            )
            self.output.add_fact(component)

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _stereotype_from_indicator(indicator: str) -> str:
        """Map a filename indicator to a component stereotype."""
        mapping = {
            "service": "service",
            "repository": "repository",
            "handler": "controller",
            "manager": "service",
        }
        return mapping.get(indicator, "service")

    @staticmethod
    def _layer_from_stereotype(stereotype: str) -> str:
        """Map a stereotype to an architecture layer."""
        mapping = {
            "controller": "presentation",
            "service": "application",
            "repository": "data_access",
            "model": "domain",
            "entity": "domain",
            "router": "presentation",
        }
        return mapping.get(stereotype, "application")
