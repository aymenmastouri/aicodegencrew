# Ecosystem Strategy Pattern

Each language ecosystem is a self-contained module that defines file extensions, marker files, symbol extraction, container detection, version collection, and component routing.

> **Key files:** `src/aicodegencrew/shared/ecosystems/`

## Problem

Before this pattern, all language-specific logic was spread across monolithic files:
- `symbol_extractor.py` — one `if/elif` chain for all languages
- `manifest_builder.py` — a flat `FRAMEWORK_MARKERS` dict
- `container_collector.py` — sequential chain for all build systems
- `techstack_version_collector.py` — 10+ `_collect_*_versions()` methods
- `component_collector.py` — hardcoded `_SPRING_TECHNOLOGIES` routing

Adding a new ecosystem required changes in 5+ files, with no clear boundary between ecosystems.

## Solution

```
shared/ecosystems/
    __init__.py                      # Re-exports Registry + all ecosystems
    base.py                          # EcosystemDefinition abstract base class
    registry.py                      # EcosystemRegistry — detection + aggregation
    _utils.py                        # Shared helpers (find_block_end, etc.)
    java_jvm.py                      # Java/JVM (Spring, Maven, Gradle, Kotlin)
    javascript_typescript.py         # JavaScript/TypeScript (Angular, React, Vue, Node)
    python_ecosystem.py              # Python (pip, poetry, setuptools)
    c_cpp.py                         # C/C++ (CMake, Make, Autotools, Meson, Conan, vcpkg)
```

Each ecosystem implements `EcosystemDefinition` and provides:

| Capability | Method / Property | Used By |
|------------|-------------------|---------|
| Identity | `id`, `name`, `priority` | Registry ordering |
| File classification | `source_extensions`, `exclude_extensions`, `skip_directories` | `file_filters.py` (merged at import time) |
| Detection | `marker_files`, `detect(repo_path)` | `ManifestBuilder`, `TechStackVersionCollector` |
| Symbol extraction | `ext_to_lang`, `extract_symbols()` | `SymbolExtractor` |
| Container detection | `detect_container(dir_path, name, ctx)` | `ContainerCollector` |
| Version collection | `collect_versions(ctx)` | `TechStackVersionCollector` |
| Component routing | `get_component_technologies()`, `collect_components()` | `ComponentCollector` |
| **Dimension delegation** | **`collect_dimension(dimension, repo_path, container_id)`** | **All 9 refactored dimension collectors** |

## EcosystemRegistry

Singleton that registers all built-in ecosystems and provides aggregation queries:

```python
registry = EcosystemRegistry()
active = registry.detect(repo_path)           # Which ecosystems are present?
ext_map = registry.get_ext_to_lang(active)    # Merged extension → language map
markers = registry.get_framework_markers()     # Merged marker → label map
eco = registry.get_ecosystem_for_technology("Spring Boot")  # Route by technology
```

## CollectorContext

Lightweight adapter passed to ecosystem methods, providing utility callbacks from the calling collector without importing collector internals:

```python
ctx = CollectorContext(repo_path)
ctx.is_test_directory = collector._is_test_directory
ctx.add_version = collector._add_version
ctx.find_files = collector._find_files
```

This avoids circular dependencies between `shared/ecosystems/` and `pipelines/`.

## Priority-Based Container Detection

Each ecosystem has a `priority` (lower = checked first). The `ContainerCollector` iterates ecosystems in priority order — first match wins:

| Priority | Ecosystem | Marker Files |
|----------|-----------|-------------|
| 10 | Java/JVM | `build.gradle`, `build.gradle.kts`, `pom.xml` |
| 20 | JavaScript/TypeScript | `package.json` |
| 30 | C/C++ | `CMakeLists.txt`, `Makefile`, `meson.build`, `configure.ac` |
| 40 | Python | `pyproject.toml`, `setup.py` |

This preserves the original detection order and ensures Java projects with a `pyproject.toml` for tooling don't get misclassified as Python containers.

## Dimension Delegation

> **Diagram:** [collector-delegation.drawio](collector-delegation.drawio)

The core innovation: dimension collectors are **thin routers** (~40-80 lines) that delegate ecosystem-specific extraction to specialist collectors. Each ecosystem has an internal dispatch dict mapping dimension names to specialist collector classes.

```python
# In EcosystemDefinition base class
def collect_dimension(self, dimension: str, repo_path: Path, container_id: str = "") -> tuple[list, list]:
    """Returns (facts, relations). Default: no facts for any dimension."""
    return [], []

# In JavaJvmEcosystem
def collect_dimension(self, dimension, repo_path, container_id=""):
    dispatch = {
        "runtime":          self._collect_runtime,
        "dependencies":     self._collect_dependencies,
        "tests":            self._collect_tests,
        "data_model":       self._collect_data_model,
        "workflows":        self._collect_workflows,
        "build_system":     self._collect_build_system,
        "security_details": self._collect_security_details,
        "validation":       self._collect_validation,
        "error_handling":   self._collect_error_handling,
        "interfaces":       self._collect_interfaces,
    }
    handler = dispatch.get(dimension)
    return handler(repo_path, container_id) if handler else ([], [])
```

Each handler lazily imports its specialist collector:

```python
def _collect_runtime(self, repo_path, container_id):
    from ...pipelines.architecture_facts.collectors.spring.runtime_collector import SpringRuntimeCollector
    output = SpringRuntimeCollector(repo_path, container_id=container_id).collect()
    return output.facts, output.relations
```

**Dimension collector as thin router:**

```python
class RuntimeCollector(DimensionCollector):
    DIMENSION = "runtime"

    def __init__(self, repo_path, container_id="backend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self):
        self._log_start()
        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)
        self._log_end()
        return self.output
```

Some routers keep **cross-cutting logic** that is not ecosystem-specific:

| Router | Cross-Cutting Code | Reason |
|--------|-------------------|--------|
| `TestCollector` | `_collect_feature_files()` | Cucumber/Gherkin is language-agnostic |
| `WorkflowCollector` | `_collect_bpmn_workflows()` | BPMN is language-agnostic |
| `DataModelCollector` | `_collect_database_schema()`, `_collect_migrations()` | SQL/database is language-agnostic |
| `InterfaceCollector` | `_collect_openapi_specs()` | OpenAPI is language-agnostic |

### Specialist files per ecosystem

```
collectors/
    spring/                          15 specialists (5 existing + 10 new)
    angular/                         13 specialists (6 existing + 7 new)
    python_eco/                      11 specialists (2 existing + 9 new)
    cpp/                              6 specialists (2 existing + 4 new)
```

### Dimensions per ecosystem

| Ecosystem | Dispatch entries |
|-----------|-----------------|
| Java/JVM | runtime, dependencies, tests, data_model, workflows, build_system, security_details, validation, error_handling, interfaces |
| JavaScript/TypeScript | dependencies, tests, workflows, build_system, security_details, validation, error_handling |
| Python | runtime, dependencies, tests, data_model, workflows, build_system, security_details, validation, error_handling |
| C/C++ | dependencies, tests, workflows, build_system |

## Cross-Cutting Concerns

Not everything belongs to an ecosystem. These stay in their respective collectors:

| Concern | Stays In | Reason |
|---------|----------|--------|
| Docker Compose services | `ContainerCollector._detect_from_docker_compose()` | Infrastructure, not language |
| Dockerfile versions | `TechStackVersionCollector._collect_dockerfile_versions()` | Infrastructure, not language |
| Test directory detection | `ContainerCollector._is_test_directory()` | Shared across all ecosystems |
| Fallback detection | `ComponentCollector._fallback_detection()` | Legacy path without containers |

## Adding a New Ecosystem

New ecosystem = new files, zero changes to existing collectors or ecosystems:

**Step 1: Ecosystem definition** (`shared/ecosystems/rust.py`)
```python
class RustEcosystem(EcosystemDefinition):
    id = "rust"
    name = "Rust"
    priority = 35
    source_extensions = {".rs"}
    exclude_extensions = set()
    skip_directories = {"target"}
    marker_files = [MarkerFile("Cargo.toml", "Rust")]
    ext_to_lang = {".rs": "rust"}

    def extract_symbols(self, path, content, lines, lang, module): ...
    def detect_container(self, dir_path, name, ctx): ...
    def collect_versions(self, ctx): ...

    def collect_dimension(self, dimension, repo_path, container_id=""):
        dispatch = {
            "dependencies": self._collect_dependencies,
            "build_system":  self._collect_build_system,
            "tests":         self._collect_tests,
        }
        handler = dispatch.get(dimension)
        return handler(repo_path, container_id) if handler else ([], [])

    def _collect_dependencies(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.rust.dependency_collector import RustDependencyCollector
        output = RustDependencyCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations
    # ... more handlers as needed
```

**Step 2: Specialist collectors** (`collectors/rust/dependency_collector.py`, etc.)
```python
class RustDependencyCollector(DimensionCollector):
    DIMENSION = "dependencies"
    def collect(self): ...  # Parse Cargo.toml
```

**Step 3:** Register in `registry.py` → `_register_builtins()` and re-export in `__init__.py`.

No existing dimension collectors, ecosystems, or specialist files need any changes.

## Integration Points

```
ManifestBuilder
  └─ registry.get_framework_markers()     → FRAMEWORK_MARKERS dict
  └─ registry.detect(repo_path)           → manifest.ecosystems

SymbolExtractor
  └─ registry.get_ext_to_lang()           → EXT_TO_LANG dict
  └─ registry.get_ecosystem_for_extension → dispatch to ecosystem.extract_symbols()

ContainerCollector
  └─ registry.get_ecosystems_by_priority  → iterate, first match wins
  └─ ecosystem.detect_container()         → RawContainer dict

TechStackVersionCollector
  └─ registry.detect(repo_path)           → iterate active ecosystems
  └─ ecosystem.collect_versions(ctx)      → ctx.add_version() callbacks

ComponentCollector
  └─ registry.get_ecosystem_for_technology → route container to ecosystem
  └─ ecosystem.collect_components()       → specialist collectors

9 Dimension Collectors (thin routers)
  └─ registry.detect(repo_path)           → iterate active ecosystems
  └─ ecosystem.collect_dimension(dim)     → specialist collectors
  ├─ RuntimeCollector        → spring/runtime, python_eco/runtime
  ├─ DependencyCollector     → spring/dependency, angular/dependency, python_eco/dependency, cpp/dependency
  ├─ TestCollector           → spring/test, angular/test, python_eco/test, cpp/test
  ├─ DataModelCollector      → spring/data_model, python_eco/data_model
  ├─ WorkflowCollector       → spring/workflow, angular/workflow, python_eco/workflow, cpp/workflow
  ├─ BuildSystemCollector    → spring/build_system, angular/build_system, python_eco/build_system, cpp/build_system
  ├─ SecurityDetailCollector → spring/security_detail, angular/security_detail, python_eco/security
  ├─ ValidationCollector     → spring/validation, angular/validation, python_eco/validation
  ├─ ErrorHandlingCollector  → spring/error, angular/error, python_eco/error
  └─ InterfaceCollector      → spring/interface_detail (schedulers, listeners)

file_filters.py
  └─ registry.get_all_exclude_extensions  → merged into BINARY_EXTENSIONS
  └─ registry.get_all_skip_directories    → merged into SKIP_DIRS
```

---

© 2026 Aymen Mastouri. All rights reserved.
