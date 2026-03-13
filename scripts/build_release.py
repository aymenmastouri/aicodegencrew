#!/usr/bin/env python3
"""
Build Release Package for AICodeGenCrew.

Creates a distribution-ready package with:
  - Python wheel (.whl) — no source code
  - Docker image (.tar.gz) — optional
  - Configuration template (.env.example)
  - User documentation (USER_GUIDE.md + USER_GUIDE.pdf)
  - phases_config.yaml
  - docker-compose.yml

Usage:
    python scripts/build_release.py                              # Build current version
    python scripts/build_release.py --bump patch                 # 0.1.0 -> 0.1.1
    python scripts/build_release.py --bump minor                 # 0.1.0 -> 0.2.0
    python scripts/build_release.py --bump major                 # 0.1.0 -> 1.0.0
    python scripts/build_release.py --bump patch --tag           # + git tag v0.1.1
    python scripts/build_release.py --bump patch --tag --docker  # + Docker image
"""

import argparse
import os
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
    result = subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-o", str(pdf_path),
            f"--pdf-engine={xelatex_cmd}",
            "-V", "geometry:margin=1in",
            "-V", "fontsize=11pt",
            "-V", "colorlinks=true",
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

    # xelatex failed, try simpler HTML-based conversion
    print("  xelatex not found, trying HTML-based conversion...")
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


def assemble_release(version: str, wheel: Path, docker_tar: Path | None):
    """Assemble release package."""
    print("\n[3/4] Assembling release package...")

    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True)

    # Wheel
    shutil.copy2(wheel, RELEASE / wheel.name)

    # Docker image (optional)
    if docker_tar and docker_tar.exists():
        shutil.copy2(docker_tar, RELEASE / docker_tar.name)

    # Configuration
    for src, dst in [
        (ROOT / ".env.example", RELEASE / ".env.example"),
        (ROOT / "docker-compose.yml", RELEASE / "docker-compose.yml"),
    ]:
        if not src.exists():
            print(f"  WARNING: Required file missing, skipping: {src}")
            continue
        shutil.copy2(src, dst)

    # Config directory
    config_dest = RELEASE / "config"
    config_dest.mkdir()
    config_src = ROOT / "config" / "phases_config.yaml"
    if config_src.exists():
        shutil.copy2(config_src, config_dest / "phases_config.yaml")
    else:
        print(f"  WARNING: Config file missing: {config_src}")

    # Documentation
    user_guide = ROOT / "docs" / "USER_GUIDE.md"
    if user_guide.exists():
        shutil.copy2(user_guide, RELEASE / "USER_GUIDE.md")
    else:
        print(f"  WARNING: USER_GUIDE.md not found at {user_guide}, skipping")

    # Generate PDF from USER_GUIDE.md
    generate_pdf_from_markdown(
        ROOT / "docs" / "USER_GUIDE.md",
        RELEASE / "USER_GUIDE.pdf"
    )

    if CHANGELOG.exists():
        shutil.copy2(CHANGELOG, RELEASE / "CHANGELOG.md")

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
    install_sh.chmod(0o755)
    uninstall_sh.chmod(0o755)

    print(f"  Release directory: {RELEASE}")


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


def print_summary(version: str, docker: bool, zip_path: Path):
    """Print release summary."""
    print("\n[4/4] Release summary")
    print("=" * 60)
    print(f"  Version:    {version}")
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
  python scripts/build_release.py                       # Build current version
  python scripts/build_release.py --bump patch          # 0.1.0 -> 0.1.1
  python scripts/build_release.py --bump minor --tag    # 0.1.0 -> 0.2.0 + git tag
  python scripts/build_release.py --bump patch --tag --docker  # Full release
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

    # Step 1: Build wheel
    wheel = build_wheel()

    # Step 2: Docker (optional)
    docker_tar = None
    if args.docker:
        docker_tar = build_docker(version)

    if args.push and args.registry:
        push_docker(version, args.registry)

    # Step 3: Assemble release
    assemble_release(version, wheel, docker_tar)

    # Step 3.5: Create ZIP file
    zip_path = create_release_zip(version)

    # Step 4: Git tag (optional)
    if args.tag:
        git_tag(version)

    # Summary
    print_summary(version, args.docker, zip_path)


if __name__ == "__main__":
    main()
