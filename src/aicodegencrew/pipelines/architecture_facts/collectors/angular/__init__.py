"""
Angular Specialist Collectors

Each collector extracts ONE specific aspect of Angular applications:
- AngularModuleCollector: NgModules, lazy loading
- AngularComponentCollector: Components, templates
- AngularRoutingCollector: Routes, guards
- AngularServiceCollector: Injectable services, HTTP clients
- AngularStateCollector: NgRx state management
- OpenAPICollector: OpenAPI/Swagger specifications and generated clients
- AngularDependencyCollector: NPM dependencies
- AngularTestCollector: Jasmine, Jest, Playwright spec files
- AngularWorkflowDetailCollector: XState, NgRx effects/reducers, RxJS flows
"""

from .build_system_collector import AngularBuildSystemCollector
from .component_collector import AngularComponentCollector
from .dependency_collector import AngularDependencyCollector
from .error_detail_collector import AngularErrorDetailCollector
from .module_collector import AngularModuleCollector
from .openapi_collector import OpenAPICollector
from .routing_collector import AngularRoutingCollector
from .security_detail_collector import AngularSecurityDetailCollector
from .service_collector import AngularServiceCollector
from .state_collector import AngularStateCollector
from .test_collector import AngularTestCollector
from .validation_detail_collector import AngularValidationDetailCollector
from .workflow_detail_collector import AngularWorkflowDetailCollector

__all__ = [
    "AngularBuildSystemCollector",
    "AngularComponentCollector",
    "AngularDependencyCollector",
    "AngularErrorDetailCollector",
    "AngularModuleCollector",
    "AngularRoutingCollector",
    "AngularSecurityDetailCollector",
    "AngularServiceCollector",
    "AngularStateCollector",
    "AngularTestCollector",
    "AngularValidationDetailCollector",
    "AngularWorkflowDetailCollector",
    "OpenAPICollector",
]
