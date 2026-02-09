"""Tests for chunker tool."""

import pytest
from aicodegencrew.pipelines.indexing.chunker_tool import ChunkerTool


@pytest.fixture
def chunker_tool():
    """Fixture for chunker tool."""
    return ChunkerTool()


def test_chunker_small_text(chunker_tool):
    """Test chunking text smaller than chunk size."""
    files = [
        {"path": "test.txt", "content": "Small text content"}
    ]
    
    result = chunker_tool._run(files, chunk_chars=100, chunk_overlap=20)
    
    assert result["success"] is True
    assert len(result["chunks"]) == 1
    assert result["chunks"][0]["chunk_index"] == 0
    assert result["chunks"][0]["text"] == "Small text content"


def test_chunker_large_text_with_overlap(chunker_tool):
    """Test chunking large text with overlap."""
    long_text = "A" * 1000 + "B" * 1000
    files = [
        {"path": "test.txt", "content": long_text}
    ]
    
    result = chunker_tool._run(files, chunk_chars=500, chunk_overlap=100)
    
    assert result["success"] is True
    assert len(result["chunks"]) > 1
    
    # Check overlap exists
    chunk1_end = result["chunks"][0]["text"][-100:]
    chunk2_start = result["chunks"][1]["text"][:100]
    assert chunk1_end == chunk2_start


def test_chunker_deterministic_ids(chunker_tool):
    """Test that chunk IDs are deterministic."""
    files = [
        {"path": "test.txt", "content": "Test content for deterministic IDs"}
    ]
    
    result1 = chunker_tool._run(files, chunk_chars=100, chunk_overlap=20)
    result2 = chunker_tool._run(files, chunk_chars=100, chunk_overlap=20)
    
    assert result1["chunks"][0]["chunk_id"] == result2["chunks"][0]["chunk_id"]


def test_chunker_multiple_files(chunker_tool):
    """Test chunking multiple files."""
    files = [
        {"path": "file1.txt", "content": "Content of file 1"},
        {"path": "file2.txt", "content": "Content of file 2"},
    ]
    
    result = chunker_tool._run(files, chunk_chars=100, chunk_overlap=20)
    
    assert result["success"] is True
    assert len(result["chunks"]) == 2
    assert result["stats"]["total_files"] == 2


def test_chunker_empty_files(chunker_tool):
    """Test chunking with empty files."""
    files = [
        {"path": "empty.txt", "content": ""},
        {"path": "nonempty.txt", "content": "Some content"},
    ]
    
    result = chunker_tool._run(files, chunk_chars=100, chunk_overlap=20)
    
    assert result["success"] is True
    # Should only create chunks for non-empty file
    assert len(result["chunks"]) == 1
    assert result["chunks"][0]["file_path"] == "nonempty.txt"


def test_chunk_metadata(chunker_tool):
    """Test that chunk metadata is correctly set."""
    files = [
        {"path": "test.txt", "content": "Test content"}
    ]
    
    result = chunker_tool._run(files, chunk_chars=100, chunk_overlap=20)
    
    chunk = result["chunks"][0]
    assert "chunk_id" in chunk
    assert "file_path" in chunk
    assert "chunk_index" in chunk
    assert "text" in chunk
    assert "start_char" in chunk
    assert "end_char" in chunk
    assert chunk["file_path"] == "test.txt"
