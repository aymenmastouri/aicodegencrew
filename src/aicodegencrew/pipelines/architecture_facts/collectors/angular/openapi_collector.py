"""
OpenAPICollector - Extracts OpenAPI/Swagger specification facts.

Detects:
- openapi.yaml / openapi.json files
- swagger.yaml / swagger.json files
- Generated API client services (often in /api or /generated directories)
- API path definitions and operations

Output feeds -> interfaces.json (API endpoints from spec)
             -> components.json (generated API clients)
"""

import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..base import DimensionCollector, CollectorOutput, RawComponent, RawInterface
from .....shared.utils.logger import logger


class OpenAPICollector(DimensionCollector):
    """
    Extracts OpenAPI/Swagger specification facts from frontend projects.

    Finds and parses:
    - openapi.yaml, openapi.json, swagger.yaml, swagger.json
    - Generated API client code (ng-openapi-gen, swagger-codegen, openapi-generator)
    """

    DIMENSION = "openapi"

    # Skip directories
    SKIP_DIRS = {'node_modules', 'dist', 'build', '.git', 'coverage'}

    # OpenAPI spec file patterns
    SPEC_PATTERNS = [
        "openapi.yaml", "openapi.yml", "openapi.json",
        "swagger.yaml", "swagger.yml", "swagger.json",
        "api-spec.yaml", "api-spec.json",
        "api.yaml", "api.json",
    ]

    # Generated client patterns
    GENERATED_DIRS = ['generated', 'api', 'openapi', 'swagger', 'client']

    def __init__(self, repo_path: Path, container_id: str = "frontend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._specs_found: List[Dict] = []

    def collect(self) -> CollectorOutput:
        """Collect OpenAPI/Swagger facts."""
        self._log_start()

        # 1. Find and parse spec files
        self._collect_spec_files()

        # 2. Find generated API clients
        self._collect_generated_clients()

        logger.info(f"[OpenAPICollector] Found {len(self._specs_found)} OpenAPI specs")
        self._log_end()
        return self.output

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)

    def _collect_spec_files(self):
        """Find and parse OpenAPI/Swagger spec files."""
        for pattern in self.SPEC_PATTERNS:
            for spec_file in self.repo_path.rglob(pattern):
                if self._should_skip(spec_file):
                    continue
                self._parse_spec_file(spec_file)

    def _parse_spec_file(self, file_path: Path):
        """Parse an OpenAPI/Swagger spec file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # Parse based on extension
            if file_path.suffix in ('.yaml', '.yml'):
                spec = yaml.safe_load(content)
            else:
                spec = json.loads(content)

            if not spec:
                return

            # Determine spec version
            openapi_version = spec.get('openapi', spec.get('swagger', 'unknown'))
            api_title = spec.get('info', {}).get('title', file_path.stem)
            api_version = spec.get('info', {}).get('version', '')

            logger.info(f"[OpenAPICollector] Parsing: {rel_path} (OpenAPI {openapi_version})")

            # Store spec info
            spec_info = {
                "file": rel_path,
                "version": openapi_version,
                "title": api_title,
                "api_version": api_version,
            }
            self._specs_found.append(spec_info)

            # Create a component for the spec itself
            spec_component = RawComponent(
                name=f"OpenAPI: {api_title}",
                stereotype="openapi_spec",
                container_hint=self.container_id,
                file_path=rel_path,
                layer_hint="infrastructure",
            )
            spec_component.metadata["openapi_version"] = openapi_version
            spec_component.metadata["api_version"] = api_version
            spec_component.metadata["title"] = api_title

            spec_component.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=20,
                reason=f"OpenAPI Spec: {api_title} v{api_version}"
            )
            self.output.add_fact(spec_component)

            # Extract endpoints from paths
            paths = spec.get('paths', {})
            for path, operations in paths.items():
                if not isinstance(operations, dict):
                    continue

                for method, operation in operations.items():
                    if method.lower() not in ('get', 'post', 'put', 'delete', 'patch', 'options', 'head'):
                        continue

                    if not isinstance(operation, dict):
                        continue

                    operation_id = operation.get('operationId', f"{method}_{path}")
                    summary = operation.get('summary', '')
                    tags = operation.get('tags', [])

                    interface = RawInterface(
                        name=f"{method.upper()} {path}",
                        type="openapi_endpoint",
                        path=path,
                        method=method.upper(),
                        container_hint=self.container_id,
                    )

                    interface.metadata["operation_id"] = operation_id
                    interface.metadata["source"] = "openapi_spec"
                    interface.metadata["spec_file"] = rel_path
                    if summary:
                        interface.metadata["summary"] = summary
                    if tags:
                        interface.metadata["tags"] = tags

                    interface.add_evidence(
                        path=rel_path,
                        line_start=1,
                        line_end=10,
                        reason=f"OpenAPI endpoint: {method.upper()} {path}"
                    )

                    self.output.add_fact(interface)

            logger.debug(f"[OpenAPICollector] Extracted {len(paths)} paths from {rel_path}")

        except yaml.YAMLError as e:
            logger.warning(f"[OpenAPICollector] Failed to parse YAML {file_path}: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"[OpenAPICollector] Failed to parse JSON {file_path}: {e}")
        except Exception as e:
            logger.debug(f"[OpenAPICollector] Error processing {file_path}: {e}")

    def _collect_generated_clients(self):
        """Find generated API client services."""
        # Look for common generated client patterns
        patterns = [
            ("*.service.ts", r'@Injectable.*?\n.*?class\s+(\w+Service)'),
            ("*.api.ts", r'class\s+(\w+Api)'),
            ("*Api.ts", r'class\s+(\w+Api)'),
        ]

        # Search in generated directories
        for gen_dir in self.GENERATED_DIRS:
            for search_path in self.repo_path.rglob(gen_dir):
                if not search_path.is_dir() or self._should_skip(search_path):
                    continue

                for file_pattern, class_regex in patterns:
                    for ts_file in search_path.glob(file_pattern):
                        self._process_generated_client(ts_file, class_regex)

    def _process_generated_client(self, file_path: Path, class_regex: str):
        """Process a generated API client file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = self._relative_path(file_path)

            # Check if it looks like generated code
            is_generated = any(marker in content for marker in [
                'AUTO GENERATED',
                'auto-generated',
                'Do not edit',
                'Generated by',
                'openapi-generator',
                'swagger-codegen',
                'ng-openapi-gen',
            ])

            if not is_generated:
                return

            # Find class name
            class_match = re.search(class_regex, content, re.DOTALL)
            if not class_match:
                return

            class_name = class_match.group(1)

            # Create component
            client = RawComponent(
                name=class_name,
                stereotype="generated_api_client",
                container_hint=self.container_id,
                file_path=rel_path,
                layer_hint="infrastructure",
            )

            client.metadata["generated"] = True
            client.tags.append("generated")
            client.tags.append("openapi-client")

            # Extract API paths from the file
            path_pattern = re.compile(r'[\'"`](/api/[^\'"` ]+)[\'"`]')
            api_paths = list(set(path_pattern.findall(content)))
            if api_paths:
                client.metadata["api_paths"] = api_paths[:20]  # Limit

            client.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=30,
                reason=f"Generated API client: {class_name}"
            )

            self.output.add_fact(client)
            logger.debug(f"[OpenAPICollector] Found generated client: {class_name}")

        except Exception as e:
            logger.debug(f"[OpenAPICollector] Error processing {file_path}: {e}")

    def _relative_path(self, file_path: Path) -> str:
        """Get relative path from repo root."""
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
