"""Repository discovery tool for finding repo root and submodules."""

import os
from pathlib import Path
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class RepoDiscoveryInput(BaseModel):
    """Input schema for RepoDiscoveryTool."""
    repo_path: str = Field(..., description="Path to the repository to discover")
    include_submodules: bool = Field(default=True, description="Whether to include git submodules")


class RepoDiscoveryTool(BaseTool):
    name: str = "repo_discovery"
    description: str = (
        "Discovers repository structure including root path, git information, "
        "and submodules if present. Returns paths to scan."
    )
    args_schema: Type[BaseModel] = RepoDiscoveryInput
    
    def _run(self, repo_path: str, include_submodules: bool = True) -> Dict[str, Any]:
        """Discover repository structure.
        
        Args:
            repo_path: Path to repository
            include_submodules: Whether to include submodules
            
        Returns:
            Dictionary with discovery results
        """
        repo_path = Path(repo_path).resolve()
        
        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository path does not exist: {repo_path}",
            }
        
        result = {
            "success": True,
            "repo_root": str(repo_path),
            "is_git_repo": False,
            "submodules": [],
            "scan_paths": [str(repo_path)],
        }
        
        # Check if it's a git repository
        git_dir = repo_path / ".git"
        if git_dir.exists():
            result["is_git_repo"] = True
            logger.info(f"Git repository detected at: {repo_path}")
        else:
            logger.warning(f"Not a git repository: {repo_path}")
        
        # Parse .gitmodules if present and requested
        if include_submodules and result["is_git_repo"]:
            gitmodules_path = repo_path / ".gitmodules"
            if gitmodules_path.exists():
                submodules = self._parse_gitmodules(gitmodules_path, repo_path)
                result["submodules"] = submodules
                
                # Add existing submodule paths to scan_paths
                for submodule in submodules:
                    if submodule["exists"]:
                        result["scan_paths"].append(submodule["path"])
                        logger.info(f"Submodule found: {submodule['name']} at {submodule['path']}")
                    else:
                        logger.warning(f"Submodule not checked out: {submodule['name']}")
        
        return result
    
    def _parse_gitmodules(self, gitmodules_path: Path, repo_root: Path) -> List[Dict[str, Any]]:
        """Parse .gitmodules file.
        
        Args:
            gitmodules_path: Path to .gitmodules file
            repo_root: Repository root path
            
        Returns:
            List of submodule information dictionaries
        """
        submodules = []
        current_submodule = {}
        
        try:
            with open(gitmodules_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    
                    if line.startswith("[submodule"):
                        # Save previous submodule if exists
                        if current_submodule:
                            submodules.append(self._finalize_submodule(current_submodule, repo_root))
                        
                        # Extract submodule name
                        name = line.split('"')[1] if '"' in line else ""
                        current_submodule = {"name": name}
                    
                    elif "=" in line and current_submodule:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "path":
                            current_submodule["relative_path"] = value
                        elif key == "url":
                            current_submodule["url"] = value
                
                # Save last submodule
                if current_submodule:
                    submodules.append(self._finalize_submodule(current_submodule, repo_root))
        
        except Exception as e:
            logger.error(f"Error parsing .gitmodules: {e}")
        
        return submodules
    
    def _finalize_submodule(self, submodule: Dict[str, str], repo_root: Path) -> Dict[str, Any]:
        """Finalize submodule information.
        
        Args:
            submodule: Submodule dictionary
            repo_root: Repository root path
            
        Returns:
            Complete submodule information
        """
        relative_path = submodule.get("relative_path", "")
        full_path = repo_root / relative_path
        
        return {
            "name": submodule.get("name", ""),
            "relative_path": relative_path,
            "path": str(full_path),
            "url": submodule.get("url", ""),
            "exists": full_path.exists(),
        }
