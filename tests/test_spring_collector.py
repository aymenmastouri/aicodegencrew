"""Tests for SpringCollector REST endpoint detection.

Tests cover all known bug patterns:
1. Multi-line annotations
2. Array paths: @GetMapping({"/path1", "/path2"})
3. All RequestMapping variants (@Get, @Post, @Put, @Delete, @Patch)
4. Class-level + method-level path combination
5. Annotations with additional attributes (produces, consumes, etc.)
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


def test_single_line_get_mapping(temp_java_project):
    """Test basic single-line @GetMapping detection."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "SimpleController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class SimpleController {
    
    @GetMapping("/api/users")
    public String getUsers() {
        return "users";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 1
    assert components[0].name == "SimpleController"
    assert components[0].stereotype == "controller"
    
    assert len(interfaces) == 1
    assert interfaces[0].path == "/api/users"
    assert interfaces[0].method == "GET"
    assert interfaces[0].type == "REST"


def test_multi_line_get_mapping(temp_java_project):
    """Test multi-line @GetMapping with attributes."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "MultiLineController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class MultiLineController {
    
    @GetMapping(
        value = "/api/products",
        produces = {"application/json"}
    )
    public String getProducts() {
        return "products";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 1
    assert interfaces[0].path == "/api/products"
    assert interfaces[0].method == "GET"


def test_array_paths_single_annotation(temp_java_project):
    """Test @GetMapping with array of paths."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "ArrayPathController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class ArrayPathController {
    
    @GetMapping(value = {"/web", "/web/", "/web/index.html"})
    public String getIndex() {
        return "index";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect 3 separate endpoints
    assert len(interfaces) == 3
    paths = [iface.path for iface in interfaces]
    assert "/web" in paths
    assert "/web/" in paths
    assert "/web/index.html" in paths


def test_array_paths_multi_line(temp_java_project):
    """Test multi-line @GetMapping with array of paths."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "MultiLineArrayController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class MultiLineArrayController {
    
    @GetMapping(
        value = {
            "/api/v1/resource",
            "/api/v2/resource"
        },
        produces = {"application/json"}
    )
    public String getResource() {
        return "resource";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 2
    paths = [iface.path for iface in interfaces]
    assert "/api/v1/resource" in paths
    assert "/api/v2/resource" in paths


def test_class_level_request_mapping(temp_java_project):
    """Test class-level @RequestMapping combined with method-level."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "BasePathController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class BasePathController {
    
    @GetMapping("/users")
    public String getUsers() {
        return "users";
    }
    
    @PostMapping("/users")
    public String createUser() {
        return "created";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 2
    
    # Check full paths include base path
    paths = [iface.path for iface in interfaces]
    assert "/api/v1/users" in paths
    
    # Check methods
    methods = {iface.path: iface.method for iface in interfaces}
    assert methods["/api/v1/users"] in ["GET", "POST"]


def test_all_http_methods(temp_java_project):
    """Test all HTTP method mappings (@Get, @Post, @Put, @Delete, @Patch)."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "AllMethodsController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/resources")
public class AllMethodsController {
    
    @GetMapping("/{id}")
    public String get() { return "get"; }
    
    @PostMapping
    public String create() { return "create"; }
    
    @PutMapping("/{id}")
    public String update() { return "update"; }
    
    @DeleteMapping("/{id}")
    public String delete() { return "delete"; }
    
    @PatchMapping("/{id}")
    public String patch() { return "patch"; }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 5
    
    methods = [iface.method for iface in interfaces]
    assert "GET" in methods
    assert "POST" in methods
    assert "PUT" in methods
    assert "DELETE" in methods
    assert "PATCH" in methods


def test_request_mapping_with_method_attribute(temp_java_project):
    """Test @RequestMapping with method attribute."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "RequestMappingController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class RequestMappingController {
    
    @RequestMapping(value = "/api/data", method = RequestMethod.GET)
    public String getData() {
        return "data";
    }
    
    @RequestMapping(
        value = "/api/data",
        method = RequestMethod.POST,
        produces = "application/json"
    )
    public String postData() {
        return "posted";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect both endpoints
    assert len(interfaces) >= 2
    paths = [iface.path for iface in interfaces]
    assert "/api/data" in paths


def test_shorthand_annotation_without_value(temp_java_project):
    """Test @GetMapping("/path") without explicit 'value=' parameter."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "ShorthandController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class ShorthandController {
    
    @GetMapping("/api/short")
    public String getShort() {
        return "short";
    }
    
    @PostMapping("/api/short")
    public String postShort() {
        return "posted";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 2
    paths = [iface.path for iface in interfaces]
    assert "/api/short" in paths


def test_produces_consumes_attributes(temp_java_project):
    """Test annotations with produces and consumes attributes."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "MediaTypeController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class MediaTypeController {
    
    @GetMapping(
        value = "/api/json",
        produces = {"application/json"},
        consumes = {"application/json"}
    )
    public String getJson() {
        return "json";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 1
    assert interfaces[0].path == "/api/json"


def test_params_and_headers_attributes(temp_java_project):
    """Test annotations with params and headers attributes."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "ParameterController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class ParameterController {
    
    @GetMapping(
        value = "/api/search",
        params = {"q", "page"},
        headers = "X-API-Version=1"
    )
    public String search() {
        return "results";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(interfaces) == 1
    assert interfaces[0].path == "/api/search"


def test_complex_real_world_example(temp_java_project):
    """Test real-world complex controller from C:\\uvz."""
    tmp_path, java_root = temp_java_project
    
    controller_file = java_root / "StaticContentController.java"
    controller_file.write_text("""
package com.example;

import org.springframework.web.bind.annotation.*;
import org.springframework.stereotype.Controller;

@Controller
public class StaticContentController {
    
    @GetMapping(value = "/web/uvz/", produces = {"text/html;charset=UTF-8"})
    public String getIndexHTML() {
        return "index";
    }
    
    @GetMapping(value = {"/web", "/web/", "/web/index.html"}, produces = {"text/html;charset=UTF-8"})
    public String redirectToOriginalEntryPoint() {
        return "redirect";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # Should detect controller component
    assert len(components) == 1
    assert components[0].stereotype == "controller"
    
    # Should detect 4 endpoints total (1 from first + 3 from array)
    assert len(interfaces) == 4
    paths = [iface.path for iface in interfaces]
    assert "/web/uvz/" in paths
    assert "/web" in paths
    assert "/web/" in paths
    assert "/web/index.html" in paths


def test_no_false_positives_for_services(temp_java_project):
    """Test that @Service classes don't generate REST interfaces."""
    tmp_path, java_root = temp_java_project
    
    service_file = java_root / "UserService.java"
    service_file.write_text("""
package com.example;

import org.springframework.stereotype.Service;

@Service
public class UserService {
    
    public String getUsers() {
        return "users";
    }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    assert len(components) == 1
    assert components[0].stereotype == "service"
    
    # Services should NOT generate REST interfaces
    assert len(interfaces) == 0


def test_multiple_controllers(temp_java_project):
    """Test scanning multiple controller files."""
    tmp_path, java_root = temp_java_project
    
    # Controller 1
    (java_root / "UserController.java").write_text("""
package com.example;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    @GetMapping
    public String list() { return "users"; }
    
    @PostMapping
    public String create() { return "created"; }
}
""")
    
    # Controller 2
    (java_root / "ProductController.java").write_text("""
package com.example;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/products")
public class ProductController {
    @GetMapping
    public String list() { return "products"; }
    
    @DeleteMapping("/{id}")
    public String delete() { return "deleted"; }
}
""")
    
    collector = SpringCollector(tmp_path, "backend")
    components, interfaces, relations, evidence = collector.collect()
    
    # 2 controllers
    assert len(components) == 2
    controller_names = [c.name for c in components]
    assert "UserController" in controller_names
    assert "ProductController" in controller_names
    
    # 4 endpoints total (2 from each controller)
    assert len(interfaces) == 4
    paths = [iface.path for iface in interfaces]
    assert "/api/users" in paths
    assert "/api/products" in paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
