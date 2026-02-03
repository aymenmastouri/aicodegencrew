"""Container detector for architecture facts.

Detects containers based on:
- Build files (pom.xml, package.json, etc.)
- Config files (application.yml, angular.json, etc.)
- Directory structure
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_collector import CollectedEvidence
from ...shared.utils.logger import logger


class ContainerDetector:
    """Detects containers (deployable units) in a repository."""
    
    # Technology indicators
    INDICATORS = {
        # Backend
        "spring_boot": {
            "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "patterns": [r"spring-boot", r"org\.springframework"],
            "config": ["application.yml", "application.yaml", "application.properties"],
            "technology": "Spring Boot",
            "type": "application"
        },
        "node": {
            "files": ["package.json"],
            "patterns": [r'"express"', r'"fastify"', r'"nest"', r'"koa"'],
            "technology": "Node.js",
            "type": "application"
        },
        "python": {
            "files": ["requirements.txt", "pyproject.toml", "setup.py"],
            "patterns": [r"flask", r"django", r"fastapi"],
            "technology": "Python",
            "type": "application"
        },
        "dotnet": {
            "files": ["*.csproj", "*.sln"],
            "patterns": [r"Microsoft\.AspNetCore"],
            "technology": ".NET",
            "type": "application"
        },
        # Frontend
        "angular": {
            "files": ["angular.json"],
            "config": ["angular.json"],
            "technology": "Angular",
            "type": "application"
        },
        "react": {
            "files": ["package.json"],
            "patterns": [r'"react":', r'"react-dom":'],
            "technology": "React",
            "type": "application"
        },
        "vue": {
            "files": ["package.json"],
            "patterns": [r'"vue":', r'vue\.config\.js'],
            "technology": "Vue.js",
            "type": "application"
        },
    }
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.evidence: Dict[str, CollectedEvidence] = {}
        self._evidence_counter = 0
    
    def _next_evidence_id(self) -> str:
        self._evidence_counter += 1
        return f"ev_container_{self._evidence_counter:04d}"
    
    def detect(self) -> Tuple[List[Dict], Dict[str, CollectedEvidence]]:
        """
        Detect containers in the repository.
        
        Returns:
            Tuple of (containers, evidence)
        """
        containers = []
        
        # Check root level
        root_container = self._detect_at_path(self.repo_path, "")
        if root_container:
            containers.append(root_container)
        
        # Check common subdirectories
        subdirs_to_check = [
            "backend", "frontend", "api", "web", "app", "server", "client",
            "service", "services", "apps", "packages"
        ]
        
        for subdir in subdirs_to_check:
            subpath = self.repo_path / subdir
            if subpath.exists() and subpath.is_dir():
                container = self._detect_at_path(subpath, subdir)
                if container:
                    containers.append(container)
                
                # Check nested directories (monorepo style)
                if subdir in ["services", "apps", "packages"]:
                    for nested in subpath.iterdir():
                        if nested.is_dir():
                            nested_container = self._detect_at_path(nested, nested.name)
                            if nested_container:
                                containers.append(nested_container)
        
        # Deduplicate by technology + path
        seen = set()
        unique_containers = []
        for c in containers:
            key = (c["technology"], c.get("root_path", ""))
            if key not in seen:
                seen.add(key)
                unique_containers.append(c)
        
        logger.info(f"[ContainerDetector] Detected {len(unique_containers)} containers")
        return unique_containers, self.evidence
    
    def _detect_at_path(self, path: Path, container_name: str) -> Optional[Dict]:
        """Detect container at a specific path."""
        for indicator_id, indicator in self.INDICATORS.items():
            # Check for indicator files
            for file_pattern in indicator.get("files", []):
                if "*" in file_pattern:
                    matches = list(path.glob(file_pattern))
                else:
                    matches = [path / file_pattern] if (path / file_pattern).exists() else []
                
                if matches:
                    # Found a match, check patterns if specified
                    if "patterns" in indicator:
                        content = self._read_file(matches[0])
                        if not any(re.search(p, content) for p in indicator["patterns"]):
                            continue
                    
                    # Create evidence
                    rel_path = str(matches[0].relative_to(self.repo_path))
                    ev_id = self._next_evidence_id()
                    self.evidence[ev_id] = CollectedEvidence(
                        id=ev_id,
                        path=rel_path,
                        lines="1-10",
                        reason=f"Build/config file indicates {indicator['technology']}"
                    )
                    
                    # Determine container ID
                    if container_name:
                        cid = self._make_id(container_name)
                    else:
                        cid = self._make_id(indicator_id)
                    
                    return {
                        "id": cid,
                        "name": container_name or indicator_id,
                        "type": indicator["type"],
                        "technology": indicator["technology"],
                        "root_path": str(path.relative_to(self.repo_path)) if path != self.repo_path else ".",
                        "evidence": [ev_id]
                    }
        
        return None
    
    def _read_file(self, file_path: Path) -> str:
        """Read file content."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
    
    def _make_id(self, name: str) -> str:
        """Create a valid ID from name."""
        return re.sub(r'[^a-z0-9_]', '_', name.lower()).strip('_')
