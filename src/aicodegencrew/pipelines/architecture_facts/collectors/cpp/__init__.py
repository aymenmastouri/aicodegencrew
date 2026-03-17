"""
C/C++ Specialist Collectors

Each collector extracts ONE specific aspect of C/C++ applications:
- CppComponentCollector: Classes, services, handlers, libraries
- CppInterfaceCollector: Public APIs, gRPC services, extern functions
- CppDependencyCollector: CMake, Conan, and vcpkg dependencies
- CppWorkflowCollector: Enum-based FSMs, switch/case state machines
"""

from .build_system_collector import CppBuildSystemCollector
from .component_collector import CppComponentCollector
from .dependency_collector import CppDependencyCollector
from .interface_collector import CppInterfaceCollector
from .test_collector import CppTestCollector
from .workflow_collector import CppWorkflowCollector

__all__ = [
    "CppBuildSystemCollector",
    "CppComponentCollector",
    "CppDependencyCollector",
    "CppInterfaceCollector",
    "CppTestCollector",
    "CppWorkflowCollector",
]
