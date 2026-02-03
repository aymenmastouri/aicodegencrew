"""Phase 3: Review Crew Tasks.

Tasks for consistency validation and quality reporting.

Status: PLANNED - Template only
"""

from crewai import Task, Agent
from typing import List


def create_consistency_check_task(agent: Agent) -> Task:
    """Create consistency check task.
    
    Validates:
    - All containers in facts appear in C4 container diagram
    - All components in facts appear in C4 component diagrams
    - All relations in facts are represented in diagrams
    - No invented elements in outputs
    """
    return Task(
        description="""
        TASK: Consistency Validation
        
        Compare architecture_facts.json with generated outputs:
        
        1. CONTAINER CONSISTENCY
           - Check all containers from facts appear in c4/c4-container.md
           - Verify container names match exactly
           - Flag any containers in output not in facts (hallucinations)
        
        2. COMPONENT CONSISTENCY
           - Check all components from facts appear in c4/c4-components-*.md
           - Verify component-container assignments match
           - Flag any components in output not in facts
        
        3. RELATION CONSISTENCY
           - Check all relations from facts are represented
           - Verify relation types match (uses, implements, etc.)
        
        4. EVIDENCE CONSISTENCY
           - Verify all evidence IDs referenced in outputs exist in evidence_map.json
        
        OUTPUT: JSON report with:
        - missing_in_output: elements from facts not in outputs
        - hallucinations: elements in outputs not in facts
        - mismatches: elements with different values
        """,
        expected_output="JSON consistency report",
        agent=agent,
    )


def create_quality_audit_task(agent: Agent) -> Task:
    """Create quality audit task.
    
    Audits documentation quality and completeness.
    """
    return Task(
        description="""
        TASK: Documentation Quality Audit
        
        Audit the generated documentation for quality:
        
        1. C4 DIAGRAMS
           - Check all required diagrams exist (context, container, components)
           - Verify Draw.io XML is valid
           - Check diagram descriptions are present
        
        2. ARC42 CHAPTERS
           - Check all required chapters exist (01, 03, 05, 06)
           - Verify each chapter has required sections
           - Check evidence references are present
        
        3. CONTENT QUALITY
           - Check for placeholder text or TODOs
           - Verify no empty sections
           - Check for UNKNOWN markers (acceptable but tracked)
        
        OUTPUT: Quality score (0-100) with detailed findings
        """,
        expected_output="Quality audit report with score",
        agent=agent,
    )


def create_report_generation_task(agent: Agent, context: List[Task]) -> Task:
    """Create report generation task.
    
    Synthesizes all findings into a comprehensive report.
    """
    return Task(
        description="""
        TASK: Generate Quality Report
        
        Synthesize all validation findings into a comprehensive report:
        
        1. EXECUTIVE SUMMARY
           - Overall quality score
           - Key findings summary
           - Recommendation priority
        
        2. DETAILED FINDINGS
           - Consistency issues with severity
           - Quality gaps with impact
           - Evidence coverage metrics
        
        3. RECOMMENDATIONS
           - Immediate fixes required
           - Improvements for next iteration
           - Process improvements
        
        OUTPUT FILE: quality/synthesis-report.md
        """,
        expected_output="Comprehensive quality report in Markdown",
        agent=agent,
        context=context,
        output_file="quality/synthesis-report.md",
    )
