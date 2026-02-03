"""Phase 6: Test Generation Agents.

Agents for test analysis and generation.

Status: PLANNED - Template only
"""

from crewai import Agent


def create_test_analyst() -> Agent:
    """Create Test Analyst agent.
    
    Role: Analyze code for test requirements.
    Goal: Identify what needs to be tested and how.
    """
    return Agent(
        role="Senior Test Analyst",
        goal="Analyze code to identify comprehensive test requirements",
        backstory="""You are a senior test analyst with expertise in test strategy 
        and planning. You analyze code to identify critical paths, edge cases, 
        and integration points that require testing. You create test plans that 
        ensure high coverage with minimal redundancy.""",
        verbose=True,
        allow_delegation=False,
    )


def create_test_generator() -> Agent:
    """Create Test Generator agent.
    
    Role: Write test code.
    Goal: Generate comprehensive, maintainable tests.
    """
    return Agent(
        role="Senior Test Developer",
        goal="Generate comprehensive, maintainable test code",
        backstory="""You are a senior test developer with expertise in multiple 
        testing frameworks. You write clean, maintainable tests that are easy 
        to understand and maintain. You follow testing best practices and 
        ensure proper test isolation and data management.""",
        verbose=True,
        allow_delegation=False,
    )


def create_coverage_analyst() -> Agent:
    """Create Coverage Analyst agent.
    
    Role: Analyze and improve test coverage.
    Goal: Ensure adequate test coverage across the codebase.
    """
    return Agent(
        role="Test Coverage Specialist",
        goal="Analyze test coverage and identify gaps for improvement",
        backstory="""You are a test coverage specialist who ensures adequate 
        testing across the codebase. You analyze coverage reports to identify 
        untested code paths, prioritize coverage gaps by risk, and recommend 
        additional tests to improve quality.""",
        verbose=True,
        allow_delegation=False,
    )
