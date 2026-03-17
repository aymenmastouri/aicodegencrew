# Collector Semantic Contract

Rules that every dimension collector must follow to produce ecosystem-independent, comparable facts.

> **Key principle:** Type fields contain abstract concepts. Framework details go into `metadata`.

---

## Why This Matters

The architecture model consumes facts from 16 dimension collectors. Phase 2 (Analyze) and Phase 3 (Document) compare facts across ecosystems:

- "How many REST endpoints does each container expose?"
- "Which containers have authentication?"
- "What validation patterns are used?"

If Java produces `security_type="pre_authorize"` but Python produces `security_type="flask_login_required"`, cross-ecosystem queries break. The consumer would need a mapping table per ecosystem — defeating the purpose of a unified model.

**Rule: A consumer that doesn't know the ecosystem must still understand every fact.**

---

## Field Naming Rules

### Type Fields (enums)

Every fact has one or more type/category fields (`test_type`, `security_type`, `handling_type`, `validation_type`, `workflow_type`, `type`). These follow strict rules:

| Rule | Correct | Wrong |
|------|---------|-------|
| Use abstract concepts, not framework names | `"authentication"` | `"flask_login_required"` |
| Use abstract concepts, not annotation names | `"authorization"` | `"pre_authorize"` |
| No framework prefix | `"exception_handler"` | `"flask_error_handler"` |
| No tool-specific subtypes | `type="cmake"` | `type="cmake_fetchcontent"` |
| Consistent across ecosystems | `"async"` for both `@Async` and Celery | `"celery_task"` |

### The `metadata` Dict

Framework-specific details belong in `metadata`:

```python
# Correct
fact = RawSecurityDetail(
    security_type="authentication",          # abstract concept
    metadata={
        "framework": "django",              # which framework
        "mechanism": "login_required",      # how it's implemented
    },
)

# Wrong
fact = RawSecurityDetail(
    security_type="django_login_required",   # framework name in type field
)
```

Standard metadata keys:

| Key | Purpose | Example Values |
|-----|---------|----------------|
| `framework` | Which framework provides this | `"django"`, `"spring"`, `"flask"`, `"fastapi"` |
| `mechanism` | How the framework implements it | `"login_required"`, `"errorhandler"`, `"middleware"` |
| `kind` | Sub-classification within a type | `"class_based_view"`, `"fixture_config"` |
| `confidence` | How certain the heuristic is (0.0-1.0) | `0.9` for annotation-based, `0.6` for filename-based |

### The `version` Field (Dependencies)

| Value | Meaning |
|-------|---------|
| `"1.2.3"` | Exact version |
| `">=1.2"` | Version constraint |
| `"managed"` | Version managed by parent (Maven BOM) |
| `""` (empty) | Version not specified / any version |

Never use `"any"` or `"latest"` — these are ambiguous.

### The `scope` Field (Dependencies)

Standard scope values across all ecosystems:

| Scope | Maven | Gradle | NPM | Python | CMake |
|-------|-------|--------|-----|--------|-------|
| `"compile"` | compile | implementation/api | dependencies | install_requires | find_package |
| `"runtime"` | runtime | runtimeOnly | dependencies | — | — |
| `"test"` | test | testImplementation | — | tests_require | — |
| `"dev"` | — | — | devDependencies | dev (extras) | — |
| `"provided"` | provided | compileOnly | — | — | — |

---

## Per-Collector Semantic Contracts

### TestCollector → `RawTestFact`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `test_type` | `"unit"`, `"integration"`, `"e2e"` | Three levels only. Never framework-specific. |
| `framework` | `"junit"`, `"pytest"`, `"unittest"`, `"googletest"`, `"catch2"`, `"ctest"`, `"doctest"`, `"cucumber"`, `"jasmine"`, `"jest"`, `"playwright"` | Lowercase, no underscores in framework names. |
| `scenarios` | List of test names | Flat names, no dot notation. `"testLogin"` not `"LoginSuite.testLogin"`. |
| `tested_component_hint` | Component name or `""` | Derived from file path, never guessed from test content. |

Fixture files (`conftest.py`) use `test_type="unit"` with `metadata={"kind": "fixture_config"}`.

### DependencyCollector → `RawDependency`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `type` | `"maven"`, `"gradle"`, `"npm"`, `"python"`, `"cmake"`, `"conan"`, `"vcpkg"` | Package manager name. Sub-mechanisms go in metadata. |
| `version` | Version string or `""` | See version rules above. |
| `scope` | `"compile"`, `"runtime"`, `"test"`, `"dev"`, `"provided"` | See scope table above. |

CMake sub-mechanisms (`find_package` vs `FetchContent` vs `ExternalProject`) go in `metadata["cmake_mechanism"]`.

### BuildSystemCollector → `RawBuildFact`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `build_tool` | `"gradle"`, `"maven"`, `"npm"`, `"angular"`, `"cmake"`, `"meson"`, `"python"`, `"tox"` | Tool category, not filename. `"python"` not `"pyproject.toml"`. |
| `tasks` | List of plain target names | No type prefixes. `["myapp", "mylib"]` not `["exe:myapp", "lib:mylib"]`. |
| `plugins` | List of plugin identifiers | Build plugins / build backends. |
| `properties` | Dict of key-value pairs | Build properties (versions, standards, etc.). |

Target classification (executable vs library) goes in `metadata["executables"]` and `metadata["libraries"]`.

### ValidationCollector → `RawValidationRule`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `validation_type` | `"not_null"`, `"not_blank"`, `"size"`, `"pattern"`, `"min"`, `"max"`, `"email"`, `"custom"`, `"valid"`, `"model_validation"`, `"schema_validation"`, `"form_validation"` | Abstract constraint type. |
| `constraint` | Constraint expression or `""` | `"min=1, max=100"` or validator count. |
| `target_class` | Class being validated | Always populated. |
| `target_field` | Field being validated or `""` | Empty for class-level validation. |

Framework goes in `metadata["framework"]`: `"pydantic"`, `"marshmallow"`, `"django"`, `"javax.validation"`.

### SecurityDetailCollector → `RawSecurityDetail`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `security_type` | `"pre_authorize"`, `"secured"`, `"roles_allowed"`, `"csrf"`, `"cors"`, `"authentication"`, `"authorization"`, `"angular_guard"` | Abstract security concept. |
| `roles` | List of role/permission strings | `["ADMIN", "USER"]` or `["app.view_item"]`. |
| `method` | Method name or `""` | Method the security applies to. |
| `class_name` | Class name | Class containing the security annotation/decorator. |

Implementation details go in `metadata`:
- `metadata["framework"]`: `"spring"`, `"django"`, `"fastapi"`, `"angular"`
- `metadata["mechanism"]`: `"login_required"`, `"permission_required"`, `"dependency_injection"`, `"permission_classes"`

### ErrorHandlingCollector → `RawErrorHandlingFact`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `handling_type` | `"exception_handler"`, `"controller_advice"`, `"custom_exception"`, `"angular_error_handler"`, `"http_interceptor"` | Abstract handler pattern. |
| `exception_class` | Exception/error class name | What is handled or defined. |
| `http_status` | HTTP status code or `""` | `"404"`, `"500"`, `"NOT_FOUND"`. |
| `handler_method` | Handler method name or `""` | The method doing the handling. |

Framework details go in `metadata["framework"]` and `metadata["mechanism"]`.

### RuntimeCollector → `RawRuntimeFact`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `type` | `"scheduler"`, `"async"`, `"event_listener"`, `"batch_job"`, `"batch_step"` | Abstract runtime behavior. Celery tasks are `"async"`, not `"celery_task"`. |
| `schedule` | Cron expression or `None` | Time-based scheduling only. |
| `trigger` | Event/trigger type or `None` | Event-based triggering only. |

Framework goes in `metadata["framework"]`: `"spring"`, `"celery"`, `"apscheduler"`.

### DataModelCollector → `RawEntity`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `type` | `"entity"`, `"table"`, `"view"` | Same across JPA, SQLAlchemy, Django ORM. |
| `columns` | List of `{"name", "type", ...}` | Field definitions. |

Relationships use `RelationHint` with consistent types:

| Relation Type | JPA Annotation | SQLAlchemy | Django |
|---------------|---------------|------------|--------|
| `"one_to_many"` | `@OneToMany` | `relationship()` (plural field) | — |
| `"many_to_one"` | `@ManyToOne` | `relationship()` (singular field) | `ForeignKey` |
| `"one_to_one"` | `@OneToOne` | — | `OneToOneField` |
| `"many_to_many"` | `@ManyToMany` | — | `ManyToManyField` |

ORM type goes in `metadata["orm"]`: `"jpa"`, `"sqlalchemy"`, `"django"`.

### WorkflowCollector → `RawWorkflow`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `workflow_type` | `"bpmn"`, `"spring_statemachine"`, `"camunda"`, `"flowable"`, `"xstate"`, `"ngrx_effects"`, `"ngrx_reducer"`, `"rxjs_flow"`, `"custom"`, `"enum_based"`, `"business_flow"`, `"service_orchestration"`, `"action_dispatcher"`, `"celery_workflow"`, `"airflow_dag"` | More specific than other type fields because workflows are inherently technology-specific. |
| `states` | List of state names | Always populated when determinable. |
| `transitions` | List of `{"from", "to", "trigger"}` | Always populated when determinable. |
| `actions` | List of action/command names | Methods, dispatchers, service calls. |

### ComponentCollector → `RawComponent`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `stereotype` | `"controller"`, `"service"`, `"repository"`, `"entity"`, `"module"`, `"component"`, `"guard"`, `"pipe"`, `"directive"`, `"model"`, `"router"`, `"library"`, `"class"`, `"handler"`, `"manager"` | Cross-ecosystem classification. Django views are `"controller"`, not `"view"`. |
| `layer_hint` | `"presentation"`, `"application"`, `"domain"`, `"data_access"` or `None` | Architectural layer. |
| `container_hint` | Container name from parameter | Always from `self.container_id`, never hardcoded. |

Sub-classifications go in `metadata["kind"]`: `"class_based_view"`, `"api_router"`, `"blueprint"`.

### InterfaceCollector → `RawInterface`

| Field | Allowed Values | Notes |
|-------|---------------|-------|
| `type` | `"rest_endpoint"`, `"route"`, `"scheduler"`, `"kafka_listener"`, `"rabbit_listener"`, `"graphql"`, `"grpc_service"`, `"public_api"`, `"extern_function"` | Protocol/transport type. |
| `path` | URL path, file path, or `None` | HTTP path for REST, file path for public APIs. |
| `method` | HTTP method (`"GET"`, `"POST"`, ...) or `None` | Only for HTTP endpoints. |
| `implemented_by_hint` | Component/function name | Best-effort link to implementing code. |

---

## Ecosystem Coverage Matrix

Which dimensions each ecosystem supports:

| Collector | Java/JVM | JS/TS | C/C++ | Python |
|-----------|----------|-------|-------|--------|
| system | cross-cutting | cross-cutting | cross-cutting | cross-cutting |
| containers | detect | detect | detect | detect |
| components | Spring specialists | Angular specialists | Class heuristics | Django/Flask/FastAPI |
| interfaces | Spring REST | Angular routes | Public headers, gRPC proto | Flask/FastAPI/Django routes |
| data_model | JPA entities | — | — | SQLAlchemy, Django ORM |
| runtime | @Scheduled, @Async | — | — | Celery, APScheduler |
| infrastructure | cross-cutting | cross-cutting | cross-cutting | cross-cutting |
| dependencies | Maven, Gradle | NPM | CMake, Conan, vcpkg | pip, Poetry |
| workflows | BPMN, Spring SM | XState, NgRx | Enum FSMs | Celery chains, Airflow |
| tech_versions | detect | detect | detect | detect |
| security_details | @PreAuthorize, CSRF/CORS | Angular guards | — | @login_required, DRF perms |
| validation | Bean Validation | Angular Validators | — | Pydantic, Marshmallow, Django forms |
| tests | JUnit, Cucumber | Jasmine, Playwright | GoogleTest, Catch2, CTest | pytest, unittest |
| error_handling | @ExceptionHandler | ErrorHandler, interceptors | — | Custom exceptions, Flask errorhandler |
| build_system | Gradle, Maven | npm, Angular | CMake, Meson | pyproject.toml, setup.py, tox |
| evidence | cross-cutting | cross-cutting | cross-cutting | cross-cutting |

**—** = No meaningful equivalent in this ecosystem (intentional gap, not missing implementation).

---

## Adding Ecosystem Support to an Existing Dimension

All dimension collectors are thin routers that delegate via `ecosystem.collect_dimension()`. To add support for a new ecosystem in an existing dimension:

1. **Create a specialist file** in the ecosystem's sub-package (e.g., `collectors/rust/test_collector.py`).
2. **Read existing specialist implementations** for that dimension. Use the same fact types and abstract field values.
3. **Import the dataclass** from the dimension collector (e.g., `from ..dependency_collector import RawDependency`).
4. **Add a dispatch entry** in the ecosystem's `collect_dimension()` method.
5. **Export from `__init__.py`** in the ecosystem sub-package.

No changes needed in the dimension collector (thin router) itself.

### Checklist for specialist collectors

1. **Use the same fact types.** Python tests produce `RawTestFact`, not a new `RawPythonTestFact`.
2. **Use abstract type values.** Check the tables above for allowed values.
3. **Put framework details in metadata.** `metadata={"framework": "...", "mechanism": "..."}`.
4. **Follow the same evidence pattern.** Every fact gets `add_evidence(path, line_start, line_end, reason)`.
5. **Use `self.container_id`** for `container_hint`, never hardcode `"backend"` or `"frontend"`.
6. **Derive version as empty string** when unspecified, not `"any"` or `"latest"`.

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| `security_type="flask_login_required"` | Consumer needs Flask knowledge | `security_type="authentication"` + `metadata` |
| `test_type="fixture"` | Not a test type, it's a test infrastructure concern | `test_type="unit"` + `metadata={"kind": "fixture_config"}` |
| `tasks=["exe:myapp"]` | Prefix couples consumer to CMake | `tasks=["myapp"]` + `metadata={"executables": ["myapp"]}` |
| `build_tool="pyproject.toml"` | Filename, not tool category | `build_tool="python"` |
| `type="cmake_fetchcontent"` | Over-specific, sub-mechanism | `type="cmake"` + `metadata={"cmake_mechanism": "fetchcontent"}` |
| `version="any"` | Ambiguous sentinel | `version=""` (empty = unspecified) |
| `stereotype="view"` | Django-specific term | `stereotype="controller"` + `metadata={"kind": "class_based_view"}` |

---

(c) 2026 Aymen Mastouri. All rights reserved.
