# Phase 1 — Extract (Architecture Facts Extraction)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Knowledge

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `extract` |
| Display Name | Architecture Facts Extraction |
| Type | Pipeline (deterministic, **NO LLM**) |
| Entry Point | `pipelines/architecture_facts/pipeline.py` → `ArchitectureFactsPipeline` |
| Output | `knowledge/extract/` |
| Dependency | Discover |
| Status | **IMPLEMENTED** |

> **Diagram:** [phase-1-extract-architecture.drawio](phase-1-extract-architecture.drawio)

Extract creates the **single source of truth for architecture**. No interpretation, no LLM, no documentation — only facts and evidence. Everything not in Extract output must NOT appear in downstream phases.

## 2. Goals

- Deterministically extract 16 architecture dimensions from source code
- Build a canonical model with normalized component IDs
- Map all relations via a 7-tier resolution pipeline
- Trace request flows (Controller → Service → Repository chains)
- Produce evidence for every extracted fact (file path, line number)

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Target repository | File system | `PROJECT_PATH` |
| **Input** | Repo manifest (optional) | JSON | `knowledge/discover/repo_manifest.json` |
| **Output** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Output** | Evidence map | JSON | `knowledge/extract/evidence_map.json` |

## 4. Architecture

### Collector System

The collector system uses a modular architecture with an **Orchestrator** that coordinates **Dimension Collectors** and **Specialist Collectors**. All dimension collectors are **thin routers** (~40-80 lines) that delegate ecosystem-specific logic to specialist collectors in `spring/`, `angular/`, `python_eco/`, `cpp/` sub-packages via the **Ecosystem Strategy Pattern** (`shared/ecosystems/`).

> **Diagram:** [collector-delegation.drawio](../../architecture/collector-delegation.drawio)

**Orchestrator** (`collectors/orchestrator.py`):
8-step flow: System → Container → Component → Interface → DataModel → Runtime → Infrastructure → Evidence

**Dimension Collectors (thin routers):**

| Collector | Output | Delegation | Cross-Cutting |
|-----------|--------|------------|---------------|
| `SystemCollector` | system metadata | — (cross-cutting only) | System name from root files |
| `ContainerCollector` | containers | `ecosystem.detect_container()` | Docker Compose |
| `ComponentCollector` | components | `ecosystem.collect_components()` | — |
| `TechStackVersionCollector` | tech_versions | `ecosystem.collect_versions()` | Dockerfile |
| `InterfaceCollector` | interfaces | `ecosystem.collect_dimension("interfaces")` | OpenAPI |
| `DataModelCollector` | data model | `ecosystem.collect_dimension("data_model")` | SQL tables, migrations |
| `RuntimeCollector` | runtime | `ecosystem.collect_dimension("runtime")` | — |
| `DependencyCollector` | dependencies | `ecosystem.collect_dimension("dependencies")` | — |
| `TestCollector` | tests | `ecosystem.collect_dimension("tests")` | Cucumber/Gherkin |
| `WorkflowCollector` | workflows | `ecosystem.collect_dimension("workflows")` | BPMN |
| `BuildSystemCollector` | build_system | `ecosystem.collect_dimension("build_system")` | — |
| `SecurityDetailCollector` | security_details | `ecosystem.collect_dimension("security_details")` | — |
| `ValidationCollector` | validation | `ecosystem.collect_dimension("validation")` | — |
| `ErrorHandlingCollector` | error_handling | `ecosystem.collect_dimension("error_handling")` | — |
| `InfrastructureCollector` | infrastructure | — (cross-cutting only) | Docker, K8s, CI/CD |
| `EvidenceCollector` | evidence map | — (cross-cutting only) | Aggregates all evidence |

**Specialist Collectors:** 45 total (15 spring + 13 angular + 11 python + 6 c/c++)

### Extraction per Ecosystem

All dimension collectors delegate to ecosystem modules via `EcosystemRegistry.detect()` → `ecosystem.collect_dimension()`. Each ecosystem defines which dimensions it supports — shown below as collapsible tabs.

> **Full pattern docs:** [Ecosystem Strategy Pattern](../../architecture/ecosystem-strategy.md)

<details>
<summary><strong>Java/JVM</strong> — Priority 10 | <code>shared/ecosystems/java_jvm.py</code></summary>

| Capability | Details |
|------------|---------|
| **Source extensions** | `.java`, `.kt`, `.kts` |
| **Exclude extensions** | `.class`, `.jar`, `.war`, `.ear` |
| **Skip directories** | `target`, `.gradle`, `.mvn`, `buildSrc` |
| **Marker files** | `pom.xml` → Spring/Maven, `build.gradle` → Spring/Gradle, `build.gradle.kts` → Spring/Gradle-KTS |

**Symbol extraction** — classes, methods, Spring annotations (`@RestController`, `@Service`, `@Repository`, `@Entity`), `@*Mapping` endpoints

**Container detection** — Gradle: reads `build.gradle` for `spring-boot` marker, searches `@SpringBootApplication` main class. Maven: reads `pom.xml`, skips parent POMs (`<modules>` + `<packaging>pom`). Classifies: `backend` / `batch` / `library` / `test`.

**Version collection:**

| Source | Versions extracted |
|--------|-------------------|
| `build.gradle` / `build.gradle.kts` | Spring Boot, Java, Kotlin |
| `gradle-wrapper.properties` | Gradle |
| `gradle.properties` | Spring Boot, Kotlin, Java |
| `libs.versions.toml` | Spring Boot, Kotlin, Java (version catalog) |
| `pom.xml` | Spring Boot (parent + BOM + properties), Java, Maven |
| `.java-version` | Java |

**Specialist collectors (15):**

| Specialist | Dimension | Extracts |
|------------|-----------|----------|
| `SpringRestCollector` | components | `@RestController`, `@RequestMapping` |
| `SpringServiceCollector` | components | `@Service`, interface+impl mappings |
| `SpringRepositoryCollector` | components | `JpaRepository`, custom queries |
| `SpringConfigCollector` | components | `@Configuration`, `application.yml` |
| `SpringSecurityCollector` | components | Security configs |
| `SpringRuntimeCollector` | runtime | `@Scheduled`, `@Async`, `@EventListener`, Spring Batch |
| `SpringDependencyCollector` | dependencies | Maven and Gradle dependencies |
| `SpringTestCollector` | tests | JUnit, SpringBootTest |
| `SpringDataModelCollector` | data_model | JPA entities, relationships |
| `SpringWorkflowCollector` | workflows | State machines, Camunda, orchestration |
| `SpringBuildSystemCollector` | build_system | Gradle, Maven modules and plugins |
| `SpringSecurityDetailCollector` | security_details | `@PreAuthorize`, `@Secured`, CSRF/CORS |
| `SpringValidationCollector` | validation | Bean Validation annotations |
| `SpringErrorCollector` | error_handling | `@ExceptionHandler`, `@ControllerAdvice` |
| `SpringInterfaceDetailCollector` | interfaces | `@Scheduled`, `@KafkaListener`, `@RabbitListener` |

</details>

<details>
<summary><strong>JavaScript/TypeScript</strong> — Priority 20 | <code>shared/ecosystems/javascript_typescript.py</code></summary>

| Capability | Details |
|------------|---------|
| **Source extensions** | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs` |
| **Exclude extensions** | `.min.js`, `.min.css`, `.map` |
| **Skip directories** | `node_modules`, `.next`, `.nuxt`, `dist`, `.angular` |
| **Marker files** | `angular.json` → Angular, `package.json` → Node.js |

**Symbol extraction** — classes, interfaces, functions, Angular/NestJS decorators (`@Component`, `@Injectable`, `@NgModule`, `@Controller`)

**Container detection** — Reads `package.json` dependencies: `@angular/core` → Angular, `react` → React, `vue` → Vue, `cypress`/`playwright` → test. Classifies: `frontend` / `test`.

**Version collection:**

| Source | Versions extracted |
|--------|-------------------|
| `package.json` | Angular, React, Vue, TypeScript, RxJS, NgRx, Webpack, Vite, Jest, Karma, Playwright, Cypress, Node.js (engines) |
| `angular.json` | Angular CLI (from `$schema` URL) |
| `.node-version`, `.nvmrc` | Node.js |

**Specialist collectors (13):**

| Specialist | Dimension | Extracts |
|------------|-----------|----------|
| `AngularModuleCollector` | components | `@NgModule` |
| `AngularComponentCollector` | components | `@Component` |
| `AngularServiceCollector` | components | `@Injectable` services |
| `AngularRoutingCollector` | interfaces | `RouterModule`, routes |
| `OpenAPICollector` | interfaces | OpenAPI/Swagger specs |
| `AngularStateCollector` | components | NgRx state management |
| `AngularDependencyCollector` | dependencies | NPM packages |
| `AngularTestCollector` | tests | Jasmine, Jest, Playwright |
| `AngularWorkflowDetailCollector` | workflows | XState, NgRx, RxJS flows |
| `AngularBuildSystemCollector` | build_system | npm scripts, angular.json |
| `AngularSecurityDetailCollector` | security_details | Route guards |
| `AngularValidationDetailCollector` | validation | Angular form validators |
| `AngularErrorDetailCollector` | error_handling | ErrorHandler, HTTP interceptors |

*(Node.js)* — `export class/function/const` with naming convention detection (service, controller, entity, test)

</details>

<details>
<summary><strong>C/C++</strong> — Priority 30 | <code>shared/ecosystems/c_cpp.py</code></summary>

| Capability | Details |
|------------|---------|
| **Source extensions** | `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.hh`, `.cxx`, `.hxx` |
| **Exclude extensions** | `.o`, `.obj`, `.a`, `.lib`, `.so`, `.dll`, `.dylib`, `.exe` |
| **Skip directories** | `build`, `cmake-build-debug`, `cmake-build-release` |
| **Marker files** | `CMakeLists.txt` → CMake, `Makefile` → Make, `configure.ac` → Autotools, `meson.build` → Meson, `SConstruct` → SCons, `conanfile.txt`/`.py` → Conan, `vcpkg.json` → vcpkg |

**Symbol extraction** — structs, unions, enums, functions, macros, typedefs. C++ additionally: classes, namespaces. Skips include guards and standard keywords.

**Container detection** — CMake: `add_executable`/`add_library`, framework hints via `find_package` (Qt, Boost, OpenCV, GoogleTest, gRPC, SDL2, OpenGL). Make: compiler variable detection. Meson: `executable()`/`library()`. Autotools: `AC_PROG_CXX`. Classifies: `backend` / `library` / `test`.

**Version collection:**

| Source | Versions extracted |
|--------|-------------------|
| `CMakeLists.txt` | CMake (`cmake_minimum_required`), C Standard, C++ Standard, project version, library versions via `find_package` |
| `Makefile` | C/C++ Standard from `-std=` flags |
| `conanfile.txt` | Conan dependency versions |
| `vcpkg.json` | vcpkg dependency versions |

**Specialist collectors (6):**

| Specialist | Dimension | Extracts |
|------------|-----------|----------|
| `CppComponentCollector` | components | Classes, services, handlers |
| `CppInterfaceCollector` | interfaces | Public APIs, gRPC, extern functions |
| `CppDependencyCollector` | dependencies | CMake, Conan, vcpkg |
| `CppTestCollector` | tests | GoogleTest, Catch2, CTest, doctest |
| `CppWorkflowCollector` | workflows | Enum-based FSMs |
| `CppBuildSystemCollector` | build_system | CMake, Meson |

</details>

<details>
<summary><strong>Python</strong> — Priority 40 | <code>shared/ecosystems/python_ecosystem.py</code></summary>

| Capability | Details |
|------------|---------|
| **Source extensions** | `.py`, `.pyx`, `.pxd` |
| **Exclude extensions** | `.pyc`, `.pyo` |
| **Skip directories** | `__pycache__`, `.venv`, `venv`, `.tox`, `.eggs`, `.mypy_cache`, `.pytest_cache` |
| **Marker files** | `requirements.txt` → Python, `pyproject.toml` → Python, `setup.py` → Python, `setup.cfg` → Python |

**Symbol extraction** — classes, top-level functions, methods (indented `def`), decorators (skips `@property`, `@staticmethod`, `@classmethod`, `@abstractmethod`)

**Container detection** — `pyproject.toml`/`setup.py` present → Python container. Framework hints from content: Django, Flask, FastAPI. Classifies: `backend` / `test`.

**Version collection:**

| Source | Versions extracted |
|--------|-------------------|
| `.python-version` | Python |
| `pyproject.toml` | Python (from `requires-python`) |

**Specialist collectors (11):**

| Specialist | Dimension | Extracts |
|------------|-----------|----------|
| `PythonComponentCollector` | components | Django views, Flask blueprints, FastAPI routers |
| `PythonInterfaceCollector` | interfaces | REST endpoints, URL patterns, gRPC |
| `PythonRuntimeCollector` | runtime | Celery tasks, APScheduler |
| `PythonDependencyCollector` | dependencies | pip, poetry, pyproject.toml |
| `PythonTestCollector` | tests | pytest, unittest |
| `PythonDataModelCollector` | data_model | SQLAlchemy, Django ORM |
| `PythonWorkflowCollector` | workflows | Celery chains, Airflow DAGs |
| `PythonBuildSystemCollector` | build_system | pyproject.toml, setup.py, tox |
| `PythonSecurityCollector` | security_details | @login_required, DRF permissions, FastAPI Depends |
| `PythonValidationCollector` | validation | Pydantic, Marshmallow, Django forms |
| `PythonErrorCollector` | error_handling | Custom exceptions, Flask errorhandler |

</details>

<details>
<summary><strong>Cross-Cutting</strong> — Docker / Infrastructure (not ecosystem-specific)</summary>

These remain in their respective collectors, independent of ecosystem detection:

| Collector | What | Source |
|-----------|------|--------|
| `ContainerCollector` | Database + external services | `docker-compose.yml` (PostgreSQL, MySQL, MongoDB, Redis, Kafka, RabbitMQ, Elasticsearch) |
| `TechStackVersionCollector` | Base image versions | `Dockerfile` (OpenJDK, Node.js, Nginx, PostgreSQL, GCC, Clang/LLVM) |
| `OracleTableCollector` | Table definitions | SQL files (multi-dialect) |
| `MigrationCollector` | Schema migrations | Flyway, Liquibase |

</details>

### 7-Tier Relation Resolution

`ModelBuilder` resolves raw component names to canonical IDs:

| Tier | Strategy | Example |
|------|----------|---------|
| 1 | Direct old-ID mapping | `"comp_1_ActionService"` → canonical |
| 2 | Already canonical | `"component.backend.service.action_service"` |
| 3 | Exact name match (unambiguous) | `"ActionService"` → 1 candidate |
| 4 | Disambiguate by stereotype hint | `"service:ActionService"` → unique |
| 5 | Interface-to-implementation | `"OrderService"` → `"OrderServiceImpl"` |
| 6 | Fuzzy suffix match | `"UserService"` ↔ `"UserServiceImpl"` |
| 7 | File path match | `from_file_hint` → component owning that file |

### Endpoint Flow Builder

Constructs evidence-based request chains from REST interfaces:

```
Interface: POST /workflow/create
  → Controller: WorkflowController (via implemented_by)
    → Service: WorkflowServiceImpl (via relation: uses)
      → Repository: WorkflowRepository (via relation: uses)
```

Chain depth limited to 5 levels. Only flows with 2+ elements included.

### FactAdapter Pipeline

Bridges collector outputs (Raw types) to legacy types consumed by ModelBuilder:

```
Collectors (RawComponent, RawInterface, RelationHint)
  → FactAdapter.to_collected_*()
  → DimensionResultsAdapter.convert()
  → ModelBuilder.build() → CanonicalModel (normalized, deduplicated)
```

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| No LLM | Facts must be deterministic and reproducible |
| Ecosystem Strategy Pattern | Each language ecosystem (Java, JS/TS, Python, C/C++) is a self-contained module defining extensions, markers, symbols, containers, versions, and dimension-specific extraction. Adding a new ecosystem = new files, zero changes to existing collectors or ecosystems. |
| Dimension delegation | All 9 ecosystem-dependent dimension collectors are thin routers (~40-80 lines) that delegate via `ecosystem.collect_dimension()`. Cross-cutting logic (BPMN, Cucumber, SQL, OpenAPI) stays in the router. |
| Specialist collectors | 45 specialists in 4 sub-packages. Modular — add new frameworks without touching existing code |
| 7-tier resolution | Handles ambiguous references (same class name in different packages) |
| Evidence-first | Every fact traceable to file + line number |

### Rules (MUST FOLLOW)

| DO | DO NOT |
|-------|-----------|
| Extract only detectable facts | Use LLM |
| Reference evidence for every fact | Describe responsibilities |
| Mark UNKNOWN if no evidence | Make architecture decisions |
| Use exact class/file names | Summarize or interpret |

## 6. Dependencies

- **Upstream**: Phase 0 (Discover) — `repo_manifest.json` for framework hints (optional)
- **Downstream**:
  - Phase 2 (Analyze): `architecture_facts.json` as primary input
  - Phase 3 (Document): `architecture_facts.json` + `evidence_map.json`
  - Phase 4 (Plan): All 17 keys of `architecture_facts.json`
  - Phase 5 (Implement): File path resolution + facts queries

## 7. Quality Gates & Validation

- `QualityValidator`: checks extracted facts for completeness
- `PhaseOutputValidator`: verifies `architecture_facts.json` exists and has required keys before downstream phases run

## 8. Configuration

No phase-specific configuration — Extract uses `PROJECT_PATH` and runs deterministically.

## 9. Risks & Open Points

- New frameworks require a new ecosystem module (one file in `shared/ecosystems/`)
- Specialist collectors are regex-based — may miss unusual code patterns
- Ecosystems not yet implemented: Rust, Go, Ruby, PHP (marker files exist but no extraction/version/container logic)

---

© 2026 Aymen Mastouri. All rights reserved.
