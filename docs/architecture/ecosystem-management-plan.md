# Ecosystem Management — Enable/Disable, Priority, Plugin Discovery

> **Status**: IMPLEMENTED | **Predecessor**: Collector Delegation Refactoring (completed)

---

## Context

Nach dem Collector-Delegation-Refactoring (57+ Specialists, 4 Ecosystems) wurde die Moeglichkeit implementiert, Ecosystems ueber die UI zu verwalten. Config-Persistence, Backend-API, Frontend-Controls und Plugin-Discovery sind vollstaendig umgesetzt.

**Ziel:** User/Admin kann Ecosystems per UI aktivieren/deaktivieren, Prioritaeten aendern, und Custom-Ecosystems als Plugins laden. Kein neuer Admin-Bereich noetig — die bestehende Collectors-Page wird erweitert.

**Kernidee:** `EcosystemRegistry.detect()` filtert disabled Ecosystems raus. Da alle 14+ Collectors `registry.detect()` aufrufen, propagiert sich die Aenderung automatisch — null Collector-Code-Aenderungen.

---

## Phase 1: Config Persistence + Registry Integration

### 1a. Neue Datei `ecosystem_config.py`

**Datei:** `src/aicodegencrew/shared/ecosystems/ecosystem_config.py`

Pattern von `collectors/collector_config.py` uebernehmen:

```python
def load_ecosystem_config(config_dir: Path) -> dict[str, dict]:
    """Load {eco_id: {enabled: bool, priority: int}}. Default: all enabled."""

def save_ecosystem_config(config_dir: Path, config: dict) -> None:
    """Persist to config/ecosystems_config.json."""

def toggle_ecosystem(config_dir: Path, eco_id: str, enabled: bool) -> dict:
    """Toggle single ecosystem, return updated entry."""

def update_priority(config_dir: Path, eco_id: str, priority: int) -> dict:
    """Update ecosystem priority, return updated entry."""
```

Config-Format (`config/ecosystems_config.json`):
```json
{
  "java_jvm": {"enabled": true, "priority": 10},
  "javascript_typescript": {"enabled": true, "priority": 20},
  "c_cpp": {"enabled": true, "priority": 30},
  "python": {"enabled": true, "priority": 40}
}
```

Default: alle `enabled: true`, Priority aus dem Ecosystem-Code.

### 1b. `EcosystemRegistry` erweitern

**Datei:** `src/aicodegencrew/shared/ecosystems/registry.py`

- Constructor laedt Config via `_load_config()`
- `detect()` filtert `_disabled_ids` raus
- `all_ecosystems` nutzt Priority-Overrides beim Sortieren
- Neue Methode `register(eco)` fuer Plugin-Registrierung

```python
class EcosystemRegistry:
    def __init__(self):
        self._ecosystems = []
        self._disabled_ids: set[str] = set()
        self._priority_overrides: dict[str, int] = {}
        self._register_builtins()
        self._load_config()

    def _load_config(self):
        config_dir = Path(os.getenv("AICODEGENCREW_ROOT", ".")) / "config"
        config = load_ecosystem_config(config_dir)
        for eco_id, entry in config.items():
            if not entry.get("enabled", True):
                self._disabled_ids.add(eco_id)
            if "priority" in entry:
                self._priority_overrides[eco_id] = entry["priority"]

    def detect(self, repo_path):
        active = [
            eco for eco in self._ecosystems
            if eco.id not in self._disabled_ids and eco.detect(repo_path)
        ]
        return sorted(active, key=lambda e: self._priority_overrides.get(e.id, e.priority))
```

### 1c. Export in `__init__.py`

**Datei:** `src/aicodegencrew/shared/ecosystems/__init__.py` — export `load_ecosystem_config`, `toggle_ecosystem`, `update_priority`

---

## Phase 2: Backend API Endpoints

### 2a. Neue Endpoints auf `/api/collectors`

**Datei:** `ui/backend/routers/collectors.py`

| Methode | Endpoint | Funktion |
|---------|----------|----------|
| `PUT` | `/api/collectors/ecosystems/{eco_id}/toggle` | Enable/Disable |
| `PUT` | `/api/collectors/ecosystems/{eco_id}/priority` | Priority aendern |

### 2b. Service-Funktionen

**Datei:** `ui/backend/services/collector_service.py`

```python
def toggle_ecosystem_state(eco_id: str, enabled: bool) -> EcosystemInfo:
    """Toggle ecosystem, persist config, return updated info."""

def update_ecosystem_priority(eco_id: str, priority: int) -> EcosystemInfo:
    """Update priority, persist config, return updated info."""
```

`list_ecosystems()` erweitern: `enabled`-Status aus Config lesen und in Response einbauen.

### 2c. Schema-Updates

**Datei:** `ui/backend/schemas.py`

```python
class EcosystemInfo(BaseModel):
    # ... bestehende Felder ...
    enabled: bool = True              # NEU

class EcosystemToggleRequest(BaseModel):
    enabled: bool

class EcosystemPriorityRequest(BaseModel):
    priority: int  # 1-999
```

---

## Phase 3: Frontend — Ecosystem Controls auf Collectors Page

### 3a. API Service erweitern

**Datei:** `ui/frontend/src/app/services/api.service.ts`

```typescript
toggleEcosystem(id: string, enabled: boolean): Observable<EcosystemInfo>
updateEcosystemPriority(id: string, priority: number): Observable<EcosystemInfo>
```

`EcosystemInfo` Interface: `enabled: boolean` hinzufuegen.

### 3b. Collectors Component erweitern

**Datei:** `ui/frontend/src/app/pages/collectors/collectors.component.ts`

**Ecosystem Tab Header:** Disabled-Ecosystems bekommen grauen Tab-Label + "disabled" Badge statt "active" Badge.

**Eco Status Bar erweitern:** Neben "Detected"/"Not detected" Chip:
- `mat-slide-toggle` fuer Enable/Disable (wie bei Collectors)
- Priority-Anzeige als editierbares Feld mit Save-Button

**Coverage Matrix:** Disabled-Ecosystems Spalte ausgegraut mit "disabled" Overlay.

**Neue Methoden:**
- `onEcoToggle(eco, enabled)` → API call + Snackbar
- `onPriorityChange(eco, priority)` → API call + Snackbar

---

## Phase 4: Plugin Discovery

### 4a. Plugin-Verzeichnis + Discovery

**Datei:** `src/aicodegencrew/shared/ecosystems/registry.py`

Neue Methode `_discover_plugins()`:
- Scannt `plugins/ecosystems/` nach Unterverzeichnissen mit `__init__.py`
- Importiert per `importlib.util.spec_from_file_location`
- Sucht Klassen die `EcosystemDefinition` erben
- Instanziiert und registriert

Wird nach `_register_builtins()` aufgerufen.

### 4b. Plugin Template

**Datei:** `plugins/ecosystems/README.md` (neu)

Dokumentiert den Vertrag:
```
plugins/ecosystems/
    rust/
        __init__.py          # class RustEcosystem(EcosystemDefinition): ...
        test_collector.py    # Optional: specialists
        dependency_collector.py
```

---

## Dateien-Uebersicht

| Datei | Aenderung |
|-------|-----------|
| `src/aicodegencrew/shared/ecosystems/ecosystem_config.py` | **NEU** — Config Load/Save/Toggle |
| `src/aicodegencrew/shared/ecosystems/registry.py` | Disabled-Filter, Priority-Overrides, Plugin-Discovery |
| `src/aicodegencrew/shared/ecosystems/__init__.py` | Neue Exports |
| `ui/backend/routers/collectors.py` | 2 neue Endpoints (toggle, priority) |
| `ui/backend/services/collector_service.py` | 2 neue Service-Funktionen, `list_ecosystems()` erweitert |
| `ui/backend/schemas.py` | `enabled` auf EcosystemInfo, 2 neue Request-Schemas |
| `ui/frontend/src/app/services/api.service.ts` | 2 neue Methoden, Interface-Update |
| `ui/frontend/src/app/pages/collectors/collectors.component.ts` | Toggle + Priority Controls in Ecosystem-Tabs |
| `plugins/ecosystems/README.md` | **NEU** — Plugin-Vertrag Dokumentation |

---

## Verifikation

1. `python -m pytest tests/ -x` — 665+ Tests gruen
2. Backend: `GET /api/collectors/ecosystems` zeigt `enabled` Feld
3. UI: Ecosystem Tab zeigt Toggle + Priority
4. Toggle-Test: Ecosystem disablen → `detect()` gibt es nicht mehr zurueck
5. Priority-Test: Priority aendern → Sortierung in `detect()` aendert sich
6. Plugin-Test: `plugins/ecosystems/test_eco/` anlegen → erscheint in Liste
7. Angular Build: `npx ng build --configuration=production` ohne Fehler

---

(c) 2026 Aymen Mastouri. All rights reserved.
