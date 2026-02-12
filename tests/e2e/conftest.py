"""
Pytest fixtures and utilities for E2E tests.

This module provides reusable fixtures for:
- Temporary workspaces with automatic cleanup
- Sample projects for testing
- Pre-configured orchestrator instances
- Test data and expected outputs
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Create an isolated temporary workspace for each test.

    Automatically cleaned up after test completion.

    Returns:
        Path: Temporary directory path
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)

    # Create standard directory structure
    (workspace / "knowledge").mkdir()
    (workspace / "knowledge" / "architecture").mkdir()
    (workspace / "knowledge" / "architecture" / "c4").mkdir()
    (workspace / "knowledge" / "architecture" / "arc42").mkdir()
    (workspace / "knowledge" / "architecture" / "quality").mkdir()
    (workspace / "logs").mkdir()

    yield workspace

    # Cleanup (comment out for debugging)
    if workspace.exists():
        shutil.rmtree(workspace)


@pytest.fixture
def sample_project(temp_workspace):
    """
    Create a minimal Spring Boot + Angular sample project for testing.

    Project structure:
    - backend/ (Java Spring Boot)
        - src/main/java/com/example/
            - DemoApplication.java
            - controller/UserController.java
            - service/UserService.java
            - repository/UserRepository.java
            - model/User.java
    - frontend/ (Angular)
        - src/app/
            - app.component.ts
            - user/user.component.ts
            - user.service.ts
    - Dockerfile
    - knowledge/architecture/
        - architecture_facts.json (test data)
        - evidence_map.json (test data)

    Returns:
        Path: Root directory of sample project
    """
    project_root = temp_workspace / "sample_project"
    project_root.mkdir()

    # Backend structure
    backend_base = project_root / "backend" / "src" / "main" / "java" / "com" / "example"
    backend_base.mkdir(parents=True)

    # DemoApplication.java
    (backend_base / "DemoApplication.java").write_text("""
package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
""")

    # Controller
    controller_dir = backend_base / "controller"
    controller_dir.mkdir()
    (controller_dir / "UserController.java").write_text("""
package com.example.controller;

import com.example.service.UserService;
import com.example.model.User;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public List<User> getAllUsers() {
        return userService.findAll();
    }

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }
}
""")

    # Service
    service_dir = backend_base / "service"
    service_dir.mkdir()
    (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.model.User;
import com.example.repository.UserRepository;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public List<User> findAll() {
        return userRepository.findAll();
    }

    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }

    public User save(User user) {
        return userRepository.save(user);
    }
}
""")

    # Repository
    repository_dir = backend_base / "repository"
    repository_dir.mkdir()
    (repository_dir / "UserRepository.java").write_text("""
package com.example.repository;

import com.example.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
}
""")

    # Model
    model_dir = backend_base / "model"
    model_dir.mkdir()
    (model_dir / "User.java").write_text("""
package com.example.model;

import javax.persistence.*;

@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;
    private String email;

    // Getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
""")

    # Frontend structure
    frontend_base = project_root / "frontend" / "src" / "app"
    frontend_base.mkdir(parents=True)

    # app.component.ts
    (frontend_base / "app.component.ts").write_text("""
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'Demo App';
}
""")

    # user.component.ts
    user_dir = frontend_base / "user"
    user_dir.mkdir()
    (user_dir / "user.component.ts").write_text("""
import { Component, OnInit } from '@angular/core';
import { UserService } from '../user.service';

@Component({
  selector: 'app-user',
  templateUrl: './user.component.html',
  styleUrls: ['./user.component.css']
})
export class UserComponent implements OnInit {
  users: any[] = [];

  constructor(private userService: UserService) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.userService.getUsers().subscribe(data => {
      this.users = data;
    });
  }
}
""")

    # user.service.ts
    (frontend_base / "user.service.ts").write_text("""
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = '/api/users';

  constructor(private http: HttpClient) {}

  getUsers(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  getUser(id: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/${id}`);
  }

  createUser(user: any): Observable<any> {
    return this.http.post<any>(this.apiUrl, user);
  }
}
""")

    # Dockerfile
    (project_root / "Dockerfile").write_text("""
FROM openjdk:17-jdk-slim
WORKDIR /app
COPY backend/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
""")

    # Create test architecture data
    knowledge_dir = project_root / "knowledge" / "architecture"
    knowledge_dir.mkdir(parents=True)

    facts_data = {
        "system": {"name": "TestSystem", "domain": "test"},
        "containers": [{"id": "backend", "name": "Backend", "stereotype": "spring-boot", "evidence_ids": ["ev_1"]}],
        "components": [
            {
                "id": "UserController",
                "name": "UserController",
                "container": "backend",
                "stereotype": "class",
                "evidence_ids": ["ev_2"],
            }
        ],
        "interfaces": [],
        "relations": [],
    }

    evidence_data = {
        "ev_1": {
            "file_path": "backend/src/main/java/com/example/DemoApplication.java",
            "start_line": 1,
            "end_line": 10,
            "reason": "Spring Boot application",
        },
        "ev_2": {
            "file_path": "backend/src/main/java/com/example/controller/UserController.java",
            "start_line": 1,
            "end_line": 20,
            "reason": "REST controller",
        },
    }

    import json

    with open(knowledge_dir / "architecture_facts.json", "w") as f:
        json.dump(facts_data, f, indent=2)

    with open(knowledge_dir / "evidence_map.json", "w") as f:
        json.dump(evidence_data, f, indent=2)

    # Create Phase 2 test outputs (C4 and arc42)
    c4_dir = knowledge_dir / "c4"
    c4_dir.mkdir(exist_ok=True)

    (c4_dir / "c4-container.md").write_text("""# C4 Container Diagram

```mermaid
C4Container
    title Container Diagram - TestSystem

    Container(backend, "Backend", "Spring Boot", "REST API")
```

## Evidence
- ev_1: Backend container from DemoApplication.java
""")

    arc42_dir = knowledge_dir / "arc42"
    arc42_dir.mkdir(exist_ok=True)

    (arc42_dir / "01-introduction.md").write_text("""# 1 - Introduction

## System Overview

Name: TestSystem
Domain: test

## Containers

| Container | Technology | Evidence |
|-----------|------------|----------|
| Backend | Spring Boot | ev_1 |

## Evidence References
- ev_1: backend/src/main/java/com/example/DemoApplication.java - Spring Boot application
""")

    (arc42_dir / "05-building-blocks.md").write_text("""# 5 - Building Blocks

## Components

| Component | Container | Stereotype | Evidence |
|-----------|-----------|------------|----------|
| UserController | Backend | class | ev_2 |

## Evidence References
- ev_2: backend/src/main/java/com/example/controller/UserController.java - REST controller
""")

    return project_root


@pytest.fixture
def expected_facts():
    """
    Provide expected structure for architecture_facts.json.

    Returns:
        Dict: Expected JSON schema
    """
    return {
        "system": {"name": str, "domain": str, "description": str},
        "containers": list,  # Should contain backend, frontend, database
        "components": list,  # Should contain classes/modules
        "interfaces": list,  # Should contain REST endpoints
        "relations": list,  # Should contain dependencies
    }


@pytest.fixture
def orchestrator_config():
    """
    Provide orchestrator configuration for testing.

    Returns:
        Dict: Orchestrator config
    """
    return {
        "index_mode": "off",  # Skip Phase 0 for faster tests
        "llm_provider": "ollama",
        "llm_model": "qwen2.5-coder:7b",
    }


def load_json_file(file_path: Path) -> dict[str, Any]:
    """
    Load and parse JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def count_components_by_container(facts: dict[str, Any]) -> dict[str, int]:
    """
    Count components per container.

    Args:
        facts: Parsed architecture_facts.json

    Returns:
        Dict mapping container IDs to component counts
    """
    component_counts = {}
    for component in facts.get("components", []):
        container_id = component.get("container")
        component_counts[container_id] = component_counts.get(container_id, 0) + 1
    return component_counts


def extract_container_ids(facts: dict[str, Any]) -> set:
    """
    Extract all container IDs from facts.

    Args:
        facts: Parsed architecture_facts.json

    Returns:
        Set of container IDs
    """
    return {c.get("id") for c in facts.get("containers", [])}


def extract_component_ids(facts: dict[str, Any]) -> set:
    """
    Extract all component IDs from facts.

    Args:
        facts: Parsed architecture_facts.json

    Returns:
        Set of component IDs
    """
    return {c.get("id") for c in facts.get("components", [])}


# Pytest markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests (>10 seconds)")
    config.addinivalue_line("markers", "smoke: Quick smoke tests")
    config.addinivalue_line("markers", "phase1: Phase 1 tests (facts extraction)")
    config.addinivalue_line("markers", "phase2: Phase 2 tests (synthesis)")
