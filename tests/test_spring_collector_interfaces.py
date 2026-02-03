"""Tests for SpringCollector interface-based REST endpoint detection.

Spring allows defining REST mappings in interfaces, and implementation classes
marked with @RestController can implement these interfaces.
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


def test_interface_with_rest_mappings(temp_java_project):
    """Test REST endpoint detection from interface definitions."""
    tmp_path, java_root = temp_java_project
    
    # Create interface with REST mappings
    (java_root / "UserRestService.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RequestMapping("/api/users")
public interface UserRestService {
    
    @GetMapping("/{id}")
    String getUser(@PathVariable Long id);
    
    @PostMapping
    String createUser();
}
""")
    
    # Create implementation
    (java_root / "UserRestServiceImpl.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class UserRestServiceImpl implements UserRestService {
    
    @Override
    public String getUser(Long id) {
        return "user";
    }
    
    @Override
    public String createUser() {
        return "created";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect the controller component
    assert len(components) == 1
    assert components[0].name == "UserRestServiceImpl"
    assert components[0].stereotype == "controller"
    
    # Should detect REST endpoints from interface
    assert len(interfaces) == 2
    paths = [iface.path for iface in interfaces]
    assert "/api/users/{id}" in paths
    assert "/api/users" in paths
    
    methods = [iface.method for iface in interfaces]
    assert "GET" in methods
    assert "POST" in methods


def test_multiple_interfaces_same_implementation(temp_java_project):
    """Test controller implementing multiple interfaces."""
    tmp_path, java_root = temp_java_project
    
    # Interface 1
    (java_root / "UserService.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RequestMapping("/api/users")
public interface UserService {
    @GetMapping
    String list();
}
""")
    
    # Interface 2
    (java_root / "AdminService.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RequestMapping("/api/admin")
public interface AdminService {
    @GetMapping("/stats")
    String getStats();
}
""")
    
    # Implementation
    (java_root / "CombinedServiceImpl.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class CombinedServiceImpl implements UserService, AdminService {
    public String list() { return "users"; }
    public String getStats() { return "stats"; }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 1
    
    # Should detect endpoints from both interfaces
    assert len(interfaces) == 2
    paths = [iface.path for iface in interfaces]
    assert "/api/users" in paths
    assert "/api/admin/stats" in paths


def test_interface_without_implementation_no_endpoints(temp_java_project):
    """Test that interface without @RestController implementation doesn't create endpoints."""
    tmp_path, java_root = temp_java_project
    
    # Interface with REST mappings
    (java_root / "UserService.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RequestMapping("/api/users")
public interface UserService {
    @GetMapping
    String list();
}
""")
    
    # Implementation WITHOUT @RestController
    (java_root / "UserServiceImpl.java").write_text("""
package com.example;

import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl implements UserService {
    public String list() { return "users"; }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect service component
    assert len(components) == 1
    assert components[0].stereotype == "service"
    
    # Should NOT create REST endpoints (no @RestController)
    assert len(interfaces) == 0


def test_real_world_uvz_pattern(temp_java_project):
    """Test the actual UVZ pattern: interface with annotations, RestController implementation."""
    tmp_path, java_root = temp_java_project
    
    # Real UVZ interface pattern
    (java_root / "ActionRestService.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

@RequestMapping(value = "/uvz/v1")
public interface ActionRestService {
    
    @PostMapping(value = "/action/{type}")
    ResponseEntity<String> create(@PathVariable String type);
    
    @GetMapping(value = "/action/{id}")
    void getStatus(@PathVariable long id);
}
""")
    
    # Implementation
    (java_root / "ActionRestServiceImpl.java").write_text("""
package com.example;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;

@RestController
public class ActionRestServiceImpl implements ActionRestService {
    
    @Override
    public ResponseEntity<String> create(String type) {
        return ResponseEntity.ok("created");
    }
    
    @Override
    public void getStatus(long id) {
        // implementation
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 1
    assert components[0].name == "ActionRestServiceImpl"
    
    # Should detect both endpoints from interface
    assert len(interfaces) == 2
    paths = [iface.path for iface in interfaces]
    assert "/uvz/v1/action/{type}" in paths
    assert "/uvz/v1/action/{id}" in paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
