"""Repository reader tool for reading files from repository."""

from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ...shared.utils.file_filters import collect_files
from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class RepoReaderInput(BaseModel):
    """Input schema for RepoReaderTool."""

    repo_path: str = Field(..., description="Path to repository")
    scan_paths: list[str] = Field(default_factory=list, description="Specific paths to scan (empty for repo root)")
    specific_files: list[str] = Field(
        default_factory=list, description="Specific files to read (overrides scan_paths if present)"
    )
    max_file_bytes: int = Field(default=1048576, description="Maximum file size in bytes")


class RepoReaderTool(BaseTool):
    name: str = "repo_reader"
    description: str = (
        "Reads files from repository based on include/exclude patterns. "
        "Returns list of file paths with content and metadata."
    )
    args_schema: type[BaseModel] = RepoReaderInput

    def _run(
        self,
        repo_path: str,
        scan_paths: list[str] = None,
        specific_files: list[str] = None,
        max_file_bytes: int = 1048576,
    ) -> dict[str, Any]:
        """Read files from repository.

        Args:
            repo_path: Path to repository
            scan_paths: Specific paths to scan
            specific_files: Specific files to read
            max_file_bytes: Maximum file size

        Returns:
            Dictionary with file information
        """
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository path does not exist: {repo_path}",
            }

        all_files = []
        stats = {
            "total_files": 0,
            "skipped_binary": 0,
            "skipped_too_large": 0,
            "skipped_encoding_error": 0,
            "successful": 0,
        }

        # Case 1: Specific files provided (Batch mode)
        if specific_files:
            files_to_process = [Path(p).resolve() for p in specific_files if Path(p).exists()]
        # Case 2: Scan directories
        else:
            if not scan_paths:
                scan_paths = [str(repo_path)]
            files_to_process = []
            for scan_path_str in scan_paths:
                scan_path = Path(scan_path_str).resolve()
                if scan_path.exists():
                    files_to_process.extend(collect_files(scan_path))
                    logger.info(f"Found {len(files_to_process)} files in {scan_path}")

        # Process files
        for file_path in files_to_process:
            stats["total_files"] += 1

            # Get relative path
            try:
                rel_path = file_path.relative_to(repo_path)
            except ValueError:
                # Fallback to absolute if outside (e.g. symlinked or submodule issue)
                rel_path = file_path

            file_info = self._read_file(file_path, rel_path, max_file_bytes)

            if file_info["success"]:
                all_files.append(file_info)
                stats["successful"] += 1
            else:
                reason = file_info.get("reason", "unknown")
                if reason == "binary":
                    stats["skipped_binary"] += 1
                elif reason == "too_large":
                    stats["skipped_too_large"] += 1
                elif reason == "encoding_error":
                    stats["skipped_encoding_error"] += 1

        logger.info(
            f"Read {stats['successful']}/{stats['total_files']} files. "
            f"Skipped: binary={stats['skipped_binary']}, "
            f"too_large={stats['skipped_too_large']}, "
            f"encoding={stats['skipped_encoding_error']}"
        )

        return {
            "success": True,
            "files": all_files,
            "stats": stats,
        }

    def _read_file(
        self,
        file_path: Path,
        rel_path: Path,
        max_file_bytes: int,
    ) -> dict[str, Any]:
        """Read a single file with error handling.

        Args:
            file_path: Absolute path to file
            rel_path: Relative path from repo root
            max_file_bytes: Maximum file size

        Returns:
            Dictionary with file information
        """
        try:
            file_size = file_path.stat().st_size

            # Check file size
            if file_size > max_file_bytes:
                return {
                    "success": False,
                    "path": str(rel_path),
                    "reason": "too_large",
                    "size": file_size,
                }

            # Try to detect binary files
            if self._is_likely_binary(file_path):
                return {
                    "success": False,
                    "path": str(rel_path),
                    "reason": "binary",
                    "size": file_size,
                }

            # Try reading with UTF-8, fallback to latin-1
            content = None
            encoding = "utf-8"

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, encoding="latin-1") as f:
                        content = f.read()
                    encoding = "latin-1"
                except Exception:
                    return {
                        "success": False,
                        "path": str(rel_path),
                        "reason": "encoding_error",
                        "size": file_size,
                    }

            return {
                "success": True,
                "path": str(rel_path).replace("\\", "/"),
                "content": content,
                "size": file_size,
                "encoding": encoding,
            }

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {
                "success": False,
                "path": str(rel_path),
                "reason": "error",
                "error": str(e),
            }

    def _is_likely_binary(self, file_path: Path) -> bool:
        """Check if file is likely binary.

        Args:
            file_path: Path to file

        Returns:
            True if likely binary
        """
        # Check by extension first
        binary_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".pdf",
            ".zip",
            ".jar",
            ".war",
            ".ear",
            ".class",
            ".pyc",
            ".so",
            ".dll",
            ".exe",
            ".bin",
            ".dat",
        }

        if file_path.suffix.lower() in binary_extensions:
            return True

        # Check first 8192 bytes for null bytes
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return True
        except Exception:
            pass

        return False
