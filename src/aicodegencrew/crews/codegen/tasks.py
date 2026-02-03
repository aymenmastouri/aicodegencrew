"""Phase 5: Code Generation Tasks.

Tasks for code design, generation, and review.

Status: PLANNED - Template only
"""

from crewai import Task, Agent
from typing import List


def create_design_task(agent: Agent, backlog_item: dict) -> Task:
    """Create code design task for a backlog item."""
    return Task(
        description=f"""
        TASK: Code Design
        
        Design code structure for backlog item:
        Title: {backlog_item.get('title', 'Unknown')}
        Type: {backlog_item.get('type', 'Unknown')}
        
        1. INTERFACE DESIGN
           - Define public interfaces
           - Define data structures
           - Define dependencies
        
        2. CLASS STRUCTURE
           - Classes and their responsibilities
           - Methods and signatures
           - Properties and types
        
        3. INTEGRATION POINTS
           - How it integrates with existing code
           - Required modifications to existing code
           - New dependencies needed
        
        OUTPUT: Design document with code structure
        """,
        expected_output="Code design document",
        agent=agent,
    )


def create_implementation_task(agent: Agent, context: List[Task]) -> Task:
    """Create code implementation task."""
    return Task(
        description="""
        TASK: Code Implementation
        
        Implement the code based on the design:
        
        1. MAIN CODE
           - Implement all classes and methods
           - Add proper error handling
           - Add logging statements
           - Add documentation comments
        
        2. UNIT TESTS
           - Test all public methods
           - Test edge cases
           - Test error handling
           - Aim for 80%+ coverage
        
        3. INTEGRATION CODE
           - Required changes to existing code
           - New configuration entries
           - Database migrations if needed
        
        OUTPUT: Complete code files ready for PR
        """,
        expected_output="Implementation code with tests",
        agent=agent,
        context=context,
    )


def create_review_task(agent: Agent, context: List[Task]) -> Task:
    """Create code review task."""
    return Task(
        description="""
        TASK: Code Review
        
        Review the generated code for quality:
        
        1. CODE QUALITY
           - Clean code principles
           - Naming conventions
           - Code organization
        
        2. SECURITY
           - Input validation
           - Authentication/Authorization
           - SQL injection prevention
           - XSS prevention
        
        3. PERFORMANCE
           - Algorithm efficiency
           - Database queries
           - Memory usage
        
        4. MAINTAINABILITY
           - Test coverage
           - Documentation
           - Complexity metrics
        
        OUTPUT: Review report with findings and recommendations
        """,
        expected_output="Code review report",
        agent=agent,
        context=context,
    )
