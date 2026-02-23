"""Issue Triage Crew — deterministic analysis + LLM synthesis.

Classifies issues, finds entry points, calculates blast radius,
and produces dual output: customer summary + developer brief.
"""

from .crew import TriageCrew

__all__ = ["TriageCrew"]
