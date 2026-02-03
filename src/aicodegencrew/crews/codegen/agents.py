"""Phase 5: Code Generation Agents.

Agents for code design, generation, and review.

Status: PLANNED - Template only
"""

from crewai import Agent


def create_code_architect() -> Agent:
    """Create Code Architect agent.
    
    Role: Design code structure and interfaces.
    Goal: Create clean, maintainable code designs.
    """
    return Agent(
        role="Senior Code Architect",
        goal="Design clean, maintainable code structures following best practices",
        backstory="""You are a senior code architect with expertise in designing 
        clean, maintainable code. You follow SOLID principles, design patterns, 
        and industry best practices. You create code designs that are easy to 
        implement, test, and maintain.""",
        verbose=True,
        allow_delegation=False,
    )


def create_code_generator() -> Agent:
    """Create Code Generator agent.
    
    Role: Write implementation code.
    Goal: Generate high-quality, tested code.
    """
    return Agent(
        role="Senior Software Developer",
        goal="Generate high-quality, tested code following the design specifications",
        backstory="""You are a senior software developer with expertise in multiple 
        programming languages. You write clean, efficient code with proper error 
        handling, logging, and documentation. You always include unit tests for 
        the code you generate.""",
        verbose=True,
        allow_delegation=False,
    )


def create_code_reviewer() -> Agent:
    """Create Code Reviewer agent.
    
    Role: Review generated code for quality.
    Goal: Ensure code meets quality standards.
    """
    return Agent(
        role="Code Review Specialist",
        goal="Review code for quality, security, and maintainability",
        backstory="""You are a code review specialist who ensures all generated 
        code meets quality standards. You check for security vulnerabilities, 
        performance issues, code smells, and adherence to coding standards. 
        You provide constructive feedback for improvements.""",
        verbose=True,
        allow_delegation=False,
    )
