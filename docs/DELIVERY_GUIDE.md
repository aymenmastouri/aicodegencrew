# AICodeGenCrew - Delivery Guide

**Step-by-step instructions for preparing the delivery package.**

---

## What Do You Deliver?

A ZIP file containing everything the end user needs. **No source code included.**

**File:** `aicodegencrew-v0.1.0.zip`

**Two Variants:**

| Variant | Contents | Code Protection | Size |
|---------|----------|-----------------|------|
| **Nuitka (Default)** | Binary (.exe/.bin) | Cannot be decompiled | ~50-100 MB |
| Wheel | Wheel (.whl) | Source code readable | ~500 KB |

**Default Contents (Nuitka - recommended):**
```
aicodegencrew-v0.1.0/
├── aicodegencrew.exe (Win) / aicodegencrew (Linux/Mac)  # Protected binary
├── .env.example                             # Configuration template
├── docker-compose.yml                       # Docker setup
├── config/
│   └── phases_config.yaml                   # Phase configuration
├── USER_GUIDE.md                            # User manual (Markdown)
├── USER_GUIDE.pdf                           # User manual (PDF)
├── CHANGELOG.md                             # Release notes (auto-generated from Git)
├── install.bat                              # Windows installer
├── install.sh                               # Linux installer
├── uninstall.bat                            # Windows uninstaller
└── uninstall.sh                             # Linux uninstaller
```

**Alternative Contents (Wheel - internal use only):**
```
aicodegencrew-v0.1.0/
├── aicodegencrew-0.1.0-py3-none-any.whl   # The tool (source code readable)
├── .env.example
├── docker-compose.yml
├── config/
│   └── phases_config.yaml
├── USER_GUIDE.md
├── USER_GUIDE.pdf
├── CHANGELOG.md
├── install.bat
├── install.sh
├── uninstall.bat
└── uninstall.sh
```

---

## Option A: Automated (Recommended)

### Step 1: Open Terminal

```
cd c:\projects\aicodegencrew
```

### Step 2: Run Release Script

**Build protected binary (default, recommended):**
```
python scripts/build_release.py
```

**Bump version + build (recommended):**
```
python scripts/build_release.py --bump patch
```

**Bump version + Git tag + build:**
```
python scripts/build_release.py --bump patch --tag
```

**Bump version + Git tag + Docker image + build:**
```
python scripts/build_release.py --bump patch --tag --docker
```

**Wheel package (internal use only, source code readable):**
```
python scripts/build_release.py --bump patch --wheel
```

### What Happens with `--bump`?

The script automates everything:

| Step | File | Action |
|------|------|--------|
| 1 | `pyproject.toml` | Version incremented (e.g., `0.1.0` to `0.1.1`) |
| 2 | `CHANGELOG.md` | New entry with Git commit messages since last tag |
| 3 | `docs/DELIVERY_GUIDE.md` | All version references updated |
| 4 | `docs/USER_GUIDE.md` | All version references updated |
| 5 | `dist/release/` | Binary + all release files created |

### What Happens with `--tag`?

| Step | Action |
|------|--------|
| 1 | `git add` of all changed files |
| 2 | `git commit -m "release: v0.1.1"` |
| 3 | `git tag -a v0.1.1 -m "Release 0.1.1"` |

**Then push to server:**
```
git push origin v0.1.1
git push
```

### Version Types (`--bump`)

| Command | Before | After | When to Use |
|---------|--------|-------|-------------|
| `--bump patch` | 0.1.0 | 0.1.1 | Bug fixes, minor changes |
| `--bump minor` | 0.1.0 | 0.2.0 | New features |
| `--bump major` | 0.1.0 | 1.0.0 | Breaking changes |

### Step 3: Result

The script automatically creates:

1. **Release folder** `dist/release/` with all files
2. **ZIP file** `dist/aicodegencrew-v0.1.0.zip` (ready to send)

```
dist/
├── aicodegencrew-v0.1.0.zip         <- FINAL DELIVERY
└── release/
    ├── aicodegencrew.exe / aicodegencrew  <- Protected binary (platform-specific)
    ├── .env.example
    ├── docker-compose.yml
    ├── config/phases_config.yaml
    ├── USER_GUIDE.md
    ├── USER_GUIDE.pdf
    ├── CHANGELOG.md
    ├── install.bat
    └── install.sh
```

**ZIP structure (extracted):**
```
aicodegencrew-v0.1.0/                <- Correct root folder
├── aicodegencrew.exe / aicodegencrew  <- Platform-specific binary
├── .env.example
├── docker-compose.yml
├── config/phases_config.yaml
├── USER_GUIDE.md
├── USER_GUIDE.pdf
├── CHANGELOG.md
├── install.bat
└── install.sh
```

### Step 4: Send ZIP

The ZIP is ready. Send it via:

```bash
# Option 1: Upload to Teams/SharePoint
# Option 2: Email
# Option 3: Copy to network drive
```

Send `dist/aicodegencrew-v0.1.0.zip` to the developer.

---

## Code Protection: Nuitka vs Wheel

**Why Nuitka is the default:**
- The `.whl` (Wheel) contains readable Python source code
- Anyone can extract and read/copy the code
- **Nuitka compiles Python to native machine code** - cannot be decompiled

### Comparison

| Method | Source Code Visible | Reverse Engineering | Recommendation |
|--------|---------------------|---------------------|----------------|
| **Nuitka (.exe)** | No | Extremely difficult | Default for all deliveries |
| Wheel (.whl) | Yes, easily | Trivial (unzip) | Internal development only |

### Nuitka Protection Features

- **Native Machine Code** - No Python bytecode, no `.pyc` files
- **Standalone** - No Python installation required on user machine
- **Obfuscated** - Variable names and structure not recognizable
- **Anti-Decompile** - Standard tools like `uncompyle6` do not work

### Differences

| Aspect | Nuitka (Default) | Wheel |
|--------|------------------|-------|
| File | `.exe` (~50-100 MB) | `.whl` (486 KB) |
| Python required | No (standalone) | Yes |
| Source code | Not extractable | Readable |
| Installation | Directly executable | `pip install ...` |
| Reverse engineering | Extremely difficult | Easy |
| Build time | 5-15 minutes | 30 seconds |

**Note:** First Nuitka build takes 5-15 minutes (compiles to C, then to machine code). Subsequent builds are faster due to caching.

---

## Option B: Manual (if script fails)

### Step 1: Build with Nuitka

```
cd c:\projects\aicodegencrew
pip install nuitka ordered-set zstandard
python -m nuitka --standalone --onefile src/aicodegencrew/main.py
```

Result: `aicodegencrew.exe` (Windows) or `aicodegencrew` (Linux/Mac) in `dist/nuitka/`

### Step 2: Assemble Delivery Folder

Create a new folder `aicodegencrew-v0.1.0/` and copy these files:

| From (Source) | To (Delivery Folder) |
|---------------|----------------------|
| `dist/nuitka/aicodegencrew[.exe]` | `aicodegencrew-v0.1.0/` |
| `.env.example` | `aicodegencrew-v0.1.0/` |
| `docker-compose.yml` | `aicodegencrew-v0.1.0/` |
| `config/phases_config.yaml` | `aicodegencrew-v0.1.0/config/` |
| `docs/USER_GUIDE.md` | `aicodegencrew-v0.1.0/USER_GUIDE.md` |
| `CHANGELOG.md` | `aicodegencrew-v0.1.0/` |

**IMPORTANT:** The root folder in ZIP must be named `aicodegencrew-v0.1.0/`

### Step 3: Create ZIP and Send

**PowerShell (Windows):**
```powershell
# Zip from OUTSIDE (not inside the folder)
Compress-Archive -Path aicodegencrew-v0.1.0 -DestinationPath aicodegencrew-v0.1.0.zip
```

**Linux/Mac:**
```bash
zip -r aicodegencrew-v0.1.0.zip aicodegencrew-v0.1.0/
```

Send the ZIP.

---

## Option C: Docker Image (for customers without Python)

### Step 1: Build Docker Image

```
cd c:\projects\aicodegencrew
docker build -t aicodegencrew:0.1.0 -t aicodegencrew:latest .
```

### Step 2: Export Image as File

```
docker save -o dist/aicodegencrew-0.1.0.tar.gz aicodegencrew:0.1.0
```

### Step 3: Delivery Folder (with Docker)

Same as Option B, plus the `.tar.gz` file.

### Step 4: Or Automated

```
python scripts/build_release.py --docker
```

Or all together:
```
python scripts/build_release.py --bump patch --tag --docker
```

---

## Option D: Wheel Package (Internal Use Only)

Use this only for internal development or when the recipient needs to inspect/modify the source code.

### When to Use Wheel

- Internal team members who need source access
- Development and debugging purposes
- Quick iteration during development

### Build Wheel

```bash
python scripts/build_release.py --wheel
```

Or with versioning:
```bash
python scripts/build_release.py --bump patch --wheel
```

### Result

```
dist/
├── aicodegencrew-v0.1.0.zip         <- DELIVERY (contains .whl)
└── release/
    ├── aicodegencrew-0.1.0-py3-none-any.whl  <- Source code readable
    ├── .env.example
    ├── docker-compose.yml
    ├── config/phases_config.yaml
    ├── USER_GUIDE.md
    ├── USER_GUIDE.pdf
    ├── CHANGELOG.md
    ├── install.bat
    └── install.sh
```

---

## What to Send to the Developer?

### Default (Nuitka) - for all external deliveries:
1. `aicodegencrew-v0.1.0.zip` (contains protected .exe, code not readable)

### Wheel - internal use only:
1. `aicodegencrew-v0.1.0.zip` (contains .whl, source code readable)

### With Docker:
1. `aicodegencrew-v0.1.0.zip` (contains everything + Docker image)

### Cover Letter Template (for Email/Teams):

**For Nuitka Delivery (default):**
```
Hello [Name],

Please find attached the AICodeGenCrew tool v0.1.0 for development planning.

Installation (2 minutes):
1. Extract ZIP
2. Windows: Run install.bat (copies binary to Program Files)
   Linux/Mac: Run install.sh (copies binary to /usr/local/bin)
   Alternative: Run binary directly from the folder
3. Copy .env.example to .env and configure:
   - PROJECT_PATH = Path to your repository
   - TASK_INPUT_DIR = Path to your JIRA export folder
4. Start Ollama: ollama serve

Usage:
   aicodegencrew --env .env plan

Note: No Python installation required.

Detailed instructions: see USER_GUIDE.md in ZIP.

Questions: [your contact]
```

**For Wheel Delivery (internal only):**
```
Hello [Name],

Please find attached the AICodeGenCrew tool v0.1.0 for development planning.

Installation (5 minutes):
1. Extract ZIP
2. Run install.bat (or: pip install aicodegencrew-0.1.0-py3-none-any.whl[parsers])
3. Copy .env.example to .env and configure:
   - PROJECT_PATH = Path to your repository
   - TASK_INPUT_DIR = Path to your JIRA export folder
4. Start Ollama: ollama serve

Usage:
   aicodegencrew --env .env plan

Detailed instructions: see USER_GUIDE.md in ZIP.

Questions: [your contact]
```

---

## Pre-Delivery Checklist

### Default (Nuitka):
- [ ] `python scripts/build_release.py` runs without errors
- [ ] `dist/release/` contains binary (`.exe` on Windows, no extension on Linux/Mac)
- [ ] Binary file exists and is larger than 10 MB
- [ ] `.env.example` contains NO real API keys or passwords
- [ ] `USER_GUIDE.md` is current
- [ ] No source code in delivery folder (no `.py`, `.whl` files)
- [ ] Version in `pyproject.toml` is correct

### Wheel (internal only):
- [ ] `python scripts/build_release.py --wheel` runs without errors
- [ ] `dist/release/` contains all files (8 items)
- [ ] `.whl` file exists and is larger than 100 KB
- [ ] `.env.example` contains NO real API keys or passwords
- [ ] `USER_GUIDE.md` is current
- [ ] `CHANGELOG.md` contains current changes (auto-generated from Git)
- [ ] No source code in delivery folder (no `.py` files)
- [ ] Version in `pyproject.toml` is correct

---

## Complete Release Workflow (Step by Step)

### For a New Version (e.g., 0.1.0 to 0.1.1):

```bash
# 1. Open terminal
cd c:\projects\aicodegencrew

# 2. Bump version + build + create Git tag
python scripts/build_release.py --bump patch --tag

# 3. What happened?
#    - pyproject.toml:        version = "0.1.1"
#    - CHANGELOG.md:          ## [0.1.1] - 2026-02-09 (with Git commits)
#    - DELIVERY_GUIDE.md:     All "0.1.0" replaced with "0.1.1"
#    - USER_GUIDE.md:         All "0.1.0" replaced with "0.1.1"
#    - dist/release/:         Protected binary with new version
#    - Git:                   Commit "release: v0.1.1" + Tag v0.1.1

# 4. (Optional) Push to Git server
git push origin v0.1.1
git push

# 5. Send ZIP
#    -> dist/aicodegencrew-v0.1.1.zip (auto-created)
```

### For Wheel Delivery (internal only):

```bash
# With source code visible (internal use)
python scripts/build_release.py --bump patch --wheel

# Or with Git tag:
python scripts/build_release.py --bump patch --tag --wheel
```

### For a New Version WITH Docker:

```bash
python scripts/build_release.py --bump patch --tag --docker
# -> Does everything above + builds Docker image + exports as .tar.gz
```

---

## Where Is the Version?

The version is in ONE place: **`pyproject.toml` line 3**

```toml
version = "0.1.0"
```

The `--bump` flag changes this location and automatically propagates the change to:
- `CHANGELOG.md` (new entry with Git commit messages)
- `docs/DELIVERY_GUIDE.md` (all version references)
- `docs/USER_GUIDE.md` (all version references)

**Never manually change the version.** Always use the script:

```bash
python scripts/build_release.py --bump patch          # Bug fix
python scripts/build_release.py --bump minor          # New feature
python scripts/build_release.py --bump major          # Breaking change
```

---

## CHANGELOG: Auto-Generated from Git

The `CHANGELOG.md` is automatically filled with Git commit messages.

**Before:**
```markdown
## [0.1.0] - 2026-02-09
### Changed
- Fix Phase 4 upgrade validation + wire repo_path in CLI
- Add Upgrade Rules Engine for Phase 4 Development Planning
- ...
```

**After `--bump patch`:**
```markdown
## [0.1.1] - 2026-02-09
### Changed
- All new commits since v0.1.0 are automatically inserted
- ...

## [0.1.0] - 2026-02-09
### Changed
- (old entry preserved)
```

**Filtered out:**
- Merge commits (`Merge ...`)
- Release commits (`release: ...`)
- Auto-generated phase commits (`[aicodegencrew] phase0_indexing completed ...`)

---

## Exporting Architecture Documents for the Architect

Phase 3 creates C4 diagrams and Arc42 chapters. These are relevant for the architect/developer.

After Phase 3, documents are automatically copied to an export folder.
**Default:** `./architecture-docs` in the current working directory.

To change the export path, set `DOCS_OUTPUT_DIR` in `.env`:

```env
# Default: ./architecture-docs (in the same folder where you run the tool)
# Or: external path for shared drive / architect
DOCS_OUTPUT_DIR=C:\work\my-project\architecture-docs
```

**What is exported (4 formats per file):**

```
C:\work\my-project\architecture-docs\
├── c4/                                    # C4 Diagrams
│   ├── c4-context.md                        # Markdown (Original)
│   ├── c4-context.confluence                # Confluence Wiki Markup
│   ├── c4-context.adoc                      # AsciiDoc (for docToolchain)
│   ├── c4-context.html                      # HTML (open in browser)
│   ├── c4-context.drawio                    # DrawIO Diagram
│   └── ... (4 C4 levels x 4 formats + DrawIO)
└── arc42/                                 # Arc42 Chapters
    ├── 00-arc42-toc.confluence              # Table of Contents (arc42 template)
    ├── 00-arc42-toc.adoc
    ├── 00-arc42-toc.html
    ├── 01-introduction.md + .confluence + .adoc + .html
    ├── ... (12 chapters x 4 formats)
    └── 12-glossary.md + .confluence + .adoc + .html
```

**Confluence format:** Paste `.confluence` files directly into Confluence Wiki Markup editor.

**AsciiDoc format:** Upload `.adoc` files with docToolchain (`asciidoc2confluence.groovy`) to Confluence.

**HTML format:** Open `.html` files directly in browser - standalone with embedded CSS.

**Language for arc42 table of contents:**
```env
ARC42_LANGUAGE=de    # German (Default: en = English)
```

**What is NOT exported:**
- `architecture_facts.json` (internal, Phase 1)
- `analyzed_architecture.json` (internal, Phase 2)
- `analysis/` folder (internal, Phase 2)
- Checkpoint files (`.checkpoint_*.json`)

**Where does everything stay for testing?**
In the project under `knowledge/architecture/` - everything is there (including JSON).
`DOCS_OUTPUT_DIR` is a **copy** of the architecture documents, not a move.

---

## Common Problems

### "pip install build" fails
```
python -m pip install --upgrade pip
pip install build
```

### "python -m build" fails
```
# Activate virtual environment
.venv\Scripts\activate
pip install build
python -m build --wheel
```

### "docker build" fails
- Docker Desktop must be running
- Internet connection required for pip install in container

### Developer reports "TASK_INPUT_DIR not configured"
They must set `TASK_INPUT_DIR` in their `.env`:
```
TASK_INPUT_DIR=C:\their\path\to\jira\exports
```

### Version is wrong after manual edit
Never manually edit `pyproject.toml`. Always use the script:
```
python scripts/build_release.py --bump patch
```

### Nuitka build fails
```bash
# Install Nuitka dependencies
pip install nuitka ordered-set zstandard

# On Windows, you may need Visual Studio Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

---

*Created: 2026-02-09 | Version: 0.1.0*
