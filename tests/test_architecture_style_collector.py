"""Tests for architecture style and design pattern detection.

Tests detection of:
- Architecture Styles (Microservices, Monolith, Layered, Hexagonal)
- Design Patterns (Repository, Factory, Singleton, Strategy, etc.)
- Module structure analysis
"""

import pytest
from pathlib import Path


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    return tmp_path


def test_layered_architecture_detection(temp_project):
    """Test detection of layered architecture (Controller -> Service -> Repository)."""
    # Create layered structure
    controller = temp_project / "src" / "main" / "java" / "com" / "app" / "controller"
    service = temp_project / "src" / "main" / "java" / "com" / "app" / "service"
    repository = temp_project / "src" / "main" / "java" / "com" / "app" / "repository"
    
    controller.mkdir(parents=True)
    service.mkdir(parents=True)
    repository.mkdir(parents=True)
    
    (controller / "UserController.java").write_text("""
@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;
    
    @Autowired
    public UserController(UserService userService) {
        this.userService = userService;
    }
}
""")
    
    (service / "UserService.java").write_text("""
@Service
public class UserService {
    private final UserRepository userRepository;
    
    @Autowired
    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
}
""")
    
    (repository / "UserRepository.java").write_text("""
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect layered architecture style
    style_components = [c for c in components if c.stereotype == "architecture_style"]
    assert len(style_components) >= 1
    assert any("layered" in c.name.lower() for c in style_components)


def test_repository_pattern_detection(temp_project):
    """Test detection of Repository design pattern."""
    repo_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "repository"
    repo_dir.mkdir(parents=True)
    
    (repo_dir / "OrderRepository.java").write_text("""
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByCustomerId(Long customerId);
    Optional<Order> findByOrderNumber(String orderNumber);
}
""")
    
    (repo_dir / "ProductRepository.java").write_text("""
@Repository
public interface ProductRepository extends CrudRepository<Product, Long> {
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect repository pattern
    pattern_components = [c for c in components if c.stereotype == "design_pattern"]
    assert any("repository" in c.name.lower() for c in pattern_components)


def test_factory_pattern_detection(temp_project):
    """Test detection of Factory design pattern."""
    factory_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "factory"
    factory_dir.mkdir(parents=True)
    
    (factory_dir / "NotificationFactory.java").write_text("""
@Component
public class NotificationFactory {
    public Notification createNotification(NotificationType type) {
        switch (type) {
            case EMAIL:
                return new EmailNotification();
            case SMS:
                return new SmsNotification();
            case PUSH:
                return new PushNotification();
            default:
                throw new IllegalArgumentException("Unknown type: " + type);
        }
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect factory pattern
    pattern_components = [c for c in components if c.stereotype == "design_pattern"]
    assert any("factory" in c.name.lower() for c in pattern_components)


def test_strategy_pattern_detection(temp_project):
    """Test detection of Strategy design pattern."""
    strategy_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "strategy"
    strategy_dir.mkdir(parents=True)
    
    (strategy_dir / "PaymentStrategy.java").write_text("""
public interface PaymentStrategy {
    void pay(BigDecimal amount);
}
""")
    
    (strategy_dir / "CreditCardPayment.java").write_text("""
@Component
public class CreditCardPayment implements PaymentStrategy {
    @Override
    public void pay(BigDecimal amount) {
        // Credit card payment logic
    }
}
""")
    
    (strategy_dir / "PayPalPayment.java").write_text("""
@Component
public class PayPalPayment implements PaymentStrategy {
    @Override
    public void pay(BigDecimal amount) {
        // PayPal payment logic
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect strategy pattern
    pattern_components = [c for c in components if c.stereotype == "design_pattern"]
    assert any("strategy" in c.name.lower() for c in pattern_components)


def test_singleton_pattern_detection(temp_project):
    """Test detection of Singleton design pattern."""
    util_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "util"
    util_dir.mkdir(parents=True)
    
    (util_dir / "ConfigurationManager.java").write_text("""
public class ConfigurationManager {
    private static ConfigurationManager instance;
    
    private ConfigurationManager() {}
    
    public static synchronized ConfigurationManager getInstance() {
        if (instance == null) {
            instance = new ConfigurationManager();
        }
        return instance;
    }
}
""")
    
    (util_dir / "CacheManager.java").write_text("""
public class CacheManager {
    private static CacheManager instance;
    
    private CacheManager() {}
    
    public static CacheManager getInstance() {
        if (instance == null) {
            instance = new CacheManager();
        }
        return instance;
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect singleton pattern (needs 2+ occurrences)
    pattern_components = [c for c in components if c.stereotype == "design_pattern"]
    assert any("singleton" in c.name.lower() for c in pattern_components)


def test_microservices_detection(temp_project):
    """Test detection of microservices architecture."""
    # Create multiple service modules with their own build files
    for svc in ["user-service", "order-service", "payment-service"]:
        svc_dir = temp_project / svc
        svc_dir.mkdir(parents=True)
        (svc_dir / "pom.xml").write_text(f"""
<project>
    <artifactId>{svc}</artifactId>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
        </dependency>
    </dependencies>
</project>
""")
        src = svc_dir / "src" / "main" / "java" / "com" / "app"
        src.mkdir(parents=True)
        (src / "Application.java").write_text(f"""
@SpringBootApplication
@EnableEurekaClient
public class {svc.replace('-', '').title()}Application {{
    public static void main(String[] args) {{
        SpringApplication.run({svc.replace('-', '').title()}Application.class, args);
    }}
}}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect microservices architecture
    style_components = [c for c in components if c.stereotype == "architecture_style"]
    assert any("microservice" in c.name.lower() for c in style_components)


def test_monolith_detection(temp_project):
    """Test detection of monolithic architecture."""
    # Single application with multiple modules in same codebase
    src = temp_project / "src" / "main" / "java" / "com" / "app"
    
    for module in ["user", "order", "payment", "inventory", "notification"]:
        module_dir = src / "module" / module
        module_dir.mkdir(parents=True)
        (module_dir / f"{module.title()}Service.java").write_text(f"""
@Service
public class {module.title()}Service {{
}}
""")
    
    (temp_project / "pom.xml").write_text("""
<project>
    <artifactId>monolith-app</artifactId>
    <packaging>war</packaging>
</project>
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect monolithic architecture (single deployable with many modules)
    style_components = [c for c in components if c.stereotype == "architecture_style"]
    assert any("monolith" in c.name.lower() or "modular" in c.name.lower() for c in style_components)


def test_hexagonal_architecture_detection(temp_project):
    """Test detection of hexagonal/ports-and-adapters architecture."""
    # Create hexagonal structure
    for folder in ["domain", "application", "infrastructure", "adapters"]:
        (temp_project / "src" / "main" / "java" / "com" / "app" / folder).mkdir(parents=True)
    
    ports_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "application" / "ports"
    ports_dir.mkdir(parents=True)
    
    (ports_dir / "UserRepositoryPort.java").write_text("""
public interface UserRepositoryPort {
    User findById(Long id);
    void save(User user);
}
""")
    
    adapters_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "adapters" / "persistence"
    adapters_dir.mkdir(parents=True)
    
    (adapters_dir / "UserRepositoryAdapter.java").write_text("""
@Component
public class UserRepositoryAdapter implements UserRepositoryPort {
    private final JpaUserRepository jpaRepository;
    
    @Override
    public User findById(Long id) {
        return jpaRepository.findById(id).orElse(null);
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect hexagonal/ports-adapters pattern
    style_components = [c for c in components if c.stereotype == "architecture_style"]
    pattern_components = [c for c in components if c.stereotype == "design_pattern"]
    
    all_names = [c.name.lower() for c in style_components + pattern_components]
    assert any("hexagonal" in n or "port" in n or "adapter" in n for n in all_names)


def test_builder_pattern_detection(temp_project):
    """Test detection of Builder design pattern."""
    model_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "model"
    model_dir.mkdir(parents=True)
    
    (model_dir / "User.java").write_text("""
@Builder
@Data
public class User {
    private Long id;
    private String name;
    private String email;
}
""")
    
    (model_dir / "OrderBuilder.java").write_text("""
public class OrderBuilder {
    private Long id;
    private List<OrderItem> items;
    
    public OrderBuilder withId(Long id) {
        this.id = id;
        return this;
    }
    
    public OrderBuilder withItems(List<OrderItem> items) {
        this.items = items;
        return this;
    }
    
    public Order build() {
        return new Order(id, items);
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect builder pattern
    pattern_components = [c for c in components if c.stereotype == "design_pattern"]
    assert any("builder" in c.name.lower() for c in pattern_components)


def test_no_false_positives(temp_project):
    """Test that random files don't create false pattern detections."""
    src = temp_project / "src"
    src.mkdir()
    
    (src / "Main.java").write_text("""
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.architecture_style_collector import ArchitectureStyleCollector
    
    collector = ArchitectureStyleCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should not detect patterns in simple hello world
    assert len(components) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
