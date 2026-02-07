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
from .base import (
    DimensionCollector,
    CollectorOutput,
    RawFact,
    RawComponent,
    RawInterface,
    RawContainer,
    RawEntity,
    RawRuntimeFact,
    RawInfraFact,
    RelationHint,
    RawEvidence,
)

# Core Collectors
from .system_collector import SystemCollector
from .container_collector import ContainerCollector
from .component_collector import ComponentCollector
from .interface_collector import InterfaceCollector
from .data_model_collector import DataModelCollector
from .runtime_collector import RuntimeCollector
from .infrastructure_collector import InfrastructureCollector
from .evidence_collector import EvidenceCollector
from .dependency_collector import DependencyCollector

# Spring Specialists
from .spring import (
    SpringRestCollector,
    SpringServiceCollector,
    SpringRepositoryCollector,
    SpringConfigCollector,
    SpringSecurityCollector,
)

# Angular Specialists
from .angular import (
    AngularModuleCollector,
    AngularComponentCollector,
    AngularRoutingCollector,
    AngularServiceCollector,
    AngularStateCollector,
)

# Database Specialists
from .database import (
    OracleTableCollector,
    OracleSchemaCollector,
    OracleViewCollector,
    OracleProcedureCollector,
    MigrationCollector,
)

# Orchestrator
from .orchestrator import CollectorOrchestrator, DimensionResults

# Adapter
from .fact_adapter import FactAdapter, DimensionResultsAdapter

__all__ = [
    # Base
    "DimensionCollector",
    "CollectorOutput",
    "RawFact",
    "RawComponent",
    "RawInterface",
    "RawContainer",
    "RawEntity",
    "RawRuntimeFact",
    "RawInfraFact",
    "RelationHint",
    "RawEvidence",
    # Core
    "SystemCollector",
    "ContainerCollector",
    "ComponentCollector",
    "InterfaceCollector",
    "DataModelCollector",
    "RuntimeCollector",
    "InfrastructureCollector",
    "EvidenceCollector",
    "DependencyCollector",
    # Spring
    "SpringRestCollector",
    "SpringServiceCollector",
    "SpringRepositoryCollector",
    "SpringConfigCollector",
    "SpringSecurityCollector",
    # Angular
    "AngularModuleCollector",
    "AngularComponentCollector",
    "AngularRoutingCollector",
    "AngularServiceCollector",
    "AngularStateCollector",
    # Database
    "OracleTableCollector",
    "OracleSchemaCollector",
    "OracleViewCollector",
    "OracleProcedureCollector",
    "MigrationCollector",
    # Orchestrator
    "CollectorOrchestrator",
    "DimensionResults",
    # Adapter
    "FactAdapter",
    "DimensionResultsAdapter",
]
