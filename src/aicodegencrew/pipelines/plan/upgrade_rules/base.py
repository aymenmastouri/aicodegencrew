"""
Declarative types for framework upgrade rules.

Pure dataclasses with no logic -- rules are data, not code.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class UpgradeSeverity(StrEnum):
    BREAKING = "breaking"
    DEPRECATED = "deprecated"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class UpgradeCategory(StrEnum):
    API_CHANGE = "api_change"
    MIGRATION = "migration"
    DEPENDENCY = "dependency"
    BUILD_CONFIG = "build_config"
    TEST_RUNNER = "test_runner"
    SYNTAX = "syntax"


@dataclass
class CodePattern:
    """A regex pattern to detect in source files."""

    name: str
    file_glob: str  # e.g., "*.component.ts", "angular.json"
    regex: str
    description: str = ""


class ConfigOperation(StrEnum):
    SET = "set"  # Set or overwrite a value
    DELETE = "delete"  # Delete a key
    RENAME_KEY = "rename_key"  # Rename a key


@dataclass
class ConfigChange:
    """A deterministic config file change (no LLM needed)."""

    file_glob: str  # e.g., "package.json", "angular.json"
    operation: ConfigOperation
    json_path: str  # Dot-separated path, e.g. "devDependencies.typescript"
    value: str | dict | list | None = None
    description: str = ""
    condition_regex: str = ""  # Only apply when current value matches this regex


@dataclass
class UpgradeRule:
    """A single upgrade rule (declarative)."""

    id: str
    title: str
    description: str
    severity: UpgradeSeverity
    category: UpgradeCategory
    from_version: str
    to_version: str
    detection_patterns: list[CodePattern] = field(default_factory=list)
    migration_steps: list[str] = field(default_factory=list)
    schematic: str | None = None
    affected_stereotypes: list[str] = field(default_factory=list)
    reference_url: str | None = None
    effort_per_occurrence: int = 5  # minutes
    config_changes: list[ConfigChange] = field(default_factory=list)


@dataclass
class UpgradeImpact:
    """Result of scanning a rule against the codebase."""

    rule: UpgradeRule
    occurrences: int = 0
    affected_files: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    estimated_effort_minutes: int = 0
    details: dict = field(default_factory=dict)


@dataclass
class UpgradeRuleSet:
    """A set of rules for one version upgrade."""

    framework: str
    from_version: str
    to_version: str
    rules: list[UpgradeRule] = field(default_factory=list)
    required_dependencies: dict[str, str] = field(default_factory=dict)
    verification_commands: list[str] = field(default_factory=list)
