# Ecosystem Plugins

Custom ecosystems can be added as plugins by placing them in subdirectories here.

## Directory Structure

```
plugins/ecosystems/
    rust/
        __init__.py              # Must define a class that extends EcosystemDefinition
        dependency_collector.py  # Optional: specialist collectors
        test_collector.py
    go/
        __init__.py
        ...
```

## Contract

Each plugin subdirectory must contain an `__init__.py` that defines at least one
concrete class inheriting from `EcosystemDefinition`.

The class must implement all abstract properties and methods:

- `id` — Unique string identifier (e.g., `"rust"`)
- `name` — Human-readable name (e.g., `"Rust"`)
- `priority` — Detection priority (lower = checked first, default 100)
- `source_extensions` — Set of file extensions (e.g., `{".rs"}`)
- `exclude_extensions` — Binary/generated extensions to skip
- `skip_directories` — Directories to ignore
- `marker_files` — List of `MarkerFile` instances for detection
- `ext_to_lang` — Extension-to-language mapping for symbol extraction
- `extract_symbols()` — Symbol extraction logic

Optional overrides:
- `detect_container()` — Container detection
- `collect_versions()` — Version extraction
- `get_component_technologies()` — Technology routing
- `collect_components()` — Component collection
- `collect_dimension()` — Dimension-specific specialist delegation

## Discovery

The `EcosystemRegistry` automatically discovers plugins at startup:

1. Scans `plugins/ecosystems/` for subdirectories (skips `_` and `.` prefixed)
2. Loads `__init__.py` via `importlib`
3. Finds classes that extend `EcosystemDefinition`
4. Instantiates and registers them

Plugins can be enabled/disabled and have their priority adjusted via the UI,
just like built-in ecosystems.

## Example

See `_example/ecosystem.py.example` for a minimal template.
