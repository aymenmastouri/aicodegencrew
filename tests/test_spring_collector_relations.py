"""Tests for SpringCollector dependency relation detection.

Tests dependency injection patterns:
- Constructor injection (@Autowired constructor)
- Field injection (private final fields)
- Relations between Controller -> Service -> Repository
"""

import pytest
from pathlib import Path
from src.aicodegencrew.pipelines.architecture_facts.spring_collector import SpringCollector


@pytest.fixture
def temp_java_project(tmp_path):
    """Create a temporary Java project structure."""
    java_root = tmp_path / "src" / "main" / "java" / "com" / "example"
    java_root.mkdir(parents=True)
    return tmp_path, java_root


def test_constructor_injection_single_dependency(temp_java_project):
    """Test constructor injection with @Autowired."""
    tmp_path, java_root = temp_java_project
    
    # Service
    (java_root / "UserService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    public String getUser() { return "user"; }
}
""")
    
    # Controller with constructor injection
    (java_root / "UserController.java").write_text("""
package com.example;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;

@RestController
public class UserController {
    
    private final UserService userService;
    
    @Autowired
    public UserController(UserService userService) {
        this.userService = userService;
    }
    
    @GetMapping("/users")
    public String list() {
        return userService.getUser();
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect both components
    assert len(components) == 2
    component_names = [c.name for c in components]
    assert "UserService" in component_names
    assert "UserController" in component_names
    
    # Should detect relation: Controller -> Service
    assert len(relations) >= 1
    relation = relations[0]
    assert "user_service" in relation.to_id.lower()
    assert "user_controller" in relation.from_id.lower()
    assert relation.type == "uses"


def test_constructor_injection_multiple_dependencies(temp_java_project):
    """Test constructor injection with multiple dependencies."""
    tmp_path, java_root = temp_java_project
    
    # Repository
    (java_root / "UserRepository.java").write_text("""
package com.example;
import org.springframework.stereotype.Repository;

@Repository
public class UserRepository {
    public String find() { return "data"; }
}
""")
    
    # Another service
    (java_root / "EmailService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class EmailService {
    public void send() {}
}
""")
    
    # Service with multiple dependencies
    (java_root / "UserService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    
    private final UserRepository userRepository;
    private final EmailService emailService;
    
    public UserService(UserRepository userRepository, EmailService emailService) {
        this.userRepository = userRepository;
        this.emailService = emailService;
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 3
    
    # Should detect 2 relations from UserService
    assert len(relations) >= 2
    
    # Check relations
    from_service_relations = [r for r in relations if "user_service" in r.from_id.lower()]
    assert len(from_service_relations) == 2
    
    to_components = [r.to_id for r in from_service_relations]
    assert any("repository" in to_id.lower() for to_id in to_components)
    assert any("email" in to_id.lower() for to_id in to_components)


def test_field_injection_pattern(temp_java_project):
    """Test field injection with @Autowired."""
    tmp_path, java_root = temp_java_project
    
    (java_root / "DataService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class DataService {
}
""")
    
    (java_root / "ProcessorService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

@Service
public class ProcessorService {
    
    @Autowired
    private DataService dataService;
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 2
    assert len(relations) >= 1
    
    relation = relations[0]
    assert "processor" in relation.from_id.lower()
    assert "data" in relation.to_id.lower()


def test_layered_architecture_pattern(temp_java_project):
    """Test typical layered architecture: Controller -> Service -> Repository."""
    tmp_path, java_root = temp_java_project
    
    # Repository layer
    (java_root / "ProductRepository.java").write_text("""
package com.example;
import org.springframework.stereotype.Repository;

@Repository
public class ProductRepository {
}
""")
    
    # Service layer
    (java_root / "ProductService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class ProductService {
    
    private final ProductRepository repository;
    
    public ProductService(ProductRepository repository) {
        this.repository = repository;
    }
}
""")
    
    # Controller layer
    (java_root / "ProductController.java").write_text("""
package com.example;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/products")
public class ProductController {
    
    private final ProductService productService;
    
    public ProductController(ProductService productService) {
        this.productService = productService;
    }
    
    @GetMapping
    public String list() { return "products"; }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # 3 components in layered architecture
    assert len(components) == 3
    
    # 2 relations: Controller->Service, Service->Repository
    assert len(relations) == 2
    
    # Verify Controller -> Service
    controller_relations = [r for r in relations if "controller" in r.from_id.lower()]
    assert len(controller_relations) == 1
    assert "service" in controller_relations[0].to_id.lower()
    
    # Verify Service -> Repository
    service_relations = [r for r in relations if "service" in r.from_id.lower()]
    assert len(service_relations) == 1
    assert "repository" in service_relations[0].to_id.lower()


def test_no_relations_for_unused_components(temp_java_project):
    """Test that components without dependencies have no relations."""
    tmp_path, java_root = temp_java_project
    
    (java_root / "UtilityService.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class UtilityService {
    public String doSomething() { return "done"; }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 1
    assert len(relations) == 0


def test_real_world_uvz_pattern(temp_java_project):
    """Test actual UVZ pattern: RestController -> Service with @Autowired constructor."""
    tmp_path, java_root = temp_java_project
    
    # Service interface
    (java_root / "ActionService.java").write_text("""
package com.example;

public interface ActionService {
    String create(String type);
}
""")
    
    # Service implementation
    (java_root / "ActionServiceImpl.java").write_text("""
package com.example;
import org.springframework.stereotype.Service;

@Service
public class ActionServiceImpl implements ActionService {
    public String create(String type) {
        return "created";
    }
}
""")
    
    # REST Service interface
    (java_root / "ActionRestService.java").write_text("""
package com.example;
import org.springframework.web.bind.annotation.*;

@RequestMapping("/api/actions")
public interface ActionRestService {
    @PostMapping("/{type}")
    String create(@PathVariable String type);
}
""")
    
    # REST Controller implementation
    (java_root / "ActionRestServiceImpl.java").write_text("""
package com.example;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.beans.factory.annotation.Autowired;

@RestController
public class ActionRestServiceImpl implements ActionRestService {
    
    private final ActionService actionService;
    
    @Autowired
    public ActionRestServiceImpl(ActionService actionService) {
        this.actionService = actionService;
    }
    
    @Override
    public String create(String type) {
        return actionService.create(type);
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect both components
    assert len(components) == 2
    component_names = [c.name for c in components]
    assert "ActionRestServiceImpl" in component_names
    assert "ActionServiceImpl" in component_names
    
    # Should detect relation: RestController -> Service
    assert len(relations) >= 1
    
    # Find the relation from RestController to Service
    rest_to_service = [r for r in relations if "rest" in r.from_id.lower() and "action_service" in r.to_id.lower()]
    assert len(rest_to_service) >= 1
    assert rest_to_service[0].type == "uses"
    
    # Should also detect REST endpoint from interface
    assert len(interfaces) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
