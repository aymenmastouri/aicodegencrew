"""
Spring Specialist Collectors

Each collector extracts ONE specific aspect of Spring applications:
- SpringRestCollector: @RestController, @RequestMapping, HTTP endpoints
- SpringServiceCollector: @Service, interface+impl mappings
- SpringRepositoryCollector: JpaRepository, custom queries
- SpringConfigCollector: @Configuration, application.yml, profiles
- SpringDependencyCollector: Maven and Gradle dependencies
- SpringDataModelCollector: JPA entities, relationships
- SpringTestCollector: JUnit, SpringBootTest, test classes
- SpringWorkflowCollector: State machines, Camunda/Flowable, orchestration
"""

from .build_system_collector import SpringBuildSystemCollector
from .communication_collector import SpringCommunicationCollector
from .config_collector import SpringConfigCollector
from .configuration_collector import SpringConfigurationCollector
from .data_model_collector import SpringDataModelCollector
from .dependency_collector import SpringDependencyCollector
from .error_collector import SpringErrorCollector
from .interface_detail_collector import SpringInterfaceDetailCollector
from .logging_collector import SpringLoggingCollector
from .repository_collector import SpringRepositoryCollector
from .rest_collector import SpringRestCollector
from .runtime_collector import SpringRuntimeCollector
from .security_collector import SpringSecurityCollector
from .security_detail_collector import SpringSecurityDetailCollector
from .service_collector import SpringServiceCollector
from .test_collector import SpringTestCollector
from .validation_collector import SpringValidationCollector
from .workflow_collector import SpringWorkflowCollector

__all__ = [
    "SpringBuildSystemCollector",
    "SpringCommunicationCollector",
    "SpringConfigCollector",
    "SpringConfigurationCollector",
    "SpringDataModelCollector",
    "SpringDependencyCollector",
    "SpringErrorCollector",
    "SpringInterfaceDetailCollector",
    "SpringLoggingCollector",
    "SpringRepositoryCollector",
    "SpringRestCollector",
    "SpringRuntimeCollector",
    "SpringSecurityCollector",
    "SpringSecurityDetailCollector",
    "SpringServiceCollector",
    "SpringTestCollector",
    "SpringValidationCollector",
    "SpringWorkflowCollector",
]
