# AICodeGenCrew - Delivery Guide

**Schritt-fur-Schritt Anleitung: Wie bereite ich das Lieferpaket vor?**

---

## Was lieferst du?

Eine ZIP-Datei mit allem was der Endbenutzer braucht. **Kein Source Code!**

**Datei:** `aicodegencrew-v0.1.0.zip` (486 KB)

**Inhalt:**
```
aicodegencrew-v0.1.0/
├── aicodegencrew-0.1.0-py3-none-any.whl   # Das Tool (installierbar)
├── .env.example                             # Konfig-Vorlage
├── docker-compose.yml                       # Docker Setup
├── config/
│   └── phases_config.yaml                   # Phase-Konfiguration
├── USER_GUIDE.md                            # Bedienungsanleitung (Markdown)
├── USER_GUIDE.pdf                           # Bedienungsanleitung (PDF)
├── CHANGELOG.md                             # Was ist neu (automatisch aus Git)
├── install.bat                              # Windows-Installer
├── install.sh                               # Linux-Installer
├── uninstall.bat                            # Windows-Deinstaller
└── uninstall.sh                             # Linux-Deinstaller
```

---

## Variante A: Automatisch (Empfohlen)

### Schritt 1: Terminal offnen

```
cd c:\projects\aicodegencrew
```

### Schritt 2: Release-Script ausfuhren

**Nur bauen (keine Versionsanderung):**
```
python scripts/build_release.py
```

**Version erhohen + bauen (empfohlen):**
```
python scripts/build_release.py --bump patch
```

**Version erhohen + Git-Tag + bauen:**
```
python scripts/build_release.py --bump patch --tag
```

**Version erhohen + Git-Tag + Docker-Image + bauen:**
```
python scripts/build_release.py --bump patch --tag --docker
```

### Was passiert bei `--bump`?

Das Script macht **alles automatisch**:

| Schritt | Datei | Was passiert |
|---------|-------|-------------|
| 1 | `pyproject.toml` | Version wird erhoht (z.B. `0.1.0` → `0.1.1`) |
| 2 | `CHANGELOG.md` | Neuer Eintrag mit Git-Commit-Messages seit letztem Tag |
| 3 | `docs/DELIVERY_GUIDE.md` | Alle Versionsreferenzen aktualisiert |
| 4 | `docs/USER_GUIDE.md` | Alle Versionsreferenzen aktualisiert |
| 5 | `dist/release/` | Wheel + alle 8 Release-Dateien erstellt |

### Was passiert bei `--tag`?

| Schritt | Was passiert |
|---------|-------------|
| 1 | `git add` aller geanderten Dateien |
| 2 | `git commit -m "release: v0.1.1"` |
| 3 | `git tag -a v0.1.1 -m "Release 0.1.1"` |

**Danach zum Server pushen:**
```
git push origin v0.1.1
git push
```

### Versionsarten (`--bump`)

| Befehl | Vorher | Nachher | Wann verwenden? |
|--------|--------|---------|-----------------|
| `--bump patch` | 0.1.0 | 0.1.1 | Bugfixes, kleine Anderungen |
| `--bump minor` | 0.1.0 | 0.2.0 | Neue Features |
| `--bump major` | 0.1.0 | 1.0.0 | Breaking Changes |

### Schritt 3: Ergebnis

Das Script erstellt automatisch:

1. **Release-Ordner** `dist/release/` mit allen Dateien
2. **ZIP-Datei** `dist/aicodegencrew-v0.1.0.zip` (fertig zum Versenden!)

```
dist/
├── aicodegencrew-v0.1.0.zip         ← FERTIGE LIEFERUNG (486 KB)
└── release/
    ├── aicodegencrew-0.1.0-py3-none-any.whl
    ├── .env.example
    ├── docker-compose.yml
    ├── config/phases_config.yaml
    ├── USER_GUIDE.md
    ├── USER_GUIDE.pdf               ← NEU! PDF-Version
    ├── CHANGELOG.md
    ├── install.bat
    └── install.sh
```

**ZIP-Struktur (entpackt):**
```
aicodegencrew-v0.1.0/                ← Korrekter Root-Ordner
├── aicodegencrew-0.1.0-py3-none-any.whl
├── .env.example
├── docker-compose.yml
├── config/phases_config.yaml
├── USER_GUIDE.md
├── USER_GUIDE.pdf
├── CHANGELOG.md
├── install.bat
└── install.sh
```

### Schritt 4: ZIP versenden

Das ZIP ist fertig! Einfach versenden:

```bash
# Option 1: Per Teams/SharePoint hochladen
# Option 2: Per E-Mail (486 KB, passt immer)
# Option 3: Auf Netzlaufwerk kopieren
```

Die Datei `dist/aicodegencrew-v0.1.0.zip` an den Entwickler schicken

---

## Variante B: Manuell (falls Script nicht funktioniert)

### Schritt 1: Wheel bauen

```
cd c:\projects\aicodegencrew
pip install build
python -m build --wheel
```

Ergebnis: `dist/aicodegencrew-0.1.0-py3-none-any.whl`

### Schritt 2: Lieferordner zusammenstellen

Erstelle einen neuen Ordner `aicodegencrew-v0.1.0/` und kopiere diese Dateien hinein:

| Von (Quelle) | Nach (Lieferordner) |
|---------------|---------------------|
| `dist/aicodegencrew-0.1.0-py3-none-any.whl` | `aicodegencrew-v0.1.0/` |
| `.env.example` | `aicodegencrew-v0.1.0/` |
| `docker-compose.yml` | `aicodegencrew-v0.1.0/` |
| `config/phases_config.yaml` | `aicodegencrew-v0.1.0/config/` |
| `docs/USER_GUIDE.md` | `aicodegencrew-v0.1.0/USER_GUIDE.md` |
| `CHANGELOG.md` | `aicodegencrew-v0.1.0/` |

**WICHTIG:** Der Root-Ordner im ZIP muss `aicodegencrew-v0.1.0/` heißen!

### Schritt 3: ZIP erstellen und versenden

**PowerShell (Windows):**
```powershell
# Von AUSSEN zippen (nicht im Ordner drin!)
Compress-Archive -Path aicodegencrew-v0.1.0 -DestinationPath aicodegencrew-v0.1.0.zip
```

**Linux/Mac:**
```bash
zip -r aicodegencrew-v0.1.0.zip aicodegencrew-v0.1.0/
```

ZIP verschicken.

---

## Variante C: Docker Image (fur Kunden ohne Python)

### Schritt 1: Docker Image bauen

```
cd c:\projects\aicodegencrew
docker build -t aicodegencrew:0.1.0 -t aicodegencrew:latest .
```

### Schritt 2: Image als Datei exportieren

```
docker save -o dist/aicodegencrew-0.1.0.tar.gz aicodegencrew:0.1.0
```

### Schritt 3: Lieferordner (mit Docker)

Gleich wie Variante B, plus die `.tar.gz` Datei dazu.

### Schritt 4: Oder automatisch

```
python scripts/build_release.py --docker
```

Oder alles zusammen:
```
python scripts/build_release.py --bump patch --tag --docker
```

---

## Was schicke ich dem Entwickler?

### Minimal (Wheel):
1. `aicodegencrew-v0.1.0.zip` (enthalt alles aus Variante A/B)

### Mit Docker:
1. `aicodegencrew-v0.1.0.zip` (enthalt alles + Docker Image)

### Begleittext (Vorlage fur E-Mail/Teams):

```
Hallo [Name],

im Anhang das AICodeGenCrew Tool v0.1.0 zur Entwicklungsplanung.

Installation (5 Minuten):
1. ZIP entpacken
2. install.bat ausfuhren (oder: pip install aicodegencrew-0.1.0-py3-none-any.whl[parsers])
3. .env.example nach .env kopieren und anpassen:
   - PROJECT_PATH = Pfad zu deinem Repository
   - TASK_INPUT_DIR = Pfad zu deinem JIRA-Export-Ordner
4. Ollama starten: ollama serve

Benutzung:
   aicodegencrew --env .env plan

Ausfuhrliche Anleitung: siehe USER_GUIDE.md im ZIP.

Bei Fragen: [dein Kontakt]
```

---

## Checkliste vor Lieferung

- [ ] `python scripts/build_release.py` lauft ohne Fehler
- [ ] `dist/release/` enthalt alle Dateien (8 Stuck)
- [ ] `.whl` Datei ist vorhanden und > 100 KB
- [ ] `.env.example` enthalt KEINE echten API-Keys oder Passworter
- [ ] `USER_GUIDE.md` ist aktuell
- [ ] `CHANGELOG.md` enthalt die aktuellen Anderungen (automatisch aus Git)
- [ ] Kein Source Code im Lieferordner (keine `.py` Dateien!)
- [ ] Version in `pyproject.toml` ist korrekt

---

## Kompletter Release-Workflow (Schritt fur Schritt)

### Fur eine neue Version (z.B. 0.1.0 → 0.1.1):

```bash
# 1. Terminal offnen
cd c:\projects\aicodegencrew

# 2. Version erhohen + bauen + Git-Tag erstellen
python scripts/build_release.py --bump patch --tag

# 3. Was ist passiert?
#    - pyproject.toml:        version = "0.1.1"
#    - CHANGELOG.md:          ## [0.1.1] - 2026-02-09 (mit Git-Commits)
#    - DELIVERY_GUIDE.md:     Alle "0.1.0" durch "0.1.1" ersetzt
#    - USER_GUIDE.md:         Alle "0.1.0" durch "0.1.1" ersetzt
#    - dist/release/:         8 Dateien mit neuer Version
#    - Git:                   Commit "release: v0.1.1" + Tag v0.1.1

# 4. (Optional) Zum Git-Server pushen
git push origin v0.1.1
git push

# 5. ZIP erstellen und versenden
#    Rechtsklick auf dist/release/ -> ZIP -> aicodegencrew-v0.1.1.zip
```

### Fur eine neue Version MIT Docker:

```bash
python scripts/build_release.py --bump patch --tag --docker
# -> Macht alles oben + baut Docker Image + exportiert als .tar.gz
```

---

## Wo sitzt die Version?

Die Version steht an EINER Stelle: **`pyproject.toml` Zeile 3**

```toml
version = "0.1.0"
```

Das `--bump` Flag andert diese Stelle und propagiert die Anderung automatisch in:
- `CHANGELOG.md` (neuer Eintrag mit Git-Commit-Messages)
- `docs/DELIVERY_GUIDE.md` (alle Versionsreferenzen)
- `docs/USER_GUIDE.md` (alle Versionsreferenzen)

**Du musst NIE manuell die Version andern!** Immer das Script benutzen:

```bash
python scripts/build_release.py --bump patch          # Bugfix
python scripts/build_release.py --bump minor          # Neues Feature
python scripts/build_release.py --bump major          # Breaking Change
```

---

## CHANGELOG: Automatisch aus Git

Das `CHANGELOG.md` wird automatisch mit Git-Commit-Messages gefullt.

**Vorher:**
```markdown
## [0.1.0] - 2026-02-09
### Changed
- Fix Phase 4 upgrade validation + wire repo_path in CLI
- Add Upgrade Rules Engine for Phase 4 Development Planning
- ...
```

**Nach `--bump patch`:**
```markdown
## [0.1.1] - 2026-02-09
### Changed
- Alle neuen Commits seit v0.1.0 werden automatisch eingefugt
- ...

## [0.1.0] - 2026-02-09
### Changed
- (alter Eintrag bleibt erhalten)
```

**Gefiltert werden:**
- Merge-Commits (`Merge ...`)
- Release-Commits (`release: ...`)
- Auto-generierte Phase-Commits (`[aicodegencrew] phase0_indexing completed ...`)

---

## Architektur-Dokumente fur den Architekten exportieren

Phase 3 erzeugt C4-Diagramme und Arc42-Kapitel. Diese sind fur den Architekten/Entwickler relevant.

Nach Phase 3 werden die Dokumente automatisch in einen Export-Ordner kopiert.
**Default:** `./architecture-docs` im aktuellen Arbeitsverzeichnis.

Um den Export-Pfad zu andern, `DOCS_OUTPUT_DIR` in der `.env` setzen:

```env
# Default: ./architecture-docs (im gleichen Ordner wo du das Tool ausfuhrst)
# Oder: externer Pfad fur Shared Drive / Architekt
DOCS_OUTPUT_DIR=C:\work\my-project\architecture-docs
```

**Was wird exportiert (4 Formate pro Datei):**

```
C:\work\my-project\architecture-docs\
├── c4/                                    # C4 Diagramme
│   ├── c4-context.md                        # Markdown (Original)
│   ├── c4-context.confluence                # Confluence Wiki Markup
│   ├── c4-context.adoc                      # AsciiDoc (fur docToolchain)
│   ├── c4-context.html                      # HTML (im Browser offnen)
│   ├── c4-context.drawio                    # DrawIO Diagramm
│   └── ... (4 C4-Level x 4 Formate + DrawIO)
└── arc42/                                 # Arc42 Kapitel
    ├── 00-arc42-toc.confluence              # Inhaltsverzeichnis (arc42 Template)
    ├── 00-arc42-toc.adoc
    ├── 00-arc42-toc.html
    ├── 01-introduction.md + .confluence + .adoc + .html
    ├── ... (12 Kapitel x 4 Formate)
    └── 12-glossary.md + .confluence + .adoc + .html
```

**Confluence-Format:** `.confluence` Dateien direkt in den Confluence Wiki-Markup-Editor einfugen.

**AsciiDoc-Format:** `.adoc` Dateien mit docToolchain (`asciidoc2confluence.groovy`) nach Confluence hochladen.

**HTML-Format:** `.html` Dateien direkt im Browser offnen — standalone mit eingebettetem CSS.

**Sprache fur arc42 Inhaltsverzeichnis:**
```env
ARC42_LANGUAGE=de    # Deutsch (Default: en = Englisch)
```

**Was wird NICHT exportiert:**
- `architecture_facts.json` (intern, Phase 1)
- `analyzed_architecture.json` (intern, Phase 2)
- `analysis/` Ordner (intern, Phase 2)
- Checkpoint-Dateien (`.checkpoint_*.json`)

**Wo bleibt alles fur Testen?**
Im Projekt selbst unter `knowledge/architecture/` — da liegt alles (inklusive JSON).
`DOCS_OUTPUT_DIR` ist eine **Kopie** der Architekturdokumente, nicht ein Verschieben.

---

## Haufige Probleme

### "pip install build" schlagt fehl
```
python -m pip install --upgrade pip
pip install build
```

### "python -m build" schlagt fehl
```
# Virtuelle Umgebung aktivieren
.venv\Scripts\activate
pip install build
python -m build --wheel
```

### "docker build" schlagt fehl
- Docker Desktop muss laufen
- Internetverbindung fur pip install im Container nötig

### Entwickler meldet "TASK_INPUT_DIR not configured"
Er muss `TASK_INPUT_DIR` in seiner `.env` setzen:
```
TASK_INPUT_DIR=C:\sein\pfad\zu\jira\exports
```

### Version ist falsch nach manuellem Edit
Niemals `pyproject.toml` manuell andern! Immer das Script benutzen:
```
python scripts/build_release.py --bump patch
```

---

*Erstellt: 2026-02-09 | Version: 0.1.0*
