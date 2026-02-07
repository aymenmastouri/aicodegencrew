"""
RuntimeCollector - Extracts runtime behavior facts.

Detects:
- Background jobs
- Schedulers
- Async operations
- Workflow triggers
- Event handlers

Output -> runtime.json
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from .base import DimensionCollector, CollectorOutput, RawRuntimeFact, RelationHint
from ....shared.utils.logger import logger


class RuntimeCollector(DimensionCollector):
    """
    Extracts runtime behavior facts.
    """
    
    DIMENSION = "runtime"
    
    # Patterns
    SCHEDULED_PATTERN = re.compile(r'@Scheduled\s*\(([^)]+)\)')
    ASYNC_PATTERN = re.compile(r'@Async')
    EVENT_LISTENER_PATTERN = re.compile(r'@EventListener')
    TRANSACTIONAL_PATTERN = re.compile(r'@Transactional')
    
    # Spring Batch
    BATCH_JOB_PATTERN = re.compile(r'@EnableBatchProcessing|JobBuilderFactory|StepBuilderFactory')
    
    # Method signature
    METHOD_PATTERN = re.compile(r'(?:public|private|protected)?\s*(?:void|[\w<>]+)\s+(\w+)\s*\([^)]*\)')
    
    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
    
    def collect(self) -> CollectorOutput:
        """Collect runtime behavior facts."""
        self._log_start()
        
        # Process Java files
        java_files = self._find_files("*.java")
        for java_file in java_files:
            self._process_java_file(java_file)
        
        # Process Kotlin files (same annotations work)
        kotlin_files = self._find_files("*.kt")
        for kt_file in kotlin_files:
            self._process_java_file(kt_file)  # Same patterns apply
        
        self._log_end()
        return self.output
    
    def _process_java_file(self, file_path: Path):
        """Process a Java file for runtime facts."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)
        
        # Schedulers
        for match in self.SCHEDULED_PATTERN.finditer(content):
            self._extract_scheduler(match, content, lines, rel_path)
        
        # Async methods
        for match in self.ASYNC_PATTERN.finditer(content):
            self._extract_async(match, content, lines, rel_path)
        
        # Event listeners
        for match in self.EVENT_LISTENER_PATTERN.finditer(content):
            self._extract_event_listener(match, content, lines, rel_path)
        
        # Batch jobs
        if self.BATCH_JOB_PATTERN.search(content):
            self._extract_batch_jobs(content, lines, rel_path)
    
    def _extract_scheduler(self, match, content: str, lines: List[str], file_path: str):
        """Extract scheduler fact."""
        config = match.group(1)
        line_num = content[:match.start()].count('\n') + 1
        
        # Find method name
        method_match = self.METHOD_PATTERN.search(content[match.end():match.end()+200])
        method_name = method_match.group(1) if method_match else "unknown"
        
        # Parse schedule
        cron_match = re.search(r'cron\s*=\s*["\']([^"\']+)["\']', config)
        rate_match = re.search(r'fixedRate\s*=\s*(\d+)', config)
        delay_match = re.search(r'fixedDelay\s*=\s*(\d+)', config)
        
        fact = RawRuntimeFact(
            name=method_name,
            type="scheduler",
        )
        
        if cron_match:
            fact.schedule = cron_match.group(1)
            fact.metadata["schedule_type"] = "cron"
        elif rate_match:
            fact.metadata["fixed_rate_ms"] = int(rate_match.group(1))
            fact.metadata["schedule_type"] = "fixed_rate"
        elif delay_match:
            fact.metadata["fixed_delay_ms"] = int(delay_match.group(1))
            fact.metadata["schedule_type"] = "fixed_delay"
        
        fact.add_evidence(
            path=file_path,
            line_start=line_num,
            line_end=line_num + 5,
            reason=f"@Scheduled: {method_name}"
        )
        
        self.output.add_fact(fact)
    
    def _extract_async(self, match, content: str, lines: List[str], file_path: str):
        """Extract async method fact."""
        line_num = content[:match.start()].count('\n') + 1
        
        # Find method name
        method_match = self.METHOD_PATTERN.search(content[match.end():match.end()+200])
        method_name = method_match.group(1) if method_match else "unknown"
        
        fact = RawRuntimeFact(
            name=method_name,
            type="async",
            metadata={"async": True}
        )
        
        fact.add_evidence(
            path=file_path,
            line_start=line_num,
            line_end=line_num + 3,
            reason=f"@Async: {method_name}"
        )
        
        self.output.add_fact(fact)
    
    def _extract_event_listener(self, match, content: str, lines: List[str], file_path: str):
        """Extract event listener fact."""
        line_num = content[:match.start()].count('\n') + 1
        
        # Find method and event type
        method_area = content[match.end():match.end()+300]
        method_match = self.METHOD_PATTERN.search(method_area)
        
        if method_match:
            method_name = method_match.group(1)
            
            # Try to find event type from parameter
            param_match = re.search(r'\(\s*(\w+Event)\s+\w+\)', method_area)
            event_type = param_match.group(1) if param_match else "unknown"
            
            fact = RawRuntimeFact(
                name=method_name,
                type="event_listener",
                trigger=event_type,
            )
            
            fact.add_evidence(
                path=file_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"@EventListener: {method_name} handles {event_type}"
            )
            
            self.output.add_fact(fact)
    
    def _extract_batch_jobs(self, content: str, lines: List[str], file_path: str):
        """Extract Spring Batch job facts."""
        # Find Job definitions
        job_pattern = re.compile(r'Job\s+(\w+)\s*\([^)]*\)\s*\{')
        step_pattern = re.compile(r'Step\s+(\w+)\s*\([^)]*\)')
        
        for match in job_pattern.finditer(content):
            job_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            fact = RawRuntimeFact(
                name=job_name,
                type="batch_job",
            )
            
            fact.tags.append("spring-batch")
            
            fact.add_evidence(
                path=file_path,
                line_start=line_num,
                line_end=line_num + 10,
                reason=f"Spring Batch Job: {job_name}"
            )
            
            self.output.add_fact(fact)
        
        # Find Step definitions
        for match in step_pattern.finditer(content):
            step_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            fact = RawRuntimeFact(
                name=step_name,
                type="batch_step",
            )
            
            fact.tags.append("spring-batch")
            
            fact.add_evidence(
                path=file_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"Spring Batch Step: {step_name}"
            )
            
            self.output.add_fact(fact)
