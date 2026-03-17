"""Ecosystem Strategy Pattern — One module per language ecosystem.

Provides EcosystemRegistry for detecting active ecosystems and routing
symbol extraction, container detection, version collection, and
component collection to the appropriate ecosystem module.
"""

from .base import CollectorContext, EcosystemDefinition, MarkerFile
from .c_cpp import CCppEcosystem
from .ecosystem_config import load_ecosystem_config, toggle_ecosystem, update_priority
from .java_jvm import JavaJvmEcosystem
from .javascript_typescript import JavaScriptTypeScriptEcosystem
from .python_ecosystem import PythonEcosystem
from .registry import EcosystemRegistry

__all__ = [
    "EcosystemDefinition",
    "EcosystemRegistry",
    "MarkerFile",
    "CollectorContext",
    "JavaJvmEcosystem",
    "JavaScriptTypeScriptEcosystem",
    "PythonEcosystem",
    "CCppEcosystem",
    "load_ecosystem_config",
    "toggle_ecosystem",
    "update_priority",
]
