"""
Spring Specialist Collectors

Each collector extracts ONE specific aspect of Spring applications:
- SpringRestCollector: @RestController, @RequestMapping, HTTP endpoints
- SpringServiceCollector: @Service, interface+impl mappings
- SpringRepositoryCollector: JpaRepository, custom queries
- SpringConfigCollector: @Configuration, application.yml, profiles
"""

from .config_collector import SpringConfigCollector
from .repository_collector import SpringRepositoryCollector
from .rest_collector import SpringRestCollector
from .security_collector import SpringSecurityCollector
from .service_collector import SpringServiceCollector

__all__ = [
    "SpringConfigCollector",
    "SpringRepositoryCollector",
    "SpringRestCollector",
    "SpringSecurityCollector",
    "SpringServiceCollector",
]
