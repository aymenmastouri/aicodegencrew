"""Smart indexing configuration - auto-detect what to index.

Reads .gitignore and analyzes directory structure to decide:
- Which directories contain code
- What file types are important
- What to exclude
"""

import os
from pathlib import Path
from typing import List, Set, Dict, Optional
import re


class SmartIndexConfig:
    """Auto-detect indexing configuration for any repository."""
    
    # Common source directories (in priority order)
    SOURCE_DIR_PATTERNS = [
        "src", "source", "lib", "libraries", "backend", "frontend",
        "app", "application", "code", "services", "modules"
    ]
    
    # File extensions that indicate source code
    CODE_EXTENSIONS = {
        # Languages
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt",
        ".cs", ".cpp", ".c", ".h", ".hpp", ".go", ".rs",
        # Markup
        ".html", ".xml", ".md", ".json",
        # Styling
        ".css", ".scss", ".less",
        # Config
        ".yml", ".yaml", ".toml", ".properties", ".gradle", ".xml",
        # Build
        ".gradle", ".maven",
        # Docs
        ".md", ".txt",
        # Database
        ".sql",
        # Shell
        ".sh", ".bash"
    }
    
    def __init__(self, repo_path: str):
        """Initialize with repository path."""
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise ValueError(f"Repository path not found: {repo_path}")
        
        self.gitignore_patterns: Set[str] = set()
        self._load_gitignore()
    
    def _load_gitignore(self) -> None:
        """Load and parse .gitignore file."""
        gitignore = self.repo_path / ".gitignore"
        if not gitignore.exists():
            return
        
        try:
            with open(gitignore, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Convert to glob pattern for fnmatch
                    self.gitignore_patterns.add(line)
        except Exception:
            pass
    
    def _is_code_directory(self, dir_path: Path) -> bool:
        """Check if directory likely contains source code."""
        # Skip obvious non-code directories
        non_code_dirs = {
            ".git", ".idea", ".vscode", ".continue", "node_modules",
            "dist", "build", "target", "__pycache__", ".pytest_cache",
            "vendor", "logs", "test-results", "coverage", ".gradle",
            ".maven", ".cache", "bin", "obj"
        }
        
        if dir_path.name in non_code_dirs:
            return False
        
        # Check if directory has code files
        try:
            for item in dir_path.iterdir():
                if item.is_file() and item.suffix in self.CODE_EXTENSIONS:
                    return True
                elif item.is_dir() and not item.name.startswith("."):
                    # Recursively check subdirs (but not too deep)
                    if self._is_code_directory(item):
                        return True
        except (PermissionError, OSError):
            pass
        
        return False
    
    def _find_source_directories(self) -> List[str]:
        """Find main source code directories in repository."""
        sources = []
        
        try:
            for item in self.repo_path.iterdir():
                if not item.is_dir():
                    continue
                if item.name.startswith("."):
                    continue
                
                # Check if it's a known source directory
                if item.name.lower() in self.SOURCE_DIR_PATTERNS:
                    sources.append(item.name)
                # Or if it contains code
                elif self._is_code_directory(item):
                    sources.append(item.name)
        except (PermissionError, OSError):
            pass
        
        return sorted(sources)
    
    def auto_generate_globs(self) -> Dict[str, List[str]]:
        """Auto-generate include/exclude glob patterns."""
        
        # Find source directories
        sources = self._find_source_directories()
        
        # If we found source dirs, create globs for them
        include_globs = []
        if sources:
            for src in sources:
                include_globs.extend([
                    f"{src}/**/*.py",
                    f"{src}/**/*.java",
                    f"{src}/**/*.ts",
                    f"{src}/**/*.tsx",
                    f"{src}/**/*.js",
                    f"{src}/**/*.jsx",
                    f"{src}/**/*.cs",
                    f"{src}/**/*.go",
                    f"{src}/**/*.rs",
                    f"{src}/**/*.cpp",
                    f"{src}/**/*.c",
                    f"{src}/**/*.h",
                    f"{src}/**/*.xml",
                    f"{src}/**/*.yml",
                    f"{src}/**/*.yaml",
                    f"{src}/**/*.properties",
                    f"{src}/**/*.gradle",
                    f"{src}/**/*.md",
                    f"{src}/**/*.sql",
                    f"{src}/**/*.json",
                    f"{src}/**/*.html",
                    f"{src}/**/*.css",
                    f"{src}/**/*.scss",
                ])
        else:
            # Fallback: index all code files in repo
            for ext in self.CODE_EXTENSIONS:
                include_globs.append(f"**/*{ext}")
        
        # Common root-level files
        include_globs.extend([
            "README.md",
            "**/README.md",
            "architecture*.md",
            "**/ARCHITECTURE.md",
            "pom.xml",
            "package.json",
            "Dockerfile",
            "docker-compose*.yml",
            "docker-compose*.yaml",
        ])
        
        # Generate exclude globs from .gitignore
        exclude_globs = []
        if self.gitignore_patterns:
            exclude_globs.extend([f"**/{p}" for p in self.gitignore_patterns])
        
        # Add common exclude patterns
        exclude_globs.extend([
            "**/.git/**",
            "**/.idea/**",
            "**/.vscode/**",
            "**/.continue/**",
            "**/node_modules/**",
            "**/dist/**",
            "**/build/**",
            "**/target/**",
            "**/__pycache__/**",
            "**/.pytest_cache/**",
            "**/logs/**",
            "**/log/**",
            "**/test-results/**",
            "**/coverage/**",
            "**/.gradle/**",
            "**/.maven/**",
            "**/venv/**",
            "**/.venv/**",
        ])
        
        return {
            "include": list(set(include_globs)),  # Remove duplicates
            "exclude": list(set(exclude_globs)),
            "source_dirs": sources
        }
    
    def print_config(self) -> None:
        """Print the detected configuration."""
        config = self.auto_generate_globs()
        
        print("\n" + "="*60)
        print("Smart Indexing Configuration")
        print("="*60)
        print(f"\nRepository: {self.repo_path}")
        print(f"\nDetected Source Directories: {config['source_dirs']}")
        print(f"\nInclude Patterns ({len(config['include'])}):")
        for p in sorted(config['include'])[:10]:
            print(f"  - {p}")
        if len(config['include']) > 10:
            print(f"  ... and {len(config['include']) - 10} more")
        
        print(f"\nExclude Patterns ({len(config['exclude'])}):")
        for p in sorted(config['exclude'])[:10]:
            print(f"  - {p}")
        if len(config['exclude']) > 10:
            print(f"  ... and {len(config['exclude']) - 10} more")
        print("\n" + "="*60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        repo = sys.argv[1]
    else:
        repo = "."
    
    config = SmartIndexConfig(repo)
    config.print_config()
