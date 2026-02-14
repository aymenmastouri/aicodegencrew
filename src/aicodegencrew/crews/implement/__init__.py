"""Implement Crew - Code Generation via CrewAI agents.

Phase 6 (implement) crew with 3 agents:
- Senior Developer: reads files, generates code, heals build errors
- Tester: writes tests matching existing patterns
- DevOps Engineer: runs builds, parses errors, reports results
"""

from .crew import ImplementCrew

__all__ = ["ImplementCrew"]
