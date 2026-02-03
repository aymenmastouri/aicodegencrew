"""Tests for repository discovery tool."""

import pytest
from pathlib import Path
from aicodegencrew.pipelines.tools.repo_discovery_tool import RepoDiscoveryTool


@pytest.fixture
def discovery_tool():
    """Fixture for discovery tool."""
    return RepoDiscoveryTool()


def test_discover_nonexistent_repo(discovery_tool):
    """Test discovery of non-existent repository."""
    result = discovery_tool._run("/nonexistent/path")
    
    assert result["success"] is False
    assert "does not exist" in result["error"]


def test_discover_non_git_directory(tmp_path, discovery_tool):
    """Test discovery of directory without .git."""
    result = discovery_tool._run(str(tmp_path))
    
    assert result["success"] is True
    assert result["is_git_repo"] is False
    assert result["repo_root"] == str(tmp_path)
    assert len(result["scan_paths"]) == 1


def test_discover_git_repository(tmp_path, discovery_tool):
    """Test discovery of git repository."""
    # Create .git directory
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    
    result = discovery_tool._run(str(tmp_path))
    
    assert result["success"] is True
    assert result["is_git_repo"] is True
    assert result["repo_root"] == str(tmp_path)


def test_discover_with_gitmodules(tmp_path, discovery_tool):
    """Test discovery with .gitmodules file."""
    # Create .git directory
    (tmp_path / ".git").mkdir()
    
    # Create .gitmodules file
    gitmodules_content = """[submodule "lib/common"]
\tpath = lib/common
\turl = https://github.com/example/common.git
[submodule "vendor/plugin"]
\tpath = vendor/plugin
\turl = https://github.com/example/plugin.git
"""
    (tmp_path / ".gitmodules").write_text(gitmodules_content)
    
    # Create one submodule directory (simulate checked out)
    (tmp_path / "lib" / "common").mkdir(parents=True)
    
    result = discovery_tool._run(str(tmp_path), include_submodules=True)
    
    assert result["success"] is True
    assert len(result["submodules"]) == 2
    
    # Check first submodule
    assert result["submodules"][0]["name"] == "lib/common"
    assert result["submodules"][0]["exists"] is True
    
    # Check second submodule (not checked out)
    assert result["submodules"][1]["name"] == "vendor/plugin"
    assert result["submodules"][1]["exists"] is False
    
    # Scan paths should include existing submodule
    assert len(result["scan_paths"]) == 2  # root + existing submodule


def test_discover_ignores_submodules_when_disabled(tmp_path, discovery_tool):
    """Test that submodules are ignored when include_submodules=False."""
    (tmp_path / ".git").mkdir()
    
    gitmodules_content = """[submodule "lib/common"]
\tpath = lib/common
\turl = https://github.com/example/common.git
"""
    (tmp_path / ".gitmodules").write_text(gitmodules_content)
    (tmp_path / "lib" / "common").mkdir(parents=True)
    
    result = discovery_tool._run(str(tmp_path), include_submodules=False)
    
    assert result["success"] is True
    assert len(result["submodules"]) == 0
    assert len(result["scan_paths"]) == 1  # Only root


def test_parse_malformed_gitmodules(tmp_path, discovery_tool):
    """Test parsing of malformed .gitmodules file."""
    (tmp_path / ".git").mkdir()
    
    # Malformed .gitmodules
    (tmp_path / ".gitmodules").write_text("invalid content\nno proper format")
    
    result = discovery_tool._run(str(tmp_path), include_submodules=True)
    
    # Should not crash, but may have empty submodules
    assert result["success"] is True
    assert isinstance(result["submodules"], list)
