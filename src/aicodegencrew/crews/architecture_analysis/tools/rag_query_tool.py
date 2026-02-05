"""
RAG Query Tool - ChromaDB Semantic Search

CrewAI Best Practice: Use semantic search to find relevant code context
without loading the entire codebase into context.

Usage:
- rag_query(query="security annotations", limit=10)
- rag_query(query="TODO FIXME", limit=20)
"""

import os
from pathlib import Path
from typing import Type, Dict, Any, Optional, List, ClassVar
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import RAG_MAX_RESPONSE_CHARS, MAX_SNIPPET_LENGTH, truncate_response

logger = setup_logger(__name__)


class RAGQueryInput(BaseModel):
    """Input schema for RAGQueryTool."""
    query: str = Field(
        ...,
        description="Semantic search query (e.g., 'security annotations', 'error handling patterns', 'TODO FIXME')"
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return (default 10, max 20)"
    )
    file_filter: str = Field(
        default="",
        description="Optional: filter by file path pattern (e.g., 'Service.java', 'Controller')"
    )


class RAGQueryTool(BaseTool):
    """
    ChromaDB semantic search for code context.
    
    CrewAI Best Practice:
    - Semantic search finds relevant code snippets
    - Much more efficient than reading entire files
    - Supports natural language queries
    
    Usage Examples:
    1. rag_query(query="@PreAuthorize security") - Find security annotations
    2. rag_query(query="TODO FIXME HACK") - Find technical debt markers
    3. rag_query(query="Workflow state transition") - Find business logic
    """
    
    name: str = "rag_query"
    description: str = (
        "Semantic search in the indexed codebase via ChromaDB. "
        "Use natural language queries to find relevant code snippets. "
        "Examples: 'security annotations', 'TODO FIXME', 'error handling'"
    )
    args_schema: Type[BaseModel] = RAGQueryInput
    
    # Configuration - Default paths to check (in order)
    chroma_dir: str = ""  # Will be auto-detected
    collection_name: str = "repo_docs"
    
    _client: Optional[Any] = None
    _collection: Optional[Any] = None
    
    # Standard locations for ChromaDB (ClassVar = not a Pydantic field)
    CHROMA_PATHS: ClassVar[List[str]] = [
        ".cache/.chroma",      # Primary location (from indexing pipeline)
        ".chroma_db",          # Legacy location
        ".chroma",             # Alternative
    ]
    
    def __init__(self, chroma_dir: str = None, **kwargs):
        """Initialize with optional chroma dir override."""
        super().__init__(**kwargs)
        if chroma_dir:
            self.chroma_dir = chroma_dir
    
    def _find_chroma_path(self) -> Optional[str]:
        """Find ChromaDB in standard locations."""
        # Check explicit config first
        if self.chroma_dir and Path(self.chroma_dir).exists():
            return self.chroma_dir
        
        # Check environment variable
        env_path = os.getenv("CHROMA_DIR")
        if env_path and Path(env_path).exists():
            return env_path
        
        # Check standard locations relative to knowledge dir
        knowledge_dir = Path("knowledge/architecture")
        if knowledge_dir.exists():
            base_dir = Path.cwd()
        else:
            base_dir = Path(__file__).parent.parent.parent.parent.parent.parent  # Up to project root
        
        for rel_path in self.CHROMA_PATHS:
            full_path = base_dir / rel_path
            if full_path.exists():
                logger.info(f"Found ChromaDB at: {full_path}")
                return str(full_path)
        
        return None
    
    def _get_collection(self):
        """Get ChromaDB collection with lazy initialization."""
        if self._collection is not None:
            return self._collection
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            chroma_path = self._find_chroma_path()
            
            if not chroma_path or not Path(chroma_path).exists():
                logger.warning(f"ChromaDB not found. Searched paths: {self.CHROMA_PATHS}")
                return None
            
            self._client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                )
            )
            
            # Get collection (don't create if not exists)
            try:
                self._collection = self._client.get_collection(self.collection_name)
                logger.info(f"Connected to ChromaDB collection: {self.collection_name}")
            except Exception:
                logger.warning(f"Collection '{self.collection_name}' not found")
                return None
            
            return self._collection
            
        except ImportError:
            logger.error("chromadb not installed. Run: pip install chromadb")
            return None
        except Exception as e:
            logger.error(f"ChromaDB error: {e}")
            return None
    
    def _run(
        self,
        query: str,
        limit: int = 10,
        file_filter: str = "",
    ) -> str:
        """
        Execute semantic search.
        
        Args:
            query: Natural language search query
            limit: Max results (capped at 20)
            file_filter: Optional file path filter
            
        Returns:
            JSON string with matching code snippets
        """
        import json
        
        try:
            collection = self._get_collection()
            
            if collection is None:
                return json.dumps({
                    "error": "ChromaDB not available. Run Phase 0 (indexing) first.",
                    "results": []
                })
            
            # Hard cap limit - reduced to prevent context overflow
            limit = min(limit, 10)
            
            # Build where filter if file_filter is specified
            where_filter = None
            if file_filter:
                where_filter = {"file_path": {"$contains": file_filter}}
            
            # Execute semantic search
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results with TOKEN BUDGET
            formatted_results = []
            
            if results and results.get("documents"):
                documents = results["documents"][0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 0
                    
                    # Truncate content to MAX_SNIPPET_LENGTH
                    content = doc[:MAX_SNIPPET_LENGTH] if doc else ""
                    if doc and len(doc) > MAX_SNIPPET_LENGTH:
                        content += "..."
                    
                    formatted_results.append({
                        "file_path": metadata.get("file_path", "unknown"),
                        "chunk_type": metadata.get("chunk_type", "code"),
                        "relevance_score": round(1 - distance, 3) if distance else 0,
                        "content": content,
                    })
            
            output = {
                "query": query,
                "file_filter": file_filter,
                "result_count": len(formatted_results),
                "results": formatted_results
            }
            
            # TOKEN BUDGET: Final truncation check
            output_str = json.dumps(output, indent=2, ensure_ascii=False)
            output_str = truncate_response(output_str, RAG_MAX_RESPONSE_CHARS)
            
            return output_str
            
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            import json
            return json.dumps({"error": str(e), "results": []})
