"""
Spring Specialist Collectors

Each collector extracts ONE specific aspect of Spring applications:
- SpringRestCollector: @RestController, @RequestMapping, HTTP endpoints
- SpringServiceCollector: @Service, interface+impl mappings
- SpringRepositoryCollector: JpaRepository, custom queries
- SpringConfigCollector: @Configuration, application.yml, profiles
"""

from .rest_collector import SpringRestCollector
from .service_collector import SpringServiceCollector
from .repository_collector import SpringRepositoryCollector
from .config_collector import SpringConfigCollector
from .security_collector import SpringSecurityCollector

__all__ = [
    "SpringRestCollector",
    "SpringServiceCollector", 
    "SpringRepositoryCollector",
    "SpringConfigCollector",
    "SpringSecurityCollector",
]
