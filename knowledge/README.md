# Knowledge Base

This directory contains shared knowledge sources for all CrewAI phases.

> **Architecture Reference:** [AI_SDLC_ARCHITECTURE.md](../AI_SDLC_ARCHITECTURE.md)
>
> **Diagrams Reference:** [docs/diagrams/](../docs/diagrams/)

---

## 1. Overview

| Phase | Operation | Output |
|-------|-----------|--------|
| 0 | Indexing | `.cache/.chroma` (ChromaDB) |
| 1 | Architecture Facts | `knowledge/architecture/architecture_facts.json` |
| 2 | Architecture Synthesis | `knowledge/architecture/` (md, html, adr) |
| 3 | Review | PLANNED |
| 4 | Development | `knowledge/development/` |

---

## 2. Directory Structure

```
knowledge/
    README.md
    user_preference.txt

    analysis/

    architecture/
        architecture_facts.json
        evidence_map.json
        adr/
            ADR-001-*.md
        confluence/
            *.md
        html/
            report.html
        quality/
            quality-report.html

    development/
```

---

## 3. Custom Knowledge Sources

Place additional context files in this directory:

| File | Purpose |
|------|---------|
| `project-guidelines.txt` | Coding standards and conventions |
| `architecture-decisions.txt` | Architecture Decision Records |
| `api-documentation.txt` | API specifications |
| `user_preference.txt` | User-specific preferences |

These files are automatically loaded as CrewAI Knowledge Sources and made available to all agents.

---

## 4. Phase Context Flow

Each phase follows this pattern:

1. Read context from previous phase outputs
2. Execute phase-specific operations
3. Write results to phase output directory
4. Subsequent phases consume these outputs

| Phase | Input | Output |
|-------|-------|--------|
| 1 | Repository files | `architecture/architecture_facts.json` |
| 2 | `architecture_facts.json` | `architecture/` (md, html, adr) |
| 3 | All architecture outputs | Review report (PLANNED) |
| 4 | Approved architecture | `development/` |

---

## 5. File Formats

| Format | Usage |
|--------|-------|
| `.json` | Structured evidence data (analyze.json) |
| `.md` | Documentation outputs (ADR, Confluence) |
| `.html` | Reports (arc42, quality) |
| `.txt` | Custom knowledge sources |
