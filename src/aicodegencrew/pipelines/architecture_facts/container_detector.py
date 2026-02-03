"""Container detector for architecture facts.

Detects containers based on:
- Build files (pom.xml, package.json, etc.)
- Config files (application.yml, angular.json, etc.)
- Directory structure

Also extracts technology stack with versions.
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

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
            "entry_points": ["src/main/java/**/Application.java", "src/main/java/**/*Application.java"],
            "technology": "Spring Boot",
            "type": "application",
            "category": "backend"
        },
        "quarkus": {
            "files": ["pom.xml", "build.gradle"],
            "patterns": [r"io\.quarkus", r"quarkus-"],
            "config": ["application.properties", "application.yaml"],
            "entry_points": ["src/main/java/**/*Resource.java"],
            "technology": "Quarkus",
            "type": "application",
            "category": "backend"
        },
        "node": {
            "files": ["package.json"],
            "patterns": [r'"express"', r'"fastify"', r'"nest"', r'"koa"'],
            "entry_points": ["src/index.ts", "src/main.ts", "src/app.ts", "index.js", "server.js"],
            "technology": "Node.js",
            "type": "application",
            "category": "backend"
        },
        "python": {
            "files": ["requirements.txt", "pyproject.toml", "setup.py"],
            "patterns": [r"flask", r"django", r"fastapi"],
            "entry_points": ["app.py", "main.py", "manage.py", "src/main.py"],
            "technology": "Python",
            "type": "application",
            "category": "backend"
        },
        "dotnet": {
            "files": ["*.csproj", "*.sln"],
            "patterns": [r"Microsoft\.AspNetCore"],
            "entry_points": ["Program.cs", "Startup.cs"],
            "technology": ".NET",
            "type": "application",
            "category": "backend"
        },
        # Frontend
        "angular": {
            "files": ["angular.json"],
            "config": ["angular.json"],
            "entry_points": ["src/main.ts", "src/app/app.module.ts", "src/app/app.config.ts"],
            "technology": "Angular",
            "type": "application",
            "category": "frontend"
        },
        "react": {
            "files": ["package.json"],
            "patterns": [r'"react":', r'"react-dom":'],
            "entry_points": ["src/index.tsx", "src/index.jsx", "src/App.tsx", "src/App.jsx"],
            "technology": "React",
            "type": "application",
            "category": "frontend"
        },
        "vue": {
            "files": ["package.json"],
            "patterns": [r'"vue":', r'vue\.config\.js'],
            "entry_points": ["src/main.ts", "src/main.js", "src/App.vue"],
            "technology": "Vue.js",
            "type": "application",
            "category": "frontend"
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
                    
                    container = {
                        "id": cid,
                        "name": container_name or indicator_id,
                        "type": indicator["type"],
                        "technology": indicator["technology"],
                        "category": indicator.get("category", "unknown"),
                        "root_path": str(path.relative_to(self.repo_path)) if path != self.repo_path else ".",
                        "evidence": [ev_id]
                    }
                    
                    # Find entry points
                    entry_points = self._find_entry_points(path, indicator.get("entry_points", []))
                    if entry_points:
                        container["entry_points"] = entry_points
                    
                    # Find config files
                    config_files = self._find_config_files(path, indicator.get("config", []))
                    if config_files:
                        container["config_files"] = config_files
                    
                    # Find module path (for Angular/React/Vue)
                    if indicator.get("category") == "frontend":
                        module_info = self._find_frontend_module(path, indicator["technology"])
                        if module_info:
                            container["module_info"] = module_info
                    
                    # Extract detailed technology stack with versions
                    tech_stack = self.extract_technology_stack(container, path)
                    if tech_stack:
                        container["technology_stack"] = tech_stack
                        logger.debug(f"[ContainerDetector] Extracted tech stack for {cid}: {tech_stack.get('framework', {})}")
                    
                    return container
        
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
    
    def _find_entry_points(self, path: Path, patterns: List[str]) -> List[str]:
        """Find entry point files matching patterns."""
        entry_points = []
        for pattern in patterns:
            if "**" in pattern:
                matches = list(path.glob(pattern))
            else:
                match_path = path / pattern
                matches = [match_path] if match_path.exists() else []
            
            for m in matches:
                try:
                    rel = str(m.relative_to(path))
                    if rel not in entry_points:
                        entry_points.append(rel)
                except ValueError:
                    pass
        return entry_points
    
    def _find_config_files(self, path: Path, patterns: List[str]) -> List[str]:
        """Find config files matching patterns."""
        config_files = []
        for pattern in patterns:
            match_path = path / pattern
            if match_path.exists():
                config_files.append(pattern)
        return config_files
    
    def _find_frontend_module(self, path: Path, technology: str) -> Optional[Dict[str, Any]]:
        """Find frontend module/entry point info."""
        module_info = {}
        
        if technology == "Angular":
            # Check for Angular module structure
            app_module = path / "src" / "app" / "app.module.ts"
            app_config = path / "src" / "app" / "app.config.ts"  # Standalone API (Angular 14+)
            app_component = path / "src" / "app" / "app.component.ts"
            main_ts = path / "src" / "main.ts"
            
            if app_module.exists():
                module_info["type"] = "NgModule"
                module_info["module_path"] = "src/app/app.module.ts"
            elif app_config.exists():
                module_info["type"] = "Standalone"
                module_info["module_path"] = "src/app/app.config.ts"
            
            if app_component.exists():
                module_info["root_component"] = "src/app/app.component.ts"
            
            if main_ts.exists():
                module_info["entry_point"] = "src/main.ts"
                # Check if standalone or module bootstrap
                content = self._read_file(main_ts)
                if "bootstrapApplication" in content:
                    module_info["bootstrap"] = "standalone"
                elif "bootstrapModule" in content:
                    module_info["bootstrap"] = "module"
            
            # Find routing module
            routing_module = path / "src" / "app" / "app-routing.module.ts"
            app_routes = path / "src" / "app" / "app.routes.ts"
            if routing_module.exists():
                module_info["routing"] = "src/app/app-routing.module.ts"
            elif app_routes.exists():
                module_info["routing"] = "src/app/app.routes.ts"
        
        elif technology == "React":
            # React entry points
            for entry in ["src/index.tsx", "src/index.jsx", "src/index.js"]:
                if (path / entry).exists():
                    module_info["entry_point"] = entry
                    break
            
            for app in ["src/App.tsx", "src/App.jsx", "src/App.js"]:
                if (path / app).exists():
                    module_info["root_component"] = app
                    break
        
        elif technology == "Vue.js":
            # Vue entry points
            for entry in ["src/main.ts", "src/main.js"]:
                if (path / entry).exists():
                    module_info["entry_point"] = entry
                    break
            
            if (path / "src" / "App.vue").exists():
                module_info["root_component"] = "src/App.vue"
            
            # Vue Router
            if (path / "src" / "router" / "index.ts").exists():
                module_info["routing"] = "src/router/index.ts"
            elif (path / "src" / "router" / "index.js").exists():
                module_info["routing"] = "src/router/index.js"
        
        return module_info if module_info else None
    
    # =========================================================================
    # TECHNOLOGY STACK EXTRACTION
    # =========================================================================
    
    def extract_technology_stack(self, container: Dict, path: Path) -> Dict[str, Any]:
        """
        Extract detailed technology stack with versions for a container.
        
        Returns dict with:
        - language: {name, version}
        - framework: {name, version}
        - build_tool: {name, version}
        - runtime: {name, version}  (optional)
        - key_dependencies: [{name, version, category}]
        - test_frameworks: [{name, version}]
        - security_frameworks: [{name, version}]
        """
        tech = container.get("technology", "")
        
        if "Spring" in tech:
            return self._extract_java_stack(path)
        elif "Angular" in tech:
            return self._extract_angular_stack(path)
        elif "React" in tech:
            return self._extract_react_stack(path)
        elif "Vue" in tech:
            return self._extract_vue_stack(path)
        elif "Node" in tech:
            return self._extract_node_stack(path)
        elif ".NET" in tech:
            return self._extract_dotnet_stack(path)
        elif "Python" in tech:
            return self._extract_python_stack(path)
        
        return {}
    
    def _extract_java_stack(self, path: Path) -> Dict[str, Any]:
        """Extract Java/Spring Boot technology stack from pom.xml or build.gradle."""
        stack = {
            "language": {"name": "Java", "version": None},
            "framework": {"name": "Spring Boot", "version": None},
            "build_tool": {"name": None, "version": None},
            "key_dependencies": [],
            "test_frameworks": [],
            "security_frameworks": [],
        }
        
        # Try pom.xml first
        pom_path = path / "pom.xml"
        if pom_path.exists():
            stack["build_tool"]["name"] = "Maven"
            self._parse_pom_xml(pom_path, stack)
        else:
            # Try build.gradle
            gradle_path = path / "build.gradle"
            gradle_kts_path = path / "build.gradle.kts"
            if gradle_path.exists():
                stack["build_tool"]["name"] = "Gradle"
                self._parse_build_gradle(gradle_path, stack)
            elif gradle_kts_path.exists():
                stack["build_tool"]["name"] = "Gradle (Kotlin DSL)"
                self._parse_build_gradle(gradle_kts_path, stack)
        
        return stack
    
    def _parse_pom_xml(self, pom_path: Path, stack: Dict):
        """Parse pom.xml to extract versions and dependencies."""
        try:
            content = self._read_file(pom_path)
            
            # Java version patterns
            java_patterns = [
                r'<java\.version>(\d+)</java\.version>',
                r'<maven\.compiler\.source>(\d+)</maven\.compiler\.source>',
                r'<maven\.compiler\.target>(\d+)</maven\.compiler\.target>',
                r'<release>(\d+)</release>',
            ]
            for pattern in java_patterns:
                match = re.search(pattern, content)
                if match:
                    stack["language"]["version"] = match.group(1)
                    break
            
            # Spring Boot version (parent or dependency)
            spring_boot_patterns = [
                r'<artifactId>spring-boot-starter-parent</artifactId>\s*<version>([^<]+)</version>',
                r'<spring-boot\.version>([^<]+)</spring-boot\.version>',
                r'<spring\.boot\.version>([^<]+)</spring\.boot\.version>',
            ]
            for pattern in spring_boot_patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    stack["framework"]["version"] = match.group(1)
                    break
            
            # Key dependencies with categories
            key_deps = {
                "spring-boot-starter-web": "web",
                "spring-boot-starter-data-jpa": "persistence",
                "spring-boot-starter-data-jdbc": "persistence",
                "spring-boot-starter-security": "security",
                "spring-boot-starter-oauth2": "security",
                "spring-boot-starter-actuator": "monitoring",
                "spring-boot-starter-validation": "validation",
                "spring-boot-starter-cache": "caching",
                "spring-boot-starter-amqp": "messaging",
                "spring-kafka": "messaging",
                "lombok": "tooling",
                "mapstruct": "tooling",
                "flyway-core": "database-migration",
                "liquibase-core": "database-migration",
            }
            
            for dep, category in key_deps.items():
                if f'<artifactId>{dep}</artifactId>' in content:
                    # Try to find version
                    version_pattern = rf'<artifactId>{dep}</artifactId>\s*<version>([^<]+)</version>'
                    version_match = re.search(version_pattern, content, re.DOTALL)
                    version = version_match.group(1) if version_match else "managed"
                    stack["key_dependencies"].append({
                        "name": dep,
                        "version": version,
                        "category": category
                    })
            
            # Test frameworks
            test_deps = ["spring-boot-starter-test", "junit-jupiter", "mockito", "testcontainers", "assertj"]
            for dep in test_deps:
                if f'<artifactId>{dep}' in content:
                    stack["test_frameworks"].append({"name": dep, "version": "managed"})
            
            # Security frameworks
            security_deps = ["spring-security", "oauth2", "jwt", "keycloak"]
            for dep in security_deps:
                if dep in content.lower():
                    stack["security_frameworks"].append({"name": dep, "version": "detected"})
            
            # Database drivers (detect which databases)
            db_drivers = {
                "postgresql": "PostgreSQL",
                "mysql-connector": "MySQL",
                "oracle": "Oracle",
                "h2": "H2 (in-memory)",
                "mssql": "SQL Server",
                "mariadb": "MariaDB",
            }
            for driver, db_name in db_drivers.items():
                if driver in content.lower():
                    stack["key_dependencies"].append({
                        "name": db_name,
                        "version": "detected",
                        "category": "database-driver"
                    })
            
            logger.info(f"[ContainerDetector] Parsed pom.xml: Java {stack['language']['version']}, Spring Boot {stack['framework']['version']}")
            
        except Exception as e:
            logger.warning(f"[ContainerDetector] Failed to parse pom.xml: {e}")
    
    def _parse_build_gradle(self, gradle_path: Path, stack: Dict):
        """Parse build.gradle to extract versions."""
        try:
            content = self._read_file(gradle_path)
            
            # Java version
            java_match = re.search(r'sourceCompatibility\s*=\s*[\'"]?(\d+)', content)
            if java_match:
                stack["language"]["version"] = java_match.group(1)
            
            # Spring Boot version
            sb_match = re.search(r'org\.springframework\.boot[\'"]?\s*version\s*[\'"]([^\'\"]+)', content)
            if not sb_match:
                sb_match = re.search(r'spring-boot[\'"\s:]+(\d+\.\d+\.\d+)', content)
            if sb_match:
                stack["framework"]["version"] = sb_match.group(1)
            
            logger.info(f"[ContainerDetector] Parsed build.gradle: Java {stack['language']['version']}, Spring Boot {stack['framework']['version']}")
            
        except Exception as e:
            logger.warning(f"[ContainerDetector] Failed to parse build.gradle: {e}")
    
    def _extract_angular_stack(self, path: Path) -> Dict[str, Any]:
        """Extract Angular/TypeScript technology stack from package.json."""
        stack = {
            "language": {"name": "TypeScript", "version": None},
            "framework": {"name": "Angular", "version": None},
            "build_tool": {"name": "npm", "version": None},
            "runtime": {"name": "Node.js", "version": None},
            "key_dependencies": [],
            "test_frameworks": [],
            "ui_frameworks": [],
        }
        
        pkg_path = path / "package.json"
        if not pkg_path.exists():
            # Check parent for frontend folder
            pkg_path = path.parent / "package.json"
        
        if pkg_path.exists():
            self._parse_package_json(pkg_path, stack, framework="angular")
        
        return stack
    
    def _extract_react_stack(self, path: Path) -> Dict[str, Any]:
        """Extract React technology stack."""
        stack = {
            "language": {"name": "JavaScript/TypeScript", "version": None},
            "framework": {"name": "React", "version": None},
            "build_tool": {"name": "npm", "version": None},
            "key_dependencies": [],
            "test_frameworks": [],
            "ui_frameworks": [],
        }
        
        pkg_path = path / "package.json"
        if pkg_path.exists():
            self._parse_package_json(pkg_path, stack, framework="react")
        
        return stack
    
    def _extract_vue_stack(self, path: Path) -> Dict[str, Any]:
        """Extract Vue.js technology stack."""
        stack = {
            "language": {"name": "JavaScript/TypeScript", "version": None},
            "framework": {"name": "Vue.js", "version": None},
            "build_tool": {"name": "npm", "version": None},
            "key_dependencies": [],
            "test_frameworks": [],
            "ui_frameworks": [],
        }
        
        pkg_path = path / "package.json"
        if pkg_path.exists():
            self._parse_package_json(pkg_path, stack, framework="vue")
        
        return stack
    
    def _extract_node_stack(self, path: Path) -> Dict[str, Any]:
        """Extract Node.js backend technology stack."""
        stack = {
            "language": {"name": "JavaScript/TypeScript", "version": None},
            "framework": {"name": "Node.js", "version": None},
            "build_tool": {"name": "npm", "version": None},
            "key_dependencies": [],
            "test_frameworks": [],
        }
        
        pkg_path = path / "package.json"
        if pkg_path.exists():
            self._parse_package_json(pkg_path, stack, framework="node")
        
        return stack
    
    def _extract_dotnet_stack(self, path: Path) -> Dict[str, Any]:
        """Extract .NET technology stack."""
        stack = {
            "language": {"name": "C#", "version": None},
            "framework": {"name": ".NET", "version": None},
            "build_tool": {"name": "dotnet CLI", "version": None},
            "key_dependencies": [],
        }
        
        # Find .csproj file
        csproj_files = list(path.glob("*.csproj"))
        if csproj_files:
            self._parse_csproj(csproj_files[0], stack)
        
        return stack
    
    def _extract_python_stack(self, path: Path) -> Dict[str, Any]:
        """Extract Python technology stack."""
        stack = {
            "language": {"name": "Python", "version": None},
            "framework": {"name": None, "version": None},
            "build_tool": {"name": "pip", "version": None},
            "key_dependencies": [],
        }
        
        # Check pyproject.toml first
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            self._parse_pyproject_toml(pyproject, stack)
        else:
            # Check requirements.txt
            requirements = path / "requirements.txt"
            if requirements.exists():
                self._parse_requirements_txt(requirements, stack)
        
        return stack
    
    def _parse_package_json(self, pkg_path: Path, stack: Dict, framework: str = ""):
        """Parse package.json for versions and dependencies."""
        try:
            content = self._read_file(pkg_path)
            pkg = json.loads(content)
            
            deps = pkg.get("dependencies", {})
            dev_deps = pkg.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}
            
            # TypeScript version
            if "typescript" in all_deps:
                stack["language"]["version"] = all_deps["typescript"].lstrip("^~")
            
            # Framework version
            if framework == "angular" and "@angular/core" in deps:
                stack["framework"]["version"] = deps["@angular/core"].lstrip("^~")
            elif framework == "react" and "react" in deps:
                stack["framework"]["version"] = deps["react"].lstrip("^~")
            elif framework == "vue" and "vue" in deps:
                stack["framework"]["version"] = deps["vue"].lstrip("^~")
            
            # Node.js version from engines
            engines = pkg.get("engines", {})
            if "node" in engines:
                stack["runtime"] = {"name": "Node.js", "version": engines["node"]}
            
            # Key Angular dependencies
            angular_deps = {
                "@angular/material": "ui",
                "@angular/cdk": "ui",
                "@ngrx/store": "state-management",
                "@ngrx/effects": "state-management",
                "rxjs": "core",
                "@angular/router": "routing",
                "@angular/forms": "forms",
                "@angular/http": "http",
            }
            
            # Key React dependencies
            react_deps = {
                "redux": "state-management",
                "@reduxjs/toolkit": "state-management",
                "react-router": "routing",
                "axios": "http",
                "styled-components": "ui",
                "@mui/material": "ui",
                "tailwindcss": "ui",
            }
            
            # Key Vue dependencies
            vue_deps = {
                "vuex": "state-management",
                "pinia": "state-management",
                "vue-router": "routing",
                "vuetify": "ui",
            }
            
            # Select appropriate deps
            key_deps_map = angular_deps if framework == "angular" else (
                react_deps if framework == "react" else (
                    vue_deps if framework == "vue" else {}
                )
            )
            
            for dep, category in key_deps_map.items():
                if dep in deps:
                    stack["key_dependencies"].append({
                        "name": dep,
                        "version": deps[dep].lstrip("^~"),
                        "category": category
                    })
            
            # Test frameworks
            test_deps = ["jest", "jasmine", "karma", "cypress", "playwright", "@testing-library"]
            for dep in test_deps:
                for d in all_deps:
                    if dep in d:
                        stack["test_frameworks"].append({
                            "name": d,
                            "version": all_deps[d].lstrip("^~")
                        })
                        break
            
            # UI frameworks
            ui_deps = ["bootstrap", "tailwind", "material", "primeng", "ng-zorro", "antd"]
            for dep in ui_deps:
                for d in deps:
                    if dep in d.lower():
                        if "ui_frameworks" not in stack:
                            stack["ui_frameworks"] = []
                        stack["ui_frameworks"].append({
                            "name": d,
                            "version": deps[d].lstrip("^~")
                        })
            
            logger.info(f"[ContainerDetector] Parsed package.json: {stack['framework']['name']} {stack['framework']['version']}")
            
        except json.JSONDecodeError as e:
            logger.warning(f"[ContainerDetector] Failed to parse package.json: {e}")
        except Exception as e:
            logger.warning(f"[ContainerDetector] Error parsing package.json: {e}")
    
    def _parse_csproj(self, csproj_path: Path, stack: Dict):
        """Parse .csproj for .NET versions."""
        try:
            content = self._read_file(csproj_path)
            
            # Target framework
            tf_match = re.search(r'<TargetFramework>net(\d+\.?\d*)</TargetFramework>', content)
            if tf_match:
                stack["framework"]["version"] = tf_match.group(1)
            
            # Language version
            lang_match = re.search(r'<LangVersion>(\d+\.?\d*)</LangVersion>', content)
            if lang_match:
                stack["language"]["version"] = lang_match.group(1)
            
        except Exception as e:
            logger.warning(f"[ContainerDetector] Failed to parse .csproj: {e}")
    
    def _parse_pyproject_toml(self, pyproject_path: Path, stack: Dict):
        """Parse pyproject.toml for Python versions."""
        try:
            content = self._read_file(pyproject_path)
            
            # Python version
            py_match = re.search(r'python\s*=\s*["\']([^"\']+)["\']', content)
            if py_match:
                stack["language"]["version"] = py_match.group(1)
            
            # Detect framework
            if "fastapi" in content.lower():
                stack["framework"]["name"] = "FastAPI"
            elif "flask" in content.lower():
                stack["framework"]["name"] = "Flask"
            elif "django" in content.lower():
                stack["framework"]["name"] = "Django"
            
        except Exception as e:
            logger.warning(f"[ContainerDetector] Failed to parse pyproject.toml: {e}")
    
    def _parse_requirements_txt(self, req_path: Path, stack: Dict):
        """Parse requirements.txt for Python dependencies."""
        try:
            content = self._read_file(req_path)
            
            if "fastapi" in content.lower():
                stack["framework"]["name"] = "FastAPI"
            elif "flask" in content.lower():
                stack["framework"]["name"] = "Flask"
            elif "django" in content.lower():
                stack["framework"]["name"] = "Django"
            
        except Exception as e:
            logger.warning(f"[ContainerDetector] Failed to parse requirements.txt: {e}")
