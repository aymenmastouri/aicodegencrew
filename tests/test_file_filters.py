"""Tests for file filtering utilities."""

import pytest
from pathlib import Path
from aicodegencrew.shared.utils.file_filters import should_include_file, collect_files, DEFAULT_INCLUDE_PATTERNS, DEFAULT_EXCLUDE_PATTERNS


def test_should_include_java_file():
    """Test that Java files are included."""
    path = Path("src/main/java/com/example/Service.java")
    assert should_include_file(path) is True


def test_should_include_yaml_file():
    """Test that YAML files are included."""
    path = Path("config/application.yml")
    assert should_include_file(path) is True


def test_should_exclude_class_file():
    """Test that .class files are excluded."""
    path = Path("target/classes/com/example/Service.class")
    assert should_include_file(path) is False


def test_should_exclude_node_modules():
    """Test that node_modules files are excluded."""
    path = Path("node_modules/package/index.js")
    assert should_include_file(path) is False


def test_should_exclude_git_directory():
    """Test that .git directory files are excluded."""
    path = Path(".git/config")
    assert should_include_file(path) is False


def test_custom_include_pattern():
    """Test custom include patterns."""
    path = Path("custom/file.txt")
    assert should_include_file(path, include_patterns=["**/*.txt"]) is True
    assert should_include_file(path, include_patterns=["**/*.java"]) is False


def test_custom_exclude_pattern():
    """Test custom exclude patterns."""
    path = Path("src/temp/file.java")
    assert should_include_file(
        path,
        include_patterns=["**/*.java"],
        exclude_patterns=["**/temp/**"]
    ) is False


def test_collect_files_empty_directory(tmp_path):
    """Test collecting files from empty directory."""
    files = collect_files(tmp_path)
    assert len(files) == 0


def test_collect_files_with_java_files(tmp_path):
    """Test collecting Java files from directory."""
    # Create test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Test.java").write_text("public class Test {}")
    (tmp_path / "src" / "Test.class").write_text("binary")
    
    files = collect_files(tmp_path)
    
    # Should find .java but not .class
    assert len(files) == 1
    assert files[0].name == "Test.java"


def test_collect_files_respects_exclude_patterns(tmp_path):
    """Test that collect_files respects exclude patterns."""
    # Create test structure
    (tmp_path / "src").mkdir()
    (tmp_path / "target").mkdir()
    
    (tmp_path / "src" / "Main.java").write_text("class Main {}")
    (tmp_path / "target" / "Main.class").write_text("binary")
    
    files = collect_files(tmp_path)
    
    # Should only find the .java file, not .class in target
    assert len(files) == 1
    assert files[0].name == "Main.java"
