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

from .module_collector import AngularModuleCollector
from .component_collector import AngularComponentCollector
from .routing_collector import AngularRoutingCollector
from .service_collector import AngularServiceCollector
from .state_collector import AngularStateCollector
from .openapi_collector import OpenAPICollector

__all__ = [
    "AngularModuleCollector",
    "AngularComponentCollector",
    "AngularRoutingCollector",
    "AngularServiceCollector",
    "AngularStateCollector",
    "OpenAPICollector",
]
