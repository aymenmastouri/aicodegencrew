"""
Angular Specialist Collectors

Each collector extracts ONE specific aspect of Angular applications:
- AngularModuleCollector: NgModules, lazy loading
- AngularComponentCollector: Components, templates
- AngularRoutingCollector: Routes, guards
- AngularServiceCollector: Injectable services, HTTP clients
- AngularStateCollector: NgRx state management
- OpenAPICollector: OpenAPI/Swagger specifications and generated clients
"""

from .component_collector import AngularComponentCollector
from .module_collector import AngularModuleCollector
from .openapi_collector import OpenAPICollector
from .routing_collector import AngularRoutingCollector
from .service_collector import AngularServiceCollector
from .state_collector import AngularStateCollector

__all__ = [
    "AngularComponentCollector",
    "AngularModuleCollector",
    "AngularRoutingCollector",
    "AngularServiceCollector",
    "AngularStateCollector",
    "OpenAPICollector",
]
