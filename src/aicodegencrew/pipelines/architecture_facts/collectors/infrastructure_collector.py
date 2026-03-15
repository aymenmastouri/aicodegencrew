"""
InfrastructureCollector - Extracts infrastructure facts.

Detects:
- Dockerfiles
- docker-compose.yml
- Kubernetes manifests
- CI/CD pipelines
- Environment configuration

Output -> infrastructure.json
"""

import re
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawInfraFact


class InfrastructureCollector(DimensionCollector):
    """
    Extracts infrastructure and deployment facts.
    """

    DIMENSION = "infrastructure"

    # Skip directories
    SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", "target", ".venv"}

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        """Collect infrastructure facts."""
        self._log_start()

        # Docker
        self._collect_docker()

        # Docker Compose
        self._collect_compose()

        # Kubernetes
        self._collect_kubernetes()

        # CI/CD
        self._collect_cicd()

        # Environment config
        self._collect_env_config()

        self._log_end()
        return self.output

    def _collect_docker(self):
        """Collect Dockerfile facts."""
        dockerfiles = []
        for pattern in ["Dockerfile", "Dockerfile.*", "*.dockerfile"]:
            dockerfiles.extend(self._find_files(pattern))

        for dockerfile in dockerfiles:
            content = self._read_file_content(dockerfile)
            rel_path = self._relative_path(dockerfile)

            # Extract base image
            from_match = re.search(r"^FROM\s+([^\s]+)", content, re.MULTILINE)
            base_image = from_match.group(1) if from_match else "unknown"

            # Extract exposed ports
            ports = re.findall(r"^EXPOSE\s+(\d+)", content, re.MULTILINE)

            # Extract environment variables
            env_vars = re.findall(r"^ENV\s+(\w+)", content, re.MULTILINE)

            fact = RawInfraFact(
                name=dockerfile.name,
                type="dockerfile",
                category="container",
            )

            fact.metadata["base_image"] = base_image
            if ports:
                fact.metadata["exposed_ports"] = [int(p) for p in ports]
            if env_vars:
                fact.metadata["env_vars"] = env_vars[:10]

            fact.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=min(30, content.count("\n") + 1),
                reason=f"Dockerfile: {dockerfile.name} (base: {base_image})",
            )

            self.output.add_fact(fact)

    def _collect_compose(self):
        """Collect docker-compose facts."""
        compose_names = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]

        for name in compose_names:
            compose_file = self.repo_path / name
            if not compose_file.exists():
                continue

            content = self._read_file_content(compose_file)
            rel_path = self._relative_path(compose_file)

            # Extract services
            services = re.findall(r"^  ([\w][\w-]*):\s*(?:#.*)?$", content, re.MULTILINE)

            # Extract images
            images = re.findall(r"image:\s*([^\s]+)", content)

            # Extract ports
            ports = re.findall(r'-\s*["\']?(\d+):(\d+)', content)

            fact = RawInfraFact(
                name=name,
                type="docker_compose",
                category="orchestration",
            )

            fact.metadata["services"] = services
            fact.metadata["images"] = images[:10]
            if ports:
                fact.metadata["port_mappings"] = [f"{h}:{c}" for h, c in ports]

            fact.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=min(50, content.count("\n") + 1),
                reason=f"Docker Compose: {len(services)} services",
            )

            self.output.add_fact(fact)

    def _collect_kubernetes(self):
        """Collect Kubernetes manifest facts."""
        k8s_dirs = ["k8s", "kubernetes", "deploy", "manifests", "charts", "helm"]

        for dir_name in k8s_dirs:
            k8s_path = self.repo_path / dir_name
            if not k8s_path.exists():
                continue

            yaml_files = self._find_files("*.yaml", k8s_path) + self._find_files("*.yml", k8s_path)

            for yaml_file in yaml_files:
                content = self._read_file_content(yaml_file)
                rel_path = self._relative_path(yaml_file)

                # Detect resource type
                kind_match = re.search(r"kind:\s*(\w+)", content)
                if not kind_match:
                    continue

                kind = kind_match.group(1)

                # Get name
                name_match = re.search(r"name:\s*([^\s]+)", content)
                resource_name = name_match.group(1) if name_match else yaml_file.stem

                fact = RawInfraFact(
                    name=resource_name,
                    type=f"k8s_{kind.lower()}",
                    category="orchestration",
                )

                fact.metadata["kind"] = kind
                fact.metadata["file"] = rel_path

                # Extract specific info based on kind
                if kind == "Deployment":
                    replicas_match = re.search(r"replicas:\s*(\d+)", content)
                    if replicas_match:
                        fact.metadata["replicas"] = int(replicas_match.group(1))

                    image_match = re.search(r"image:\s*([^\s]+)", content)
                    if image_match:
                        fact.metadata["image"] = image_match.group(1)

                elif kind == "Service":
                    type_match = re.search(r"type:\s*(\w+)", content)
                    if type_match:
                        fact.metadata["service_type"] = type_match.group(1)

                    ports = re.findall(r"port:\s*(\d+)", content)
                    if ports:
                        fact.metadata["ports"] = [int(p) for p in ports]

                elif kind == "Ingress":
                    hosts = re.findall(r"host:\s*([^\s]+)", content)
                    if hosts:
                        fact.metadata["hosts"] = hosts

                fact.add_evidence(
                    path=rel_path,
                    line_start=1,
                    line_end=min(30, content.count("\n") + 1),
                    reason=f"Kubernetes {kind}: {resource_name}",
                )

                self.output.add_fact(fact)

    def _collect_cicd(self):
        """Collect CI/CD pipeline facts."""
        ci_files = [
            (".github/workflows", "*.yml", "github_actions"),
            (".gitlab-ci.yml", None, "gitlab_ci"),
            ("Jenkinsfile", None, "jenkins"),
            ("azure-pipelines.yml", None, "azure_devops"),
            (".circleci/config.yml", None, "circleci"),
        ]

        for path, pattern, ci_type in ci_files:
            target = self.repo_path / path

            if target.is_file():
                self._process_ci_file(target, ci_type)
            elif target.is_dir() and pattern:
                for ci_file in target.glob(pattern):
                    self._process_ci_file(ci_file, ci_type)

    def _process_ci_file(self, file_path: Path, ci_type: str):
        """Process a CI/CD configuration file."""
        content = self._read_file_content(file_path)
        rel_path = self._relative_path(file_path)

        fact = RawInfraFact(
            name=file_path.name,
            type="ci_pipeline",
            category="ci_cd",
        )

        fact.metadata["ci_system"] = ci_type

        # Extract jobs/stages based on CI system
        if ci_type == "github_actions":
            jobs = re.findall(r"^\s{2}(\w+):\s*$", content, re.MULTILINE)
            fact.metadata["jobs"] = jobs[:10]
        elif ci_type == "gitlab_ci":
            stages_block_match = re.search(r'^stages:\s*\n((?:[ \t]+-[^\n]+\n?)*)', content, re.MULTILINE)
            if stages_block_match:
                stages = re.findall(r'-\s*([\w][\w-]*)', stages_block_match.group(1))
            else:
                stages = []
            fact.metadata["stages"] = stages[:10]

        fact.add_evidence(
            path=rel_path, line_start=1, line_end=min(50, content.count("\n") + 1), reason=f"CI/CD Pipeline: {ci_type}"
        )

        self.output.add_fact(fact)

    def _collect_env_config(self):
        """Collect environment configuration files."""
        env_files = list(self.repo_path.glob(".env*")) + list(self.repo_path.glob("*.env"))

        for env_file in env_files:
            if not env_file.is_file():
                continue

            content = self._read_file_content(env_file)
            rel_path = self._relative_path(env_file)

            # Count variables (don't expose values)
            var_count = len(re.findall(r"^[A-Z_]+=", content, re.MULTILINE))

            fact = RawInfraFact(
                name=env_file.name,
                type="env_file",
                category="configuration",
            )

            fact.metadata["variable_count"] = var_count

            fact.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=1,
                reason=f"Environment file: {env_file.name} ({var_count} variables)",
            )

            self.output.add_fact(fact)
