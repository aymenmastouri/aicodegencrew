"""
Root-level shared fixtures for all tests.

Provides reusable test data and fixtures that are duplicated
across test_development_planning.py and test_code_generation.py.
"""

import json
from unittest.mock import MagicMock

import pytest

# =============================================================================
# Shared Sample Data
# =============================================================================

SAMPLE_FACTS = {
    "system": {"name": "TestSystem"},
    "containers": [
        {"id": "container.backend", "name": "Backend", "technology": "Spring Boot"},
        {"id": "container.frontend", "name": "Frontend", "technology": "Angular"},
    ],
    "components": [
        {
            "id": "comp.user_service",
            "name": "UserService",
            "stereotype": "service",
            "layer": "application",
            "package": "com.example.user",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/user/UserService.java",
            "file_paths": ["src/main/java/com/example/user/UserService.java"],
        },
        {
            "id": "comp.auth_controller",
            "name": "AuthController",
            "stereotype": "controller",
            "layer": "presentation",
            "package": "com.example.auth",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/auth/AuthController.java",
            "file_paths": ["src/main/java/com/example/auth/AuthController.java"],
        },
        {
            "id": "comp.user_repo",
            "name": "UserRepository",
            "stereotype": "repository",
            "layer": "dataaccess",
            "package": "com.example.user",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/user/UserRepository.java",
            "file_paths": ["src/main/java/com/example/user/UserRepository.java"],
        },
        {
            "id": "comp.user_entity",
            "name": "User",
            "stereotype": "entity",
            "layer": "domain",
            "package": "com.example.user",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/user/User.java",
            "file_paths": ["src/main/java/com/example/user/User.java"],
        },
    ],
    "interfaces": [
        {
            "id": "if.get_users",
            "type": "REST",
            "path": "/api/users",
            "method": "GET",
            "implemented_by": "comp.auth_controller",
        },
    ],
    "relations": [
        {"from": "comp.auth_controller", "to": "comp.user_service", "type": "uses"},
        {"from": "comp.user_service", "to": "comp.user_repo", "type": "uses"},
    ],
    "tests": [
        {
            "file_path": "src/test/java/com/example/user/UserServiceTest.java",
            "test_type": "unit",
            "targets": ["UserService"],
        },
    ],
    "security_details": [
        {
            "type": "authentication",
            "package": "com.example.auth",
            "detail": "Spring Security with JWT",
        },
    ],
    "validation_patterns": [
        {
            "target_class": "User",
            "pattern_name": "user.email",
            "annotation": "@Email",
            "usage_count": 3,
        },
    ],
    "error_handling_patterns": [
        {
            "handling_type": "exception_handler",
            "exception_class": "ResourceNotFoundException",
            "handler_method": "handleNotFound",
        },
    ],
    "workflows": [
        {
            "name": "User Registration",
            "components_involved": ["AuthController", "UserService"],
            "trigger": "REST POST /api/users",
        },
    ],
}


SAMPLE_PLAN_JSON = {
    "task_id": "TEST-001",
    "source_files": ["inputs/tasks/TEST-001.xml"],
    "understanding": {
        "summary": "Add email notification on user registration",
        "description": "Send welcome email when user registers",
        "requirements": ["Send welcome email"],
        "acceptance_criteria": ["Email sent within 1 minute"],
        "technical_notes": "Use existing EmailService",
    },
    "development_plan": {
        "affected_components": [
            {
                "id": "component.backend.service.user_service_impl",
                "name": "UserServiceImpl",
                "stereotype": "service",
                "layer": "application",
                "package": "com.example.user",
                "file_path": "backend/src/main/java/com/example/user/UserServiceImpl.java",
                "relevance_score": 0.95,
                "change_type": "modify",
                "source": "chromadb",
            },
            {
                "id": "component.backend.service.email_service",
                "name": "EmailService",
                "stereotype": "service",
                "layer": "application",
                "file_path": "",
                "relevance_score": 0.80,
                "change_type": "create",
                "source": "name_match",
            },
        ],
        "implementation_steps": [
            "1. Add EmailService dependency to UserServiceImpl",
            "2. Create sendWelcomeEmail() method",
            "3. Call sendWelcomeEmail() from registerUser()",
        ],
        "test_strategy": {
            "unit_tests": ["UserServiceImplTest.testSendEmail()"],
            "integration_tests": [],
            "similar_patterns": [],
        },
        "security_considerations": [
            {
                "security_type": "authentication",
                "recommendation": "Verify user is authenticated",
            }
        ],
        "validation_strategy": [
            {
                "validation_type": "not_null",
                "target_class": "UserServiceImpl",
                "recommendation": "Use @NotNull on email field",
            }
        ],
        "error_handling": [
            {
                "exception_class": "EmailSendException",
                "handling_type": "exception_handler",
                "recommendation": "Add retry with backoff",
            }
        ],
        "architecture_context": {
            "style": "Layered Architecture",
            "layer_pattern": "Controller -> Service -> Repository",
            "quality_grade": "B",
        },
        "estimated_complexity": "Low",
        "complexity_reasoning": "Simple service call addition",
        "estimated_files_changed": 2,
        "risks": ["Email failure should not block registration"],
    },
}


MINIMAL_PHASES_CONFIG = {
    "phases": {
        "discover": {
            "enabled": True,
            "name": "Repository Indexing",
            "order": 0,
            "required": True,
        },
        "extract": {
            "enabled": True,
            "name": "Architecture Facts Extraction",
            "order": 1,
            "required": True,
            "dependencies": ["discover"],
        },
        "analyze": {
            "enabled": True,
            "name": "Architecture Analysis",
            "order": 2,
            "required": True,
            "dependencies": ["extract"],
        },
        "document": {
            "enabled": True,
            "name": "Architecture Synthesis",
            "order": 3,
            "required": False,
            "dependencies": ["analyze"],
        },
        "plan": {
            "enabled": True,
            "name": "Development Planning",
            "order": 4,
            "required": False,
            "dependencies": ["analyze"],
        },
    },
    "presets": {
        "index": ["discover"],
        "scan": ["discover", "extract"],
        "analyze": [
            "discover",
            "extract",
            "analyze",
        ],
        "document": [
            "discover",
            "extract",
            "analyze",
            "document",
        ],
        "plan": [
            "discover",
            "extract",
            "analyze",
            "plan",
        ],
    },
    "execution": {
        "mode": "document",
        "stop_on_error": True,
    },
}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_knowledge_dir(tmp_path):
    """Create a temporary knowledge directory structure."""
    knowledge = tmp_path / "knowledge"
    architecture = knowledge / "architecture"
    architecture.mkdir(parents=True)
    (architecture / "c4").mkdir()
    (architecture / "arc42").mkdir()
    (knowledge / "development").mkdir()
    (knowledge / "codegen").mkdir()
    return knowledge


@pytest.fixture
def sample_facts():
    """Return a copy of SAMPLE_FACTS (safe to mutate in tests)."""
    return json.loads(json.dumps(SAMPLE_FACTS))


@pytest.fixture
def sample_plan():
    """Return a copy of SAMPLE_PLAN_JSON (safe to mutate in tests)."""
    return json.loads(json.dumps(SAMPLE_PLAN_JSON))


@pytest.fixture
def sample_facts_file(tmp_knowledge_dir):
    """Write SAMPLE_FACTS to a file and return its path."""
    facts_file = tmp_knowledge_dir / "architecture" / "architecture_facts.json"
    facts_file.write_text(json.dumps(SAMPLE_FACTS, indent=2), encoding="utf-8")
    return facts_file


@pytest.fixture
def mock_llm():
    """Create a mock LLM client (OpenAI-compatible)."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Mock LLM response"
    response.usage = MagicMock()
    response.usage.total_tokens = 100
    client.chat.completions.create.return_value = response
    return client


# =============================================================================
# Pytest configuration
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "phase0: Phase 0 tests (discover)")
    config.addinivalue_line("markers", "phase1: Phase 1 tests (extract)")
    config.addinivalue_line("markers", "phase2: Phase 2 tests (analyze)")
    config.addinivalue_line("markers", "phase3: Phase 3 tests (document)")
    config.addinivalue_line("markers", "phase4: Phase 4 tests (plan)")
    config.addinivalue_line("markers", "phase5: Phase 5 tests (implement)")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests (>10 seconds)")


@pytest.fixture(autouse=True)
def _isolate_phase_state(tmp_path):
    """Redirect phase_state.json to tmp dir for every test."""
    from aicodegencrew.shared.utils.phase_state import configure_state_dir

    configure_state_dir(tmp_path)
    yield
    configure_state_dir(None)
