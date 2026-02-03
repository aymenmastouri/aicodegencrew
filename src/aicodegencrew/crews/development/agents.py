"""Phase 4: Development Planning Agents.

Agents for architecture analysis and backlog generation.

Status: PLANNED - Template only
"""

from crewai import Agent


def create_architecture_analyst() -> Agent:
    """Create Architecture Analyst agent.
    
    Role: Identify architecture debt, risks, and improvement areas.
    Goal: Analyze architecture for actionable improvements.
    """
    return Agent(
        role="Senior Architecture Analyst",
        goal="Identify architecture debt, technical risks, and improvement opportunities",
        backstory="""You are a senior architecture analyst with deep expertise in 
        identifying technical debt, architectural anti-patterns, and improvement 
        opportunities. You analyze architecture documentation to derive actionable 
        work items that improve system quality and maintainability.""",
        verbose=True,
        allow_delegation=False,
    )


def create_backlog_generator() -> Agent:
    """Create Backlog Generator agent.
    
    Role: Transform findings into structured work items.
    Goal: Create JIRA-ready work items with acceptance criteria.
    """
    return Agent(
        role="Technical Product Owner",
        goal="Generate structured backlog items from architecture analysis",
        backstory="""You are a technical product owner who transforms architecture 
        findings into well-structured work items. You write clear user stories, 
        technical tasks, and spikes with proper acceptance criteria and 
        effort estimates.""",
        verbose=True,
        allow_delegation=False,
    )


def create_priority_assessor() -> Agent:
    """Create Priority Assessor agent.
    
    Role: Prioritize work items based on impact and effort.
    Goal: Create prioritized backlog with clear rationale.
    """
    return Agent(
        role="Technical Lead",
        goal="Prioritize work items based on business impact, technical risk, and effort",
        backstory="""You are a technical lead who excels at prioritizing work. 
        You consider business impact, technical risk, dependencies, and effort 
        to create a prioritized backlog that maximizes value delivery while 
        managing technical risk.""",
        verbose=True,
        allow_delegation=False,
    )
