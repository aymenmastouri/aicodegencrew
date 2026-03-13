#!/usr/bin/env python3
"""
Build Docker-based Release Package for SDLC Pilot.

Creates a distribution-ready ZIP with:
  - Docker images (.tar.gz) — backend + frontend
  - docker-compose.yml
  - start.sh / start.bat (one-click start)
  - clean.sh / clean.bat (full cleanup)
  - .env.example
  - config/phases_config.yaml
  - README.md

Usage:
    python scripts/build_release.py                              # Build current version
    python scripts/build_release.py --bump patch                 # 0.7.3 -> 0.7.4
    python scripts/build_release.py --bump patch --tag           # + git tag v0.7.4
    python scripts/build_release.py --no-docker                  # Skip Docker build (use existing images)
"""

import argparse
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
TEMPLATE = DIST / "release-template"
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
    print(f'  Updated pyproject.toml: version = "{new_version}"')


def get_git_log_since_last_tag() -> list[str]:
    """Get commit messages since the last git tag (or all if no tags)."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    last_tag = result.stdout.strip() if result.returncode == 0 else ""

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

    commits = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Merge ") or line.startswith("release:"):
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
    commits = get_git_log_since_last_tag()
    changes = "\n".join(f"- {c}" for c in commits) if commits else "- (describe changes here)"
    new_section = f"\n## [{new_version}] - {today}\n\n### Changed\n\n{changes}\n"

    match = re.search(r'^## \[\d+\.\d+\.\d+\]', content, re.MULTILINE)
    if match:
        pos = match.start()
        updated = content[:pos] + new_section + "\n" + content[pos:]
    else:
        updated = content + new_section

    CHANGELOG.write_text(updated, encoding="utf-8")
    print(f"  Updated CHANGELOG.md with [{new_version}] - {today}")


def git_tag(version: str):
    """Create git tag and commit version bump."""
    tag = f"v{version}"

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    dirty_files = result.stdout.strip()

    if dirty_files:
        print(f"\n[GIT] Committing version bump to v{version}...")
        run(["git", "add", "pyproject.toml", "CHANGELOG.md"])
        run(["git", "commit", "-m", f"release: v{version}"])

    print(f"[GIT] Creating tag {tag}...")
    run(["git", "tag", "-a", tag, "-m", f"Release {version}"])
    print(f"  Tag created: {tag}")
    print(f"  To push: git push origin {tag}")


# ── Docker Build ──────────────────────────────────────────────────────────


def build_docker_images(version: str):
    """Build Docker images for backend and frontend."""
    print("\n[1/4] Building Docker images...")

    # Backend
    print("  Building backend image...")
    run([
        "docker", "build",
        "-t", f"sdlc-pilot/backend:{version}",
        "-t", "sdlc-pilot/backend:latest",
        "-f", "ui/backend/Dockerfile.dev",
        ".",
    ])

    # Frontend
    print("  Building frontend image...")
    run([
        "docker", "build",
        "-t", f"sdlc-pilot/frontend:{version}",
        "-t", "sdlc-pilot/frontend:latest",
        "-f", "ui/frontend/Dockerfile",
        ".",
    ])

    print("  Docker images built successfully.")


def export_docker_images(version: str, release_dir: Path):
    """Export Docker images as .tar.gz files."""
    print("\n[2/4] Exporting Docker images...")

    backend_tar = release_dir / "sdlc-pilot-backend.tar.gz"
    frontend_tar = release_dir / "sdlc-pilot-frontend.tar.gz"

    print(f"  Exporting backend image...")
    run(["docker", "save", "-o", str(backend_tar), f"sdlc-pilot/backend:{version}"])

    print(f"  Exporting frontend image...")
    run(["docker", "save", "-o", str(frontend_tar), f"sdlc-pilot/frontend:{version}"])

    backend_mb = backend_tar.stat().st_size / (1024 * 1024)
    frontend_mb = frontend_tar.stat().st_size / (1024 * 1024)
    print(f"  Backend:  {backend_mb:.1f} MB")
    print(f"  Frontend: {frontend_mb:.1f} MB")


# ── Assemble Release ─────────────────────────────────────────────────────


def assemble_release(version: str) -> Path:
    """Assemble release directory from release-template."""
    print("\n[3/4] Assembling release package...")

    release_dir = DIST / f"sdlc-pilot-v{version}"

    if release_dir.exists():
        shutil.rmtree(release_dir)

    if not TEMPLATE.exists():
        print(f"ERROR: Release template not found at {TEMPLATE}")
        sys.exit(1)

    # Copy entire template
    shutil.copytree(TEMPLATE, release_dir)

    # Copy CHANGELOG
    if CHANGELOG.exists():
        shutil.copy2(CHANGELOG, release_dir / "CHANGELOG.md")

    # Ensure config is up-to-date
    config_src = ROOT / "config" / "phases_config.yaml"
    config_dst = release_dir / "config" / "phases_config.yaml"
    if config_src.exists():
        config_dst.parent.mkdir(exist_ok=True)
        shutil.copy2(config_src, config_dst)

    # Set executable permissions on shell scripts
    for sh in release_dir.glob("*.sh"):
        sh.chmod(0o755)

    print(f"  Release directory: {release_dir}")
    return release_dir


def create_release_zip(version: str, release_dir: Path) -> Path:
    """Create ZIP file for distribution."""
    print("\n[3.5/4] Creating distribution ZIP...")

    zip_name = f"sdlc-pilot-v{version}.zip"
    zip_path = DIST / zip_name

    if zip_path.exists():
        zip_path.unlink()

    root_folder = f"sdlc-pilot-v{version}"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in release_dir.rglob('*'):
            if file.is_file():
                rel_path = file.relative_to(release_dir)
                arcname = f"{root_folder}/{rel_path}"
                zipf.write(file, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ZIP created: {zip_name} ({size_mb:.1f} MB)")
    print(f"  Extracts to: {root_folder}/")

    return zip_path


def print_summary(version: str, release_dir: Path, zip_path: Path):
    """Print release summary."""
    print("\n[4/4] Release summary")
    print("=" * 60)
    print(f"  Version:    {version}")
    print(f"  Directory:  {release_dir}")
    print(f"  ZIP file:   {zip_path.name}")
    print()

    total_size = 0
    for f in sorted(release_dir.rglob("*")):
        if f.is_file():
            size = f.stat().st_size
            total_size += size
            rel = str(f.relative_to(release_dir))
            if size > 1024 * 1024:
                print(f"  {rel:<45} {size / (1024*1024):>8.1f} MB")
            else:
                print(f"  {rel:<45} {size:>10,} bytes")

    print(f"  {'TOTAL':<45} {total_size / (1024*1024):>8.1f} MB")

    zip_size = zip_path.stat().st_size
    print(f"  {'ZIP archive':<45} {zip_size / (1024*1024):>8.1f} MB")

    print("=" * 60)
    print()
    print("Delivery instructions:")
    print(f"  1. Send '{zip_path.name}' to the end user")
    print(f"  2. User extracts ZIP -> 'sdlc-pilot-v{version}/' folder")
    print(f"  3. User copies .env.example -> .env and edits settings")
    print(f"  4. User runs: start.bat (Windows) or ./start.sh (Linux/Mac)")
    print(f"  5. Open http://localhost in browser")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Build SDLC Pilot Docker release package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/build_release.py                       # Build current version
  python scripts/build_release.py --bump patch          # 0.7.3 -> 0.7.4
  python scripts/build_release.py --bump minor --tag    # 0.7.3 -> 0.8.0 + git tag
  python scripts/build_release.py --no-docker           # Skip Docker build (test packaging)
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
        "--no-docker", action="store_true",
        help="Skip Docker image build and export (for testing packaging only)",
    )
    args = parser.parse_args()

    # Step 0: Version bump (optional)
    current_version = get_version()

    if args.bump:
        new_version = bump_version(current_version, args.bump)
        print(f"SDLC Pilot Release Builder")
        print(f"  Version bump: {current_version} -> {new_version}")
        print("=" * 60)
        set_version(new_version)
        update_changelog(new_version)
        version = new_version
    else:
        version = current_version
        print(f"SDLC Pilot Release Builder v{version}")
        print("=" * 60)

    # Step 1-2: Docker build + export
    if not args.no_docker:
        build_docker_images(version)

    # Step 3: Assemble release from template
    release_dir = assemble_release(version)

    # Step 2 (after assemble so dir exists): Export Docker images into release dir
    if not args.no_docker:
        export_docker_images(version, release_dir)

    # Step 3.5: Create ZIP
    zip_path = create_release_zip(version, release_dir)

    # Step 4: Git tag (optional)
    if args.tag:
        git_tag(version)

    # Summary
    print_summary(version, release_dir, zip_path)


if __name__ == "__main__":
    main()
