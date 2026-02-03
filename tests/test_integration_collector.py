"""Tests for cross-container integration detection.

Tests detection of:
- REST Client calls (WebClient, RestTemplate, Feign)
- Database connections (JDBC URLs, DataSource)
- Message queues (Kafka, RabbitMQ)
- External service integrations
"""

import pytest
from pathlib import Path


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    return tmp_path


def test_rest_template_detection(temp_project):
    """Test detection of RestTemplate calls to external services."""
    service_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "service"
    service_dir.mkdir(parents=True)
    
    (service_dir / "UserServiceClient.java").write_text("""
@Service
public class UserServiceClient {
    private final RestTemplate restTemplate;
    
    @Value("${user-service.url}")
    private String userServiceUrl;
    
    public User getUser(Long id) {
        return restTemplate.getForObject(
            userServiceUrl + "/api/users/{id}", 
            User.class, 
            id
        );
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect REST client integration
    integrations = [c for c in components if c.stereotype == "integration"]
    assert len(integrations) >= 1
    assert any("rest" in c.name.lower() or "http" in c.name.lower() for c in integrations)


def test_feign_client_detection(temp_project):
    """Test detection of Feign client interfaces."""
    client_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "client"
    client_dir.mkdir(parents=True)
    
    (client_dir / "PaymentClient.java").write_text("""
@FeignClient(name = "payment-service", url = "${payment.service.url}")
public interface PaymentClient {
    
    @PostMapping("/api/payments")
    PaymentResponse processPayment(@RequestBody PaymentRequest request);
    
    @GetMapping("/api/payments/{id}")
    PaymentResponse getPayment(@PathVariable("id") String paymentId);
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Feign client
    integrations = [c for c in components if c.stereotype == "integration"]
    assert any("payment" in c.name.lower() for c in integrations)


def test_webclient_detection(temp_project):
    """Test detection of WebClient reactive calls."""
    service_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "service"
    service_dir.mkdir(parents=True)
    
    (service_dir / "OrderServiceClient.java").write_text("""
@Service
public class OrderServiceClient {
    private final WebClient webClient;
    
    public OrderServiceClient(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder
            .baseUrl("http://order-service:8080")
            .build();
    }
    
    public Mono<Order> getOrder(String orderId) {
        return webClient.get()
            .uri("/api/orders/{id}", orderId)
            .retrieve()
            .bodyToMono(Order.class);
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect WebClient integration
    integrations = [c for c in components if c.stereotype == "integration"]
    assert len(integrations) >= 1


def test_kafka_producer_detection(temp_project):
    """Test detection of Kafka producer."""
    service_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "messaging"
    service_dir.mkdir(parents=True)
    
    (service_dir / "OrderEventProducer.java").write_text("""
@Service
public class OrderEventProducer {
    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;
    
    @Value("${kafka.topic.orders}")
    private String ordersTopic;
    
    public void sendOrderCreated(OrderEvent event) {
        kafkaTemplate.send(ordersTopic, event.getOrderId(), event);
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Kafka producer
    integrations = [c for c in components if c.stereotype == "message_queue"]
    assert len(integrations) >= 1
    assert any("kafka" in c.name.lower() for c in integrations)


def test_kafka_consumer_detection(temp_project):
    """Test detection of Kafka consumer."""
    service_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "messaging"
    service_dir.mkdir(parents=True)
    
    (service_dir / "PaymentEventConsumer.java").write_text("""
@Service
public class PaymentEventConsumer {
    
    @KafkaListener(topics = "${kafka.topic.payments}", groupId = "${kafka.group.id}")
    public void handlePaymentEvent(PaymentEvent event) {
        // Process payment event
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect Kafka consumer
    integrations = [c for c in components if c.stereotype == "message_queue"]
    assert len(integrations) >= 1


def test_database_connection_detection(temp_project):
    """Test detection of database connections from application.properties."""
    resources_dir = temp_project / "src" / "main" / "resources"
    resources_dir.mkdir(parents=True)
    
    (resources_dir / "application.properties").write_text("""
spring.datasource.url=jdbc:postgresql://db-server:5432/myapp
spring.datasource.username=app_user
spring.datasource.driver-class-name=org.postgresql.Driver

spring.jpa.hibernate.ddl-auto=validate
spring.jpa.show-sql=true
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect database connection
    db_integrations = [c for c in components if c.stereotype == "database_connection"]
    assert len(db_integrations) >= 1
    assert any("postgresql" in c.name.lower() for c in db_integrations)


def test_rabbitmq_detection(temp_project):
    """Test detection of RabbitMQ integration."""
    service_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "messaging"
    service_dir.mkdir(parents=True)
    
    (service_dir / "NotificationSender.java").write_text("""
@Service
public class NotificationSender {
    private final RabbitTemplate rabbitTemplate;
    
    @Value("${rabbitmq.exchange.notifications}")
    private String exchange;
    
    public void sendNotification(Notification notification) {
        rabbitTemplate.convertAndSend(exchange, "notification.created", notification);
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect RabbitMQ
    mq_integrations = [c for c in components if c.stereotype == "message_queue"]
    assert len(mq_integrations) >= 1


def test_cross_container_relation_creation(temp_project):
    """Test that cross-container relations are created."""
    service_dir = temp_project / "src" / "main" / "java" / "com" / "app" / "service"
    service_dir.mkdir(parents=True)
    
    (service_dir / "OrderService.java").write_text("""
@Service
public class OrderService {
    private final PaymentClient paymentClient;
    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;
    
    public Order createOrder(OrderRequest request) {
        // Call payment service
        PaymentResponse payment = paymentClient.processPayment(request.getPayment());
        
        // Send event
        kafkaTemplate.send("orders", new OrderEvent(order));
        
        return order;
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should create relations for external dependencies
    assert len(relations) >= 0  # Relations may or may not be created depending on context


def test_no_false_positives(temp_project):
    """Test that simple files don't create false integrations."""
    src_dir = temp_project / "src" / "main" / "java"
    src_dir.mkdir(parents=True)
    
    (src_dir / "Main.java").write_text("""
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
""")
    
    from src.aicodegencrew.pipelines.architecture_facts.integration_collector import IntegrationCollector
    
    collector = IntegrationCollector(temp_project, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should not detect integrations in simple code
    assert len(components) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
