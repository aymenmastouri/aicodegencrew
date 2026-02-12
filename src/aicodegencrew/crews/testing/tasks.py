"""Phase 6: Test Generation Tasks.

Tasks for test analysis, generation, and coverage.

Status: PLANNED - Template only
"""

from crewai import Agent, Task


def create_test_analysis_task(agent: Agent) -> Task:
    """Create test analysis task."""
    return Task(
        description="""
        TASK: Test Requirements Analysis

        Analyze the codebase for test requirements:

        1. UNIT TEST REQUIREMENTS
           - Public methods that need testing
           - Edge cases to cover
           - Error conditions to test

        2. INTEGRATION TEST REQUIREMENTS
           - API endpoints to test
           - Database operations to verify
           - External service integrations

        3. E2E TEST SCENARIOS
           - Critical user workflows
           - Business process validations
           - Performance scenarios

        4. PRIORITY ASSESSMENT
           - Critical paths (must test)
           - High risk areas (should test)
           - Low risk areas (nice to test)

        OUTPUT: Test requirements document with priorities
        """,
        expected_output="Test requirements analysis",
        agent=agent,
    )


def create_unit_test_generation_task(agent: Agent, context: list[Task]) -> Task:
    """Create unit test generation task."""
    return Task(
        description="""
        TASK: Unit Test Generation

        Generate unit tests based on analysis:

        1. TEST STRUCTURE
           - One test file per source file
           - Descriptive test method names
           - Proper setup and teardown

        2. TEST CASES
           - Happy path tests
           - Edge case tests
           - Error handling tests
           - Boundary condition tests

        3. MOCKING
           - Mock external dependencies
           - Use appropriate mocking framework
           - Verify mock interactions

        4. ASSERTIONS
           - Clear, specific assertions
           - Meaningful error messages
           - No redundant assertions

        OUTPUT: Unit test files ready for execution
        """,
        expected_output="Unit test code files",
        agent=agent,
        context=context,
    )


def create_coverage_analysis_task(agent: Agent, context: list[Task]) -> Task:
    """Create coverage analysis task."""
    return Task(
        description="""
        TASK: Coverage Analysis and Improvement

        Analyze test coverage and recommend improvements:

        1. COVERAGE METRICS
           - Line coverage percentage
           - Branch coverage percentage
           - Method coverage percentage

        2. GAP ANALYSIS
           - Untested code paths
           - Partially tested methods
           - Missing edge cases

        3. RISK ASSESSMENT
           - High-risk untested code
           - Critical paths without coverage
           - Security-sensitive untested code

        4. RECOMMENDATIONS
           - Priority tests to add
           - Effort estimates
           - Expected coverage improvement

        OUTPUT FILE: testing/coverage-report.md
        """,
        expected_output="Coverage analysis report",
        agent=agent,
        context=context,
        output_file="testing/coverage-report.md",
    )
