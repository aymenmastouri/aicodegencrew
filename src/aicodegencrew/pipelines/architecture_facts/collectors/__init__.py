"""
Architecture Facts Collectors

Modular collector architecture where each collector extracts ONE dimension.
No collector thinks. No collector summarizes. All deliver structured facts.

Core Collectors (always needed):
    SystemCollector         -> system.json
    ContainerCollector      -> containers.json
    ComponentCollector      -> components.json (aggregates from specialists)
    InterfaceCollector      -> interfaces.json (aggregates from specialists)
    DataModelCollector      -> data_model.json
    RuntimeCollector        -> runtime.json
    InfrastructureCollector -> infrastructure.json
    EvidenceCollector       -> evidence_map.json
    DependencyCollector     -> dependencies info

Spring Specialists:
    SpringRestCollector
    SpringServiceCollector
    SpringRepositoryCollector
    SpringConfigCollector
    SpringSecurityCollector

Angular Specialists:
    AngularModuleCollector
    AngularComponentCollector
    AngularRoutingCollector
    AngularServiceCollector
    AngularStateCollector

Database Specialists:
    OracleTableCollector
    OracleSchemaCollector
    OracleViewCollector
    OracleProcedureCollector
    MigrationCollector
"""

# Base - import with error handling for incremental development
# Angular Specialists
from .angular import (
    AngularComponentCollector,
    AngularModuleCollector,
    AngularRoutingCollector,
    AngularServiceCollector,
    AngularStateCollector,
)
from .build_system_collector import BuildSystemCollector
from .base import (
    CollectorOutput,
    DimensionCollector,
    RawComponent,
    RawContainer,
    RawEntity,
    RawEvidence,
    RawFact,
    RawInfraFact,
    RawInterface,
    RawRuntimeFact,
    RelationHint,
)
from .component_collector import ComponentCollector
from .container_collector import ContainerCollector
from .data_model_collector import DataModelCollector

# Database Specialists
from .database import (
    MigrationCollector,
    OracleProcedureCollector,
    OracleSchemaCollector,
    OracleTableCollector,
    OracleViewCollector,
)
from .dependency_collector import DependencyCollector
from .evidence_collector import EvidenceCollector

# Adapter
from .fact_adapter import DimensionResultsAdapter, FactAdapter
from .infrastructure_collector import InfrastructureCollector
from .interface_collector import InterfaceCollector

# Orchestrator
from .orchestrator import CollectorOrchestrator, DimensionResults
from .runtime_collector import RuntimeCollector

# Spring Specialists
from .spring import (
    SpringConfigCollector,
    SpringRepositoryCollector,
    SpringRestCollector,
    SpringSecurityCollector,
    SpringServiceCollector,
)

# Core Collectors
from .system_collector import SystemCollector
from .techstack_version_collector import TechStackVersionCollector

# Cross-cutting Collectors
from .workflow_collector import WorkflowCollector

__all__ = [
    "AngularComponentCollector",
    # Angular
    "AngularModuleCollector",
    "BuildSystemCollector",
    "AngularRoutingCollector",
    "AngularServiceCollector",
    "AngularStateCollector",
    # Orchestrator
    "CollectorOrchestrator",
    "CollectorOutput",
    "ComponentCollector",
    "ContainerCollector",
    "DataModelCollector",
    "DependencyCollector",
    # Base
    "DimensionCollector",
    "DimensionResults",
    "DimensionResultsAdapter",
    "EvidenceCollector",
    # Adapter
    "FactAdapter",
    "InfrastructureCollector",
    "InterfaceCollector",
    "MigrationCollector",
    "OracleProcedureCollector",
    "OracleSchemaCollector",
    # Database
    "OracleTableCollector",
    "OracleViewCollector",
    "RawComponent",
    "RawContainer",
    "RawEntity",
    "RawEvidence",
    "RawFact",
    "RawInfraFact",
    "RawInterface",
    "RawRuntimeFact",
    "RelationHint",
    "RuntimeCollector",
    "SpringConfigCollector",
    "SpringRepositoryCollector",
    # Spring
    "SpringRestCollector",
    "SpringSecurityCollector",
    "SpringServiceCollector",
    # Core
    "SystemCollector",
    "TechStackVersionCollector",
    # Cross-cutting
    "WorkflowCollector",
]
