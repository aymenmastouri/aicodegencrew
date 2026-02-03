"""Phase 3: Review Crew Agents.

Agents for consistency validation and quality assurance.

Status: PLANNED - Template only
"""

from crewai import Agent


def create_consistency_validator() -> Agent:
    """Create Consistency Validator agent.
    
    Role: Cross-reference architecture_facts.json with generated outputs.
    Goal: Ensure no invented elements, all facts are represented.
    """
    return Agent(
        role="Senior Quality Assurance Architect",
        goal="Validate consistency between architecture facts and generated documentation",
        backstory="""You are a senior QA architect with expertise in architecture 
        documentation validation. You ensure that all generated C4 diagrams and 
        arc42 chapters accurately reflect the source architecture facts without 
        any invented or missing elements.""",
        verbose=True,
        allow_delegation=False,
    )


def create_quality_auditor() -> Agent:
    """Create Quality Auditor agent.
    
    Role: Check documentation completeness and quality.
    Goal: Ensure all required sections are present and well-documented.
    """
    return Agent(
        role="Documentation Quality Auditor",
        goal="Audit documentation completeness and quality standards",
        backstory="""You are a documentation quality expert who ensures that 
        architecture documentation meets professional standards. You check for 
        completeness, clarity, and adherence to C4 and arc42 conventions.""",
        verbose=True,
        allow_delegation=False,
    )


def create_report_generator() -> Agent:
    """Create Report Generator agent.
    
    Role: Generate quality reports and recommendations.
    Goal: Produce actionable quality improvement reports.
    """
    return Agent(
        role="Quality Report Specialist",
        goal="Generate comprehensive quality reports with actionable recommendations",
        backstory="""You are a technical writer specialized in quality reporting. 
        You synthesize validation findings into clear, actionable reports that 
        help teams improve their architecture documentation.""",
        verbose=True,
        allow_delegation=False,
    )
