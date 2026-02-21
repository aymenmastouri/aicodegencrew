"""Embedder configuration for CrewAI crews."""
import os


def get_crew_embedder() -> dict:
    """Return embedder config for CrewAI Crew constructor.

    Used when ``memory=True`` or ``knowledge_sources`` is set on a Crew.
    Adding it to all Crew constructors is a no-op until memory is enabled,
    but removes the blocker for future memory usage (avoids OpenAI default).
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("EMBED_MODEL", "nomic-embed-text")
    return {
        "provider": "ollama",
        "config": {
            "model": model,
            "url": base_url,
        },
    }
