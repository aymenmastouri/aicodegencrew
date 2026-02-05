"""
SpringConfigCollector - Extracts configuration facts.

Detects:
- @Configuration classes
- @Bean definitions
- application.yml / application.properties
- Spring profiles
- Property sources

Output feeds → infrastructure.json (config components)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..base import DimensionCollector, CollectorOutput, RawComponent, RawInfraFact
from .....shared.utils.logger import logger


class SpringConfigCollector(DimensionCollector):
    """
    Extracts Spring configuration facts.
    """
    
    DIMENSION = "spring_config"
    
    # Patterns
    CONFIGURATION_PATTERN = re.compile(r'@Configuration')
    BEAN_PATTERN = re.compile(r'@Bean')
    CLASS_PATTERN = re.compile(r'^(?:public\s+)?class\s+([A-Z]\w*)', re.MULTILINE)
    
    # Profile patterns
    PROFILE_PATTERN = re.compile(r'@Profile\s*\(\s*["\']([^"\']+)["\']')
    CONDITIONAL_PATTERN = re.compile(r'@Conditional\w+')
    
    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
    
    def collect(self) -> CollectorOutput:
        """Collect Spring configuration facts."""
        self._log_start()
        
        # Collect @Configuration classes
        self._collect_configuration_classes()
        
        # Collect application.yml/properties
        self._collect_config_files()
        
        # Collect profiles
        self._collect_profiles()
        
        self._log_end()
        return self.output
    
    def _collect_configuration_classes(self):
        """Collect @Configuration annotated classes (Java and Kotlin)."""
        # Collect Java and Kotlin files
        java_files = self._find_files("*.java")
        kotlin_files = self._find_files("*.kt")
        all_files = java_files + kotlin_files
        
        for src_file in all_files:
            content = self._read_file_content(src_file)
            
            if not self.CONFIGURATION_PATTERN.search(content):
                continue
            
            lines = self._read_file(src_file)
            rel_path = self._relative_path(src_file)
            
            # Get class name
            class_match = self.CLASS_PATTERN.search(content)
            if not class_match:
                continue
            
            class_name = class_match.group(1)
            class_line = self._find_line_number(lines, f"class {class_name}")
            
            # Count @Bean methods
            bean_count = len(self.BEAN_PATTERN.findall(content))
            
            # Check for profile
            profile_match = self.PROFILE_PATTERN.search(content)
            profile = profile_match.group(1) if profile_match else None
            
            # Check for conditionals
            has_conditionals = bool(self.CONDITIONAL_PATTERN.search(content))
            
            config = RawComponent(
                name=class_name,
                stereotype="configuration",
                container_hint=self.container_id,
                module=self._derive_module(rel_path),
                file_path=rel_path,
                layer_hint="infrastructure",
            )
            
            config.metadata["bean_count"] = bean_count
            if profile:
                config.metadata["profile"] = profile
            if has_conditionals:
                config.metadata["conditional"] = True
            
            config.add_evidence(
                path=rel_path,
                line_start=class_line - 1,
                line_end=class_line + 5,
                reason=f"@Configuration: {class_name} ({bean_count} beans)"
            )
            
            self.output.add_fact(config)
    
    def _collect_config_files(self):
        """Collect application.yml/properties files."""
        config_patterns = [
            "application.yml",
            "application.yaml",
            "application.properties",
            "application-*.yml",
            "application-*.yaml",
            "application-*.properties",
            "bootstrap.yml",
            "bootstrap.yaml",
        ]
        
        for pattern in config_patterns:
            config_files = self._find_files(pattern)
            
            for config_file in config_files:
                rel_path = self._relative_path(config_file)
                
                # Determine profile from filename
                profile = None
                if "-" in config_file.stem:
                    parts = config_file.stem.split("-", 1)
                    if len(parts) > 1 and parts[0] == "application":
                        profile = parts[1]
                
                config = RawInfraFact(
                    name=config_file.name,
                    type="config_file",
                    category="configuration",
                )
                
                if profile:
                    config.metadata["profile"] = profile
                
                # Extract some key properties
                content = self._read_file_content(config_file)
                config.metadata["size_lines"] = content.count('\n')
                
                # Look for common properties
                props_found = []
                if "spring.datasource" in content:
                    props_found.append("datasource")
                if "spring.jpa" in content:
                    props_found.append("jpa")
                if "spring.security" in content:
                    props_found.append("security")
                if "spring.kafka" in content or "spring.rabbitmq" in content:
                    props_found.append("messaging")
                if "spring.cloud" in content:
                    props_found.append("cloud")
                
                if props_found:
                    config.metadata["configures"] = props_found
                
                config.add_evidence(
                    path=rel_path,
                    line_start=1,
                    line_end=min(20, content.count('\n')),
                    reason=f"Spring config file: {config_file.name}"
                )
                
                self.output.add_fact(config)
    
    def _collect_profiles(self):
        """Collect Spring profiles from config files."""
        profiles_found = set()
        
        # From application-{profile}.yml files
        for pattern in ["application-*.yml", "application-*.yaml", "application-*.properties"]:
            for f in self._find_files(pattern):
                parts = f.stem.split("-", 1)
                if len(parts) > 1:
                    profiles_found.add(parts[1])
        
        # From @Profile annotations
        for java_file in self._find_files("*.java"):
            content = self._read_file_content(java_file)
            for match in self.PROFILE_PATTERN.finditer(content):
                profiles_found.add(match.group(1))
        
        # Create profile facts
        for profile in profiles_found:
            profile_fact = RawInfraFact(
                name=f"profile-{profile}",
                type="spring_profile",
                category="configuration",
                metadata={"profile_name": profile}
            )
            
            profile_fact.tags.append(f"profile:{profile}")
            
            self.output.add_fact(profile_fact)
            logger.info(f"[SpringConfigCollector] Found profile: {profile}")
