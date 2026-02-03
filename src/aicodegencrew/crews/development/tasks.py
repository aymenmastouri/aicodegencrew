"""Phase 4: Development Planning Tasks.

Tasks for backlog generation and prioritization.

Status: PLANNED - Template only
"""

from crewai import Task, Agent
from typing import List


def create_debt_analysis_task(agent: Agent) -> Task:
    """Create architecture debt analysis task."""
    return Task(
        description="""
        TASK: Architecture Debt Analysis
        
        Analyze architecture documentation for technical debt:
        
        1. STRUCTURAL DEBT
           - Circular dependencies
           - Missing abstraction layers
           - Tight coupling patterns
        
        2. DOCUMENTATION DEBT
           - UNKNOWN markers in documentation
           - Missing evidence references
           - Incomplete sections
        
        3. PATTERN VIOLATIONS
           - Anti-patterns detected
           - Inconsistent naming conventions
           - Missing design patterns
        
        4. RISK ASSESSMENT
           - Single points of failure
           - Scalability concerns
           - Security gaps
        
        OUTPUT: JSON list of debt items with severity and location
        """,
        expected_output="Architecture debt analysis report",
        agent=agent,
    )


def create_backlog_generation_task(agent: Agent, context: List[Task]) -> Task:
    """Create backlog generation task."""
    return Task(
        description="""
        TASK: Backlog Item Generation
        
        Generate structured work items from analysis:
        
        1. USER STORIES (for feature work)
           - Title, Description, Acceptance Criteria
           - Story points estimate (1, 2, 3, 5, 8, 13)
        
        2. TECHNICAL TASKS (for debt)
           - Title, Description, Definition of Done
           - Effort estimate in hours
        
        3. SPIKES (for unknowns)
           - Research question
           - Time-box in hours
           - Expected outcome
        
        4. BUGS (for issues found)
           - Title, Steps to reproduce
           - Expected vs Actual behavior
        
        OUTPUT FILE: development/backlog.json
        """,
        expected_output="Structured backlog items in JSON",
        agent=agent,
        context=context,
        output_file="development/backlog.json",
    )


def create_prioritization_task(agent: Agent, context: List[Task]) -> Task:
    """Create prioritization task."""
    return Task(
        description="""
        TASK: Backlog Prioritization
        
        Prioritize backlog items using WSJF or similar:
        
        1. IMPACT ASSESSMENT
           - Business value (1-10)
           - Technical risk reduction (1-10)
           - Urgency (1-10)
        
        2. EFFORT ESTIMATION
           - Complexity (1-10)
           - Dependencies count
           - Risk of delay
        
        3. PRIORITY CALCULATION
           - Priority score = (Value + Risk + Urgency) / Effort
           - Group into: Critical, High, Medium, Low
        
        4. SPRINT PLANNING
           - Group items into suggested sprints
           - Consider dependencies
        
        OUTPUT FILE: development/prioritized-backlog.md
        """,
        expected_output="Prioritized backlog with sprint suggestions",
        agent=agent,
        context=context,
        output_file="development/prioritized-backlog.md",
    )
