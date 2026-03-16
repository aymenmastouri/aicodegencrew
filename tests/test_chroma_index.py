"""Tests for vector store index tool (Qdrant backend)."""

import shutil
import tempfile

import pytest

from aicodegencrew.pipelines.indexing.chroma_index_tool import ChromaIndexTool


@pytest.fixture
def temp_discover_dir():
    """Create temporary discover directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def index_tool(temp_discover_dir, monkeypatch):
    """Fixture for index tool with temporary directory."""
    monkeypatch.setenv("DISCOVER_DIR", temp_discover_dir)
    tool = ChromaIndexTool()
    tool.chroma_dir = temp_discover_dir
    return tool


def test_upsert_chunks(index_tool):
    """Test upserting chunks to vector store."""
    chunks = [
        {
            "chunk_id": "test_001",
            "file_path": "test.txt",
            "chunk_index": 0,
            "text": "Test content",
            "start_char": 0,
            "end_char": 12,
        }
    ]
    embeddings = [[0.1] * 768]  # Mock embedding

    result = index_tool._run(
        operation="upsert", chunks=chunks, embeddings=embeddings, collection_name="test_collection"
    )

    assert result["success"] is True
    assert result["upserted_count"] == 1


def test_upsert_empty_chunks(index_tool):
    """Test upserting empty chunks list."""
    result = index_tool._run(operation="upsert", chunks=[], embeddings=[], collection_name="test_collection")

    assert result["success"] is False
    assert "No chunks" in result["error"]


def test_upsert_mismatched_lengths(index_tool):
    """Test upserting with mismatched chunk and embedding counts."""
    chunks = [{"chunk_id": "test_001", "text": "Test", "file_path": "test.txt", "chunk_index": 0}]
    embeddings = [[0.1] * 768, [0.2] * 768]  # More embeddings than chunks

    result = index_tool._run(
        operation="upsert", chunks=chunks, embeddings=embeddings, collection_name="test_collection"
    )

    assert result["success"] is False
    assert "Mismatch" in result["error"]


def test_query_empty_collection(index_tool):
    """Test querying an empty collection."""
    query_embedding = [0.1] * 768

    result = index_tool._run(
        operation="query",
        query_text="test query",
        query_embedding=query_embedding,
        top_k=5,
        collection_name="empty_collection",
    )

    # Non-existent collection: Qdrant returns 404.
    # Either way the tool should not crash -- success=True with 0 results
    # or success=False with an error message are both acceptable.
    assert isinstance(result["success"], bool)
    if result["success"]:
        assert result["count"] == 0


def test_query_without_embedding(index_tool):
    """Test querying without providing embedding."""
    result = index_tool._run(
        operation="query", query_text="test query", query_embedding=[], top_k=5, collection_name="test_collection"
    )

    assert result["success"] is False
    assert "No query embedding" in result["error"]


def test_invalid_operation(index_tool):
    """Test invalid operation."""
    result = index_tool._run(operation="invalid_op", collection_name="test_collection")

    assert result["success"] is False
    assert "Unknown operation" in result["error"]


def test_upsert_and_query_roundtrip(index_tool):
    """Test full roundtrip: upsert then query."""
    # First upsert
    chunks = [
        {
            "chunk_id": "test_001",
            "file_path": "test.txt",
            "chunk_index": 0,
            "text": "Test content for searching",
            "start_char": 0,
            "end_char": 26,
        }
    ]
    embeddings = [[0.5] * 768]

    upsert_result = index_tool._run(
        operation="upsert", chunks=chunks, embeddings=embeddings, collection_name="roundtrip_test"
    )

    assert upsert_result["success"] is True

    # Then query with similar embedding
    query_embedding = [0.51] * 768  # Similar to upserted embedding

    query_result = index_tool._run(
        operation="query",
        query_text="search query",
        query_embedding=query_embedding,
        top_k=5,
        collection_name="roundtrip_test",
    )

    assert query_result["success"] is True
    assert query_result["count"] >= 1
    if query_result["count"] > 0:
        assert "chunk_id" in query_result["results"][0]
        assert "text" in query_result["results"][0]
