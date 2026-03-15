"""Crews — CrewAI agents for phases that require true iterative tool use.

Only phases where the next action depends on the previous result use agents:
  - implement: CodegenCrew  (code generation with tool feedback loops)
  - verify:    TestingCrew  (test generation and validation)

All other phases use Pipeline + LLM (see pipelines/).
"""
