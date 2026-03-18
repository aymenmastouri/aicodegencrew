"""API Contracts Collector — OpenAPI, gRPC proto, GraphQL, AsyncAPI, WSDL.

Cross-cutting collector that discovers API contract/specification files.
Extracts endpoint counts, schema info, and API versioning.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawApiContractFact


class ApiContractsCollector(DimensionCollector):
    DIMENSION = "api_contracts"

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_openapi_specs()
        self._collect_grpc_protos()
        self._collect_graphql_schemas()
        self._collect_asyncapi_specs()
        self._collect_wsdl_files()
        self._log_end()
        return self.output

    def _collect_openapi_specs(self):
        """Find OpenAPI/Swagger specification files."""
        for pattern in ("openapi.json", "openapi.yml", "openapi.yaml",
                        "swagger.json", "swagger.yml", "swagger.yaml",
                        "api-docs.json", "api-docs.yml", "api-docs.yaml",
                        "api-spec.json", "api-spec.yml", "api-spec.yaml"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                rel = self._relative_path(path)
                lines = content.splitlines()

                # Try to extract version and endpoint count
                version = ""
                endpoint_count = 0
                if path.suffix == ".json":
                    try:
                        spec = json.loads(content)
                        version = spec.get("info", {}).get("version", "")
                        paths = spec.get("paths", {})
                        endpoint_count = sum(
                            len([m for m in v if m in ("get", "post", "put", "delete", "patch")])
                            for v in paths.values() if isinstance(v, dict)
                        )
                    except (json.JSONDecodeError, AttributeError):
                        pass
                else:
                    # YAML — simple regex counting
                    version_match = re.search(r"version:\s*['\"]?([^\s'\"]+)", content)
                    if version_match:
                        version = version_match.group(1)
                    # Count HTTP method entries under paths
                    endpoint_count = len(re.findall(r"^\s+(?:get|post|put|delete|patch):", content, re.MULTILINE))

                fmt = "json" if path.suffix == ".json" else "yaml"
                fact = RawApiContractFact(
                    name=f"openapi:{path.name}",
                    contract_type="openapi",
                    format=fmt,
                    file_path=rel,
                    endpoint_count=endpoint_count,
                    version=version,
                )
                fact.add_evidence(rel, 1, min(len(lines), 20), f"OpenAPI spec: {endpoint_count} endpoints, version {version or 'unknown'}")
                self.output.add_fact(fact)

    def _collect_grpc_protos(self):
        """Find gRPC .proto files and extract service/rpc counts."""
        for path in self._find_files("*.proto"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            services = re.findall(r"service\s+(\w+)", content)
            rpcs = re.findall(r"rpc\s+(\w+)", content)
            # Extract package as version hint
            pkg_match = re.search(r"package\s+([\w.]+)", content)
            pkg = pkg_match.group(1) if pkg_match else ""

            fact = RawApiContractFact(
                name=f"grpc:{path.name}",
                contract_type="grpc_proto",
                format="proto",
                file_path=rel,
                endpoint_count=len(rpcs),
                version=pkg,
            )
            fact.metadata["services"] = services
            fact.metadata["rpc_count"] = len(rpcs)
            fact.add_evidence(rel, 1, min(len(lines), 20), f"gRPC proto: {len(services)} services, {len(rpcs)} RPCs")
            self.output.add_fact(fact)

    def _collect_graphql_schemas(self):
        """Find GraphQL schema files."""
        for pattern in ("*.graphql", "*.gql", "schema.graphqls"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                rel = self._relative_path(path)
                lines = content.splitlines()

                types = re.findall(r"type\s+(\w+)", content)
                queries = re.findall(r"(?:type\s+Query\s*\{[^}]*)", content, re.DOTALL)
                mutations = re.findall(r"(?:type\s+Mutation\s*\{[^}]*)", content, re.DOTALL)

                # Count fields in Query and Mutation
                query_fields = len(re.findall(r"^\s+\w+", queries[0], re.MULTILINE)) if queries else 0
                mutation_fields = len(re.findall(r"^\s+\w+", mutations[0], re.MULTILINE)) if mutations else 0

                fact = RawApiContractFact(
                    name=f"graphql:{path.name}",
                    contract_type="graphql_schema",
                    format="graphql",
                    file_path=rel,
                    endpoint_count=query_fields + mutation_fields,
                )
                fact.metadata["type_count"] = len(types)
                fact.metadata["query_count"] = query_fields
                fact.metadata["mutation_count"] = mutation_fields
                fact.add_evidence(rel, 1, min(len(lines), 20), f"GraphQL: {len(types)} types, {query_fields} queries, {mutation_fields} mutations")
                self.output.add_fact(fact)

    def _collect_asyncapi_specs(self):
        """Find AsyncAPI specification files."""
        for pattern in ("asyncapi.json", "asyncapi.yml", "asyncapi.yaml"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                rel = self._relative_path(path)
                lines = content.splitlines()

                # Count channels
                channel_count = len(re.findall(r"^\s{2}\w+.*:", content, re.MULTILINE))
                version_match = re.search(r"version:\s*['\"]?([^\s'\"]+)", content)
                version = version_match.group(1) if version_match else ""

                fmt = "json" if path.suffix == ".json" else "yaml"
                fact = RawApiContractFact(
                    name=f"asyncapi:{path.name}",
                    contract_type="asyncapi",
                    format=fmt,
                    file_path=rel,
                    endpoint_count=channel_count,
                    version=version,
                )
                fact.add_evidence(rel, 1, min(len(lines), 20), f"AsyncAPI: {channel_count} channels")
                self.output.add_fact(fact)

    def _collect_wsdl_files(self):
        """Find WSDL service definition files."""
        for path in self._find_files("*.wsdl"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            operations = re.findall(r"<wsdl:operation\s+name=\"(\w+)\"", content)
            if not operations:
                operations = re.findall(r"<operation\s+name=\"(\w+)\"", content)

            fact = RawApiContractFact(
                name=f"wsdl:{path.name}",
                contract_type="wsdl",
                format="xml",
                file_path=rel,
                endpoint_count=len(operations),
            )
            fact.add_evidence(rel, 1, min(len(lines), 20), f"WSDL: {len(operations)} operations")
            self.output.add_fact(fact)
