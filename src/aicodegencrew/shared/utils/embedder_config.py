"""Embedder configuration for CrewAI crews."""
import os


def get_crew_embedder() -> dict:
    """Return embedder config for CrewAI Crew constructor.

    When API_BASE is set (Sovereign AI Platform), uses the OpenAI-compatible
    embed endpoint (model alias "embed"). Falls back to local Ollama otherwise.
    """
    api_base = os.getenv("API_BASE", "")
    model = os.getenv("EMBED_MODEL", "nomic-embed-text")

    if api_base:
        return {
            "provider": "openai",
            "config": {
                "model": model,
                "api_base": api_base,
                "api_key": os.getenv("OPENAI_API_KEY", ""),
            },
        }

    # Fallback: local Ollama
    return {
        "provider": "ollama",
        "config": {
            "model": model,
            "url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        },
    }
