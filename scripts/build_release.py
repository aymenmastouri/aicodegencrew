#!/usr/bin/env python3
"""
Build Release Package for AICodeGenCrew.

Creates a distribution-ready package with:
  - Protected native binary (Nuitka) - default, cannot be decompiled
  - Python wheel (.whl) - optional, for internal use only
  - Docker image (.tar.gz) - optional
  - Configuration template (.env.example)
  - User documentation (USER_GUIDE.md + USER_GUIDE.pdf)
  - phases_config.yaml
  - docker-compose.yml

Usage:
    python scripts/build_release.py                              # Build protected binary (default)
    python scripts/build_release.py --wheel                      # Build wheel (internal use only)
    python scripts/build_release.py --bump patch                 # 0.1.0 -> 0.1.1
    python scripts/build_release.py --bump minor                 # 0.1.0 -> 0.2.0
    python scripts/build_release.py --bump major                 # 0.1.0 -> 1.0.0
    python scripts/build_release.py --bump patch --tag           # + git tag v0.1.1
    python scripts/build_release.py --bump patch --tag --docker  # + Docker image
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
RELEASE = DIST / "release"
SRC = ROOT / "src" / "aicodegencrew"
NUITKA_DIST = DIST / "nuitka"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run command and exit on failure."""
    print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT), **kwargs)
    if result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def get_version() -> str:
    """Extract version from pyproject.toml."""
    toml = PYPROJECT.read_text(encoding="utf-8")
    for line in toml.splitlines():
        if line.strip().startswith("version"):
            return line.split("=")[1].strip().strip('"').strip("'")
    return "0.0.0"


def bump_version(current: str, part: str) -> str:
    """Bump version: major, minor, or patch."""
    parts = current.split(".")
    if len(parts) != 3:
        print(f"ERROR: Invalid version format: {current}")
        sys.exit(1)

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    elif part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"ERROR: Invalid bump type: {part}. Use: major, minor, patch")
        sys.exit(1)


def set_version(new_version: str):
    """Update version in pyproject.toml."""
    content = PYPROJECT.read_text(encoding="utf-8")
    updated = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"  Updated pyproject.toml: version = \"{new_version}\"")


def get_git_log_since_last_tag() -> list[str]:
    """Get commit messages since the last git tag (or all if no tags)."""
    # Find the latest tag
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    last_tag = result.stdout.strip() if result.returncode == 0 else ""

    # Get commits since that tag (or all commits if no tag)
    if last_tag:
        log_range = f"{last_tag}..HEAD"
    else:
        log_range = "HEAD"

    result = subprocess.run(
        ["git", "log", log_range, "--pretty=format:%s"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    # Filter out noise: merge commits, release commits, auto-generated phase commits
    commits = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Merge "):
            continue
        if line.startswith("release:"):
            continue
        if line.startswith("[aicodegencrew]") and "completed" in line:
            continue
        commits.append(line)

    return commits


def update_changelog(new_version: str):
    """Add new version header to CHANGELOG.md with git commit messages."""
    if not CHANGELOG.exists():
        return

    content = CHANGELOG.read_text(encoding="utf-8")
    header = f"## [{new_version}]"

    if header in content:
        print(f"  CHANGELOG.md already has {header}")
        return

    today = date.today().isoformat()

    # Collect git commits since last tag
    commits = get_git_log_since_last_tag()
    if commits:
        changes = "\n".join(f"- {c}" for c in commits)
    else:
        changes = "- (describe changes here)"

    new_section = f"\n## [{new_version}] - {today}\n\n### Changed\n\n{changes}\n"

    # Find the first existing version header and insert before it
    match = re.search(r'^## \[\d+\.\d+\.\d+\]', content, re.MULTILINE)
    if match:
        pos = match.start()
        updated = content[:pos] + new_section + "\n" + content[pos:]
    else:
        # No existing version, append at end
        updated = content + new_section

    CHANGELOG.write_text(updated, encoding="utf-8")
    print(f"  Updated CHANGELOG.md with [{new_version}] - {today}")
    if commits:
        print(f"  Auto-filled {len(commits)} commit messages")


def update_docs_version(old_version: str, new_version: str):
    """Update version references in documentation files."""
    docs_to_update = [
        ROOT / "docs" / "DELIVERY_GUIDE.md",
        ROOT / "docs" / "USER_GUIDE.md",
    ]

    old_patterns = [
        (f"aicodegencrew-v{old_version}", f"aicodegencrew-v{new_version}"),
        (f"aicodegencrew-{old_version}", f"aicodegencrew-{new_version}"),
        (f"aicodegencrew:{old_version}", f"aicodegencrew:{new_version}"),
        (f"v{old_version}", f"v{new_version}"),
        (f"Version {old_version}", f"Version {new_version}"),
        (f"Version: {old_version}", f"Version: {new_version}"),
    ]

    for doc in docs_to_update:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8")
        updated = content
        for old, new in old_patterns:
            updated = updated.replace(old, new)
        if updated != content:
            doc.write_text(updated, encoding="utf-8")
            print(f"  Updated {doc.name}: {old_version} -> {new_version}")


def git_tag(version: str):
    """Create git tag and commit version bump."""
    tag = f"v{version}"

    # Check for uncommitted changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    dirty_files = result.stdout.strip()

    if dirty_files:
        # Stage version-related files
        print(f"\n[GIT] Committing version bump to v{version}...")
        run(["git", "add", "pyproject.toml", "CHANGELOG.md",
             "docs/DELIVERY_GUIDE.md", "docs/USER_GUIDE.md"])
        run(["git", "commit", "-m", f"release: v{version}"])

    # Create annotated tag
    print(f"[GIT] Creating tag {tag}...")
    run(["git", "tag", "-a", tag, "-m", f"Release {version}"])
    print(f"  Tag created: {tag}")
    print(f"  To push: git push origin {tag}")


def build_wheel() -> Path:
    """Build Python wheel."""
    print("\n[1/4] Building wheel...")
    run([sys.executable, "-m", "pip", "install", "--quiet", "build"])
    run([sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST)])

    wheels = list(DIST.glob("aicodegencrew-*.whl"))
    if not wheels:
        print("ERROR: No wheel found in dist/")
        sys.exit(1)

    wheel = wheels[-1]  # Latest
    print(f"  Wheel: {wheel.name}")
    return wheel


def build_nuitka(version: str) -> Path:
    """
    Build protected native binary with Nuitka.
    
    Nuitka compiles Python to C, then to native machine code.
    This makes reverse engineering extremely difficult.
    """
    print("\n[2/4] Building protected binary with Nuitka...")
    
    # Ensure Nuitka is installed
    print("  Checking Nuitka installation...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise FileNotFoundError()
        print(f"  Nuitka version: {result.stdout.strip().splitlines()[0]}")
    except FileNotFoundError:
        print("  Installing Nuitka...")
        run([sys.executable, "-m", "pip", "install", "--quiet", "nuitka", "ordered-set", "zstandard"])
    
    # Clean previous build
    if NUITKA_DIST.exists():
        shutil.rmtree(NUITKA_DIST)
    NUITKA_DIST.mkdir(parents=True)
    
    # Determine output filename based on platform
    is_windows = platform.system() == "Windows"
    exe_name = "aicodegencrew.exe" if is_windows else "aicodegencrew"
    output_path = NUITKA_DIST / exe_name
    
    # Main entry point module
    main_module = SRC / "main.py"
    
    # Build Nuitka command with protection options
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        # Output
        f"--output-dir={NUITKA_DIST}",
        f"--output-filename={exe_name}",
        
        # Compilation mode - standalone binary with all dependencies
        "--standalone",
        "--onefile",  # Single executable file
        
        # Protection options (macht Reverse Engineering sehr schwer)
        "--no-pyi-file",          # Keine Type-Stub-Dateien
        "--remove-output",        # Entfernt temporäre Build-Dateien
        
        # Include all required packages
        "--follow-imports",
        f"--include-package=aicodegencrew",
        f"--include-package-data=aicodegencrew",
        
        # Product info (embedded in binary)
        f"--product-name=AICodeGenCrew",
        f"--product-version={version}",
        f"--file-version={version}",
        f"--file-description=AI Code Generation Crew - Architecture Analysis Tool",
        f"--copyright=Copyright 2024-2026",
        
        # Performance
        "--lto=yes",              # Link-Time Optimization
        "--assume-yes-for-downloads",  # Auto-download dependencies
        
        # Entry point
        str(main_module),
    ]
    
    # Windows-specific: hide console for GUI mode (optional)
    # nuitka_cmd.append("--windows-console-mode=disable")
    
    print("  Compiling to native binary (this may take 5-15 minutes)...")
    print(f"  Command: {' '.join(nuitka_cmd[:8])}...")
    
    result = subprocess.run(
        nuitka_cmd,
        cwd=str(ROOT),
        capture_output=False,  # Show Nuitka progress
    )
    
    if result.returncode != 0:
        print("ERROR: Nuitka compilation failed")
        sys.exit(1)
    
    # Find the generated executable
    if not output_path.exists():
        # Nuitka might put it in a subfolder
        exe_candidates = list(NUITKA_DIST.rglob(exe_name))
        if exe_candidates:
            output_path = exe_candidates[0]
        else:
            print(f"ERROR: Cannot find compiled binary {exe_name}")
            sys.exit(1)
    
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Protected binary: {output_path.name} ({size_mb:.1f} MB)")
    print(f"  ✓ Code protection: Native machine code - sehr schwer zu dekompilieren!")
    
    return output_path


def build_docker(version: str) -> Path | None:
    """Build Docker image and export as .tar.gz."""
    print("\n[2/4] Building Docker image...")

    tag = f"aicodegencrew:{version}"
    tag_latest = "aicodegencrew:latest"

    run(["docker", "build", "-t", tag, "-t", tag_latest, "."])

    # Export as tar
    tar_path = DIST / f"aicodegencrew-{version}.tar.gz"
    print(f"  Exporting Docker image to {tar_path.name}...")
    run(["docker", "save", "-o", str(tar_path), tag])

    print(f"  Docker image: {tar_path.name}")
    return tar_path


def push_docker(version: str, registry: str):
    """Push Docker image to registry."""
    print(f"\n[*] Pushing to {registry}...")
    remote_tag = f"{registry}/aicodegencrew:{version}"
    remote_latest = f"{registry}/aicodegencrew:latest"

    run(["docker", "tag", f"aicodegencrew:{version}", remote_tag])
    run(["docker", "tag", "aicodegencrew:latest", remote_latest])
    run(["docker", "push", remote_tag])
    run(["docker", "push", remote_latest])
    print(f"  Pushed: {remote_tag}")


def generate_pdf_from_markdown(md_path: Path, pdf_path: Path) -> bool:
    """
    Convert Markdown to PDF using pandoc.

    Returns True if successful, False if pandoc not available.
    """
    # Check if pandoc is available
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("  WARNING: pandoc not found. Skipping PDF generation.")
            print("  To generate PDF: Install pandoc from https://pandoc.org/")
            return False
    except FileNotFoundError:
        print("  WARNING: pandoc not installed. Skipping PDF generation.")
        print("  To generate PDF: Install pandoc from https://pandoc.org/")
        return False

    # Generate PDF with pandoc
    print(f"  Generating PDF: {pdf_path.name}...")

    # Find xelatex (check PATH and Windows default location)
    xelatex_cmd = "xelatex"
    if sys.platform == "win32":
        # Try default MiKTeX location on Windows
        miktex_paths = [
            r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\xelatex.exe"),
        ]
        for miktex_path in miktex_paths:
            if Path(miktex_path).exists():
                xelatex_cmd = miktex_path
                break

    # Try with xelatex first (best quality, needs LaTeX)
    pandoc_args = [
        "pandoc",
        str(md_path),
        "-o", str(pdf_path),
        f"--pdf-engine={xelatex_cmd}",
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
        "-V", "colorlinks=true",
        "--toc",
        "--toc-depth=2",
    ]

    result = subprocess.run(
        pandoc_args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    if pdf_path.exists():
        print(f"  PDF generated: {pdf_path.name} ({pdf_path.stat().st_size:,} bytes)")
        return True

    # xelatex failed, show error
    if result.stderr:
        print(f"  LaTeX error: {result.stderr[:500]}")

    # Try simpler HTML-based conversion
    print("  xelatex generation failed, trying HTML-based conversion...")
    result = subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-o", str(pdf_path),
            "--pdf-engine=wkhtmltopdf",
            "--toc",
            "--toc-depth=2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    if pdf_path.exists():
        print(f"  PDF generated: {pdf_path.name} ({pdf_path.stat().st_size:,} bytes)")
        return True

    # Both failed
    print("  WARNING: PDF generation failed.")
    print("  Reason: LaTeX engine not installed.")
    print("  To generate PDF: choco install miktex -y")
    print("  Alternative: Use markdown version (USER_GUIDE.md)")
    return False


def assemble_release(version: str, wheel: Path | None, docker_tar: Path | None, nuitka_exe: Path | None = None):
    """Assemble release package."""
    print("\n[3/4] Assembling release package...")
    
    is_nuitka_build = nuitka_exe is not None

    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True)

    # Copy main artifact: Nuitka binary or Wheel
    if is_nuitka_build:
        shutil.copy2(nuitka_exe, RELEASE / nuitka_exe.name)
        print(f"  \u2713 Protected binary: {nuitka_exe.name}")
    else:
        shutil.copy2(wheel, RELEASE / wheel.name)

    # Docker image (optional)
    if docker_tar and docker_tar.exists():
        shutil.copy2(docker_tar, RELEASE / docker_tar.name)

    # Configuration
    shutil.copy2(ROOT / ".env.example", RELEASE / ".env.example")
    shutil.copy2(ROOT / "docker-compose.yml", RELEASE / "docker-compose.yml")

    # Config directory
    config_dest = RELEASE / "config"
    config_dest.mkdir()
    shutil.copy2(ROOT / "config" / "phases_config.yaml", config_dest / "phases_config.yaml")

    # Documentation
    shutil.copy2(ROOT / "docs" / "USER_GUIDE.md", RELEASE / "USER_GUIDE.md")

    # Generate PDF from USER_GUIDE.md
    generate_pdf_from_markdown(
        ROOT / "docs" / "USER_GUIDE.md",
        RELEASE / "USER_GUIDE.pdf"
    )

    if CHANGELOG.exists():
        shutil.copy2(CHANGELOG, RELEASE / "CHANGELOG.md")

    # Create install scripts based on build type
    if is_nuitka_build:
        _create_nuitka_install_scripts(version, nuitka_exe)
    else:
        _create_wheel_install_scripts(version, wheel)

    print(f"  Release directory: {RELEASE}")


def _create_nuitka_install_scripts(version: str, nuitka_exe: Path):
    """Create install scripts for protected Nuitka binary."""
    exe_name = nuitka_exe.name
    is_windows = exe_name.endswith(".exe")
    
    # Windows install
    install_bat = RELEASE / "install.bat"
    install_bat.write_text(
        f"@echo off\n"
        f"echo Installing AICodeGenCrew v{version} (Protected Binary)...\n"
        f"echo.\n"
        f"echo Copying executable to C:\\Program Files\\AICodeGenCrew\\...\n"
        f"mkdir \"C:\\Program Files\\AICodeGenCrew\" 2>nul\n"
        f"copy /Y \"{exe_name}\" \"C:\\Program Files\\AICodeGenCrew\\\"\n"
        f"echo.\n"
        f"echo Adding to PATH...\n"
        f"setx PATH \"%PATH%;C:\\Program Files\\AICodeGenCrew\" /M 2>nul || (\n"
        f"    echo Note: Could not add to PATH automatically. Run as Administrator or add manually.\n"
        f")\n"
        f"echo.\n"
        f"echo Installation complete!\n"
        f"echo.\n"
        f"echo Next steps:\n"
        f"echo   1. Copy .env.example to your project folder as .env\n"
        f"echo   2. Edit .env with your settings\n"
        f"echo   3. Start Ollama: ollama serve\n"
        f"echo   4. Run: aicodegencrew --env .env plan\n"
        f"echo.\n"
        f"echo Alternative: Run directly from this folder:\n"
        f"echo   {exe_name} --env .env plan\n"
        f"echo.\n"
        f"pause\n",
        encoding="utf-8",
    )

    # Linux/macOS install
    install_sh = RELEASE / "install.sh"
    linux_exe = exe_name.replace(".exe", "") if is_windows else exe_name
    install_sh.write_text(
        f"#!/bin/bash\n"
        f"set -e\n"
        f'echo "Installing AICodeGenCrew v{version} (Protected Binary)..."\n'
        f'echo ""\n'
        f'echo "Copying executable to /usr/local/bin/..."\n'
        f'sudo cp "{linux_exe}" /usr/local/bin/aicodegencrew\n'
        f'sudo chmod +x /usr/local/bin/aicodegencrew\n'
        f'echo ""\n'
        f'echo "Installation complete!"\n'
        f'echo ""\n'
        f'echo "Next steps:"\n'
        f'echo "  1. Copy .env.example to your project folder as .env"\n'
        f'echo "  2. Edit .env with your settings"\n'
        f'echo "  3. Start Ollama: ollama serve"\n'
        f'echo "  4. Run: aicodegencrew --env .env plan"\n',
        encoding="utf-8",
    )
    install_sh.chmod(0o755)

    # Windows uninstall
    uninstall_bat = RELEASE / "uninstall.bat"
    uninstall_bat.write_text(
        "@echo off\n"
        "echo Uninstalling AICodeGenCrew...\n"
        "echo.\n"
        "del /F /Q \"C:\\Program Files\\AICodeGenCrew\\aicodegencrew.exe\" 2>nul\n"
        "rmdir \"C:\\Program Files\\AICodeGenCrew\" 2>nul\n"
        "echo.\n"
        "echo AICodeGenCrew has been uninstalled.\n"
        "echo.\n"
        "echo Note: Configuration files (.env) and generated knowledge base\n"
        "echo       remain in their respective directories.\n"
        "echo.\n"
        "pause\n",
        encoding="utf-8",
    )

    # Linux/macOS uninstall
    uninstall_sh = RELEASE / "uninstall.sh"
    uninstall_sh.write_text(
        "#!/bin/bash\n"
        'echo "Uninstalling AICodeGenCrew..."\n'
        'echo ""\n'
        "sudo rm -f /usr/local/bin/aicodegencrew\n"
        'echo ""\n'
        'echo "AICodeGenCrew has been uninstalled."\n'
        'echo ""\n'
        'echo "Note: Configuration files (.env) and generated knowledge base"\n'
        'echo "      remain in their respective directories."\n',
        encoding="utf-8",
    )
    uninstall_sh.chmod(0o755)


def _create_wheel_install_scripts(version: str, wheel: Path):
    """Create install scripts for wheel package."""
    # Create install script (Windows)
    install_bat = RELEASE / "install.bat"
    install_bat.write_text(
        f"@echo off\n"
        f"echo Installing AICodeGenCrew v{version}...\n"
        f"pip install {wheel.name}[parsers]\n"
        f"echo.\n"
        f"echo Installation complete!\n"
        f"echo.\n"
        f"echo Next steps:\n"
        f"echo   1. Copy .env.example to .env and edit with your settings\n"
        f"echo   2. Start Ollama: ollama serve\n"
        f"echo   3. Run: aicodegencrew --env .env plan\n"
        f"echo.\n"
        f"pause\n",
        encoding="utf-8",
    )

    # Create install script (Linux/macOS)
    install_sh = RELEASE / "install.sh"
    install_sh.write_text(
        f"#!/bin/bash\n"
        f"set -e\n"
        f'echo "Installing AICodeGenCrew v{version}..."\n'
        f"pip install {wheel.name}\"[parsers]\"\n"
        f'echo ""\n'
        f'echo "Installation complete!"\n'
        f'echo ""\n'
        f'echo "Next steps:"\n'
        f'echo "  1. Copy .env.example to .env and edit with your settings"\n'
        f'echo "  2. Start Ollama: ollama serve"\n'
        f'echo "  3. Run: aicodegencrew --env .env plan"\n',
        encoding="utf-8",
    )
    install_sh.chmod(0o755)

    # Create uninstall script (Windows)
    uninstall_bat = RELEASE / "uninstall.bat"
    uninstall_bat.write_text(
        "@echo off\n"
        "echo Uninstalling AICodeGenCrew...\n"
        "echo.\n"
        "pip uninstall -y aicodegencrew\n"
        "echo.\n"
        "echo AICodeGenCrew has been uninstalled.\n"
        "echo.\n"
        "echo Note: Configuration files (.env) and generated knowledge base\n"
        "echo       remain in their respective directories.\n"
        "echo.\n"
        "echo To completely remove all data:\n"
        "echo   1. Delete your .env file (if no longer needed)\n"
        "echo   2. Delete the knowledge/ folder in your project directory\n"
        "echo.\n"
        "pause\n",
        encoding="utf-8",
    )

    # Create uninstall script (Linux/macOS)
    uninstall_sh = RELEASE / "uninstall.sh"
    uninstall_sh.write_text(
        "#!/bin/bash\n"
        'echo "Uninstalling AICodeGenCrew..."\n'
        'echo ""\n'
        "pip uninstall -y aicodegencrew\n"
        'echo ""\n'
        'echo "AICodeGenCrew has been uninstalled."\n'
        'echo ""\n'
        'echo "Note: Configuration files (.env) and generated knowledge base"\n'
        'echo "      remain in their respective directories."\n'
        'echo ""\n'
        'echo "To completely remove all data:"\n'
        'echo "  1. Delete your .env file (if no longer needed)"\n'
        'echo "  2. Delete the knowledge/ folder in your project directory"\n'
        'echo ""\n'
        'read -p "Press Enter to continue..."\n',
        encoding="utf-8",
    )
    uninstall_sh.chmod(0o755)


def create_release_zip(version: str) -> Path:
    """Create properly structured ZIP file for distribution."""
    print("\n[3.5/4] Creating distribution ZIP...")

    # ZIP file in dist/ (not inside release/)
    zip_name = f"aicodegencrew-v{version}.zip"
    zip_path = DIST / zip_name

    # Remove old ZIP if exists
    if zip_path.exists():
        zip_path.unlink()

    # Create ZIP with correct structure: aicodegencrew-v0.1.0/ at root
    root_folder = f"aicodegencrew-v{version}"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files from dist/release/ into aicodegencrew-vX.Y.Z/
        for file in RELEASE.rglob('*'):
            if file.is_file():
                # Path relative to RELEASE
                rel_path = file.relative_to(RELEASE)
                # Store in ZIP under root_folder/
                arcname = f"{root_folder}/{rel_path}"
                zipf.write(file, arcname)

    size_kb = zip_path.stat().st_size / 1024
    print(f"  ZIP created: {zip_name} ({size_kb:.1f} KB)")
    print(f"  Extracts to: {root_folder}/")

    return zip_path


def print_summary(version: str, docker: bool, nuitka: bool, zip_path: Path):
    """Print release summary."""
    print("\n[4/4] Release summary")
    print("=" * 60)
    print(f"  Version:    {version}")
    build_type = "Protected Native Binary (Nuitka)" if nuitka else "Python Wheel"
    print(f"  Build Type: {build_type}")
    print(f"  Directory:  {RELEASE}")
    print(f"  ZIP file:   {zip_path.name}")
    print()

    files = sorted(RELEASE.rglob("*"))
    total_size = 0
    for f in files:
        if f.is_file():
            size = f.stat().st_size
            total_size += size
            rel = str(f.relative_to(RELEASE))
            print(f"  {rel:<45} {size:>10,} bytes")

    print(f"  {'TOTAL':<45} {total_size:>10,} bytes")

    # Show ZIP size
    zip_size = zip_path.stat().st_size
    print(f"  {'ZIP archive':<45} {zip_size:>10,} bytes")

    print("=" * 60)
    print()
    
    if nuitka:
        print("Code Protection:")
        print("  ✓ Native machine code - Source code ist nicht extrahierbar!")
        print("  ✓ Keine Python-Bytecode-Dateien (.pyc) in der Delivery")
        print("  ✓ Reverse Engineering extrem schwierig")
        print()
    
    print("Delivery instructions:")
    print(f"  1. Send '{zip_path.name}' to the end user")
    print(f"  2. User extracts ZIP -> 'aicodegencrew-v{version}/' folder")
    print(f"  3. User runs: install.bat (Windows) or install.sh (Linux)")
    print(f"  4. User configures .env with their settings")
    print(f"  5. User runs: aicodegencrew --env .env plan")
    if docker:
        print(f"  6. Docker: docker load -i aicodegencrew-{version}.tar.gz")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Build AICodeGenCrew release package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build_release.py                       # Build protected binary (default)
  python scripts/build_release.py --wheel               # Build wheel (internal use only)
  python scripts/build_release.py --bump patch          # 0.1.0 -> 0.1.1
  python scripts/build_release.py --bump patch --wheel  # Wheel + version bump
  python scripts/build_release.py --bump minor --tag    # 0.1.0 -> 0.2.0 + git tag
  python scripts/build_release.py --bump patch --tag --docker  # Full release

Code Protection (Default):
  Default build uses Nuitka to compile to native machine code.
  The binary cannot be decompiled back to Python source code.
  Use --wheel only for internal development purposes.
""",
    )
    parser.add_argument(
        "--bump", choices=["major", "minor", "patch"],
        help="Bump version before building (major/minor/patch)",
    )
    parser.add_argument(
        "--tag", action="store_true",
        help="Create git tag (commits pyproject.toml + CHANGELOG.md, tags vX.Y.Z)",
    )
    parser.add_argument(
        "--wheel", action="store_true",
        help="Build wheel package instead of protected binary (internal use only)",
    )
    parser.add_argument("--docker", action="store_true", help="Build Docker image")
    parser.add_argument("--push", action="store_true", help="Push Docker image to registry")
    parser.add_argument("--registry", default="", help="Docker registry URL")
    args = parser.parse_args()

    # Step 0: Version bump (optional)
    current_version = get_version()

    if args.bump:
        new_version = bump_version(current_version, args.bump)
        print(f"AICodeGenCrew Release Builder")
        print(f"  Version bump: {current_version} -> {new_version}")
        print("=" * 60)
        set_version(new_version)
        update_changelog(new_version)
        update_docs_version(current_version, new_version)
        version = new_version
    else:
        version = current_version
        print(f"AICodeGenCrew Release Builder v{version}")
        print("=" * 60)

    # Step 1: Build Nuitka binary (default) or wheel
    nuitka_exe = None
    wheel = None
    
    if args.wheel:
        wheel = build_wheel()
    else:
        nuitka_exe = build_nuitka(version)

    # Step 2: Docker (optional)
    docker_tar = None
    if args.docker:
        docker_tar = build_docker(version)

    if args.push and args.registry:
        push_docker(version, args.registry)

    # Step 3: Assemble release
    assemble_release(version, wheel, docker_tar, nuitka_exe)

    # Step 3.5: Create ZIP file
    zip_path = create_release_zip(version)

    # Step 4: Git tag (optional)
    if args.tag:
        git_tag(version)

    # Summary
    print_summary(version, args.docker, not args.wheel, zip_path)


if __name__ == "__main__":
    main()
