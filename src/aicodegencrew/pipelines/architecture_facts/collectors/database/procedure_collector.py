"""
Oracle Procedure Collector - Extracts stored procedure and package facts.

Detects:
- CREATE PROCEDURE
- CREATE FUNCTION
- CREATE PACKAGE
- CREATE PACKAGE BODY
- CREATE TRIGGER

Output: Procedure/package facts for data_model.json
"""

import re
from pathlib import Path
from typing import List

from ..base import DimensionCollector, CollectorOutput, RawEntity, RawEvidence, RelationHint


class OracleProcedureCollector(DimensionCollector):
    """Extracts Oracle stored procedure and package facts."""
    
    def collect(self) -> CollectorOutput:
        """Collect procedure/package facts from SQL files."""
        facts: List[RawEntity] = []
        relations: List[RelationHint] = []
        
        # Find SQL files
        sql_patterns = ['*.sql', '*.pls', '*.pkb', '*.pks', '*.prc', '*.fnc', '*.trg']
        sql_files = []
        for pattern in sql_patterns:
            sql_files.extend(self.repo_path.rglob(pattern))
        
        for sql_file in sql_files:
            try:
                content = sql_file.read_text(encoding='utf-8', errors='ignore')
                
                # Procedures
                facts.extend(self._extract_procedures(sql_file, content))
                
                # Functions
                facts.extend(self._extract_functions(sql_file, content))
                
                # Packages
                facts.extend(self._extract_packages(sql_file, content))
                
                # Triggers
                facts.extend(self._extract_triggers(sql_file, content))
                
                # Dependencies
                relations.extend(self._extract_dependencies(sql_file, content))
                
            except Exception:
                continue
        
        return CollectorOutput(facts=facts, relations=relations)
    
    def _extract_procedures(self, file_path: Path, content: str) -> List[RawEntity]:
        """Extract procedure definitions."""
        facts = []
        
        # CREATE [OR REPLACE] PROCEDURE [schema.]name (params) IS/AS
        proc_pattern = re.compile(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+'
            r'(?:(\w+)\.)?(\w+)\s*'
            r'(\([^)]*\))?\s*'
            r'(?:IS|AS)',
            re.IGNORECASE
        )
        
        for match in proc_pattern.finditer(content):
            schema = match.group(1) or ""
            proc_name = match.group(2)
            params = match.group(3) or "()"
            line_num = content[:match.start()].count('\n') + 1
            
            # Count parameters
            param_count = params.count(',') + 1 if params.strip() != '()' else 0
            
            facts.append(RawEntity(
                name=proc_name,
                entity_type="procedure",
                file_path=file_path,
                description=f"Stored procedure: {proc_name} ({param_count} params)",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 50,
                    reason=f"CREATE PROCEDURE {proc_name}",
                ),
                schema=schema,
            ))
        
        return facts
    
    def _extract_functions(self, file_path: Path, content: str) -> List[RawEntity]:
        """Extract function definitions."""
        facts = []
        
        # CREATE [OR REPLACE] FUNCTION [schema.]name (params) RETURN type IS/AS
        func_pattern = re.compile(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+'
            r'(?:(\w+)\.)?(\w+)\s*'
            r'(\([^)]*\))?\s*'
            r'RETURN\s+(\w+(?:\([^)]*\))?)',
            re.IGNORECASE
        )
        
        for match in func_pattern.finditer(content):
            schema = match.group(1) or ""
            func_name = match.group(2)
            params = match.group(3) or "()"
            return_type = match.group(4)
            line_num = content[:match.start()].count('\n') + 1
            
            facts.append(RawEntity(
                name=func_name,
                entity_type="function",
                file_path=file_path,
                description=f"Function: {func_name} returns {return_type}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 50,
                    reason=f"CREATE FUNCTION {func_name}",
                ),
                schema=schema,
                tags=[f"returns_{return_type.lower()}"],
            ))
        
        return facts
    
    def _extract_packages(self, file_path: Path, content: str) -> List[RawEntity]:
        """Extract package definitions."""
        facts = []
        
        # CREATE [OR REPLACE] PACKAGE [BODY] [schema.]name IS/AS
        pkg_pattern = re.compile(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(BODY\s+)?'
            r'(?:(\w+)\.)?(\w+)\s*'
            r'(?:IS|AS)',
            re.IGNORECASE
        )
        
        for match in pkg_pattern.finditer(content):
            is_body = bool(match.group(1))
            schema = match.group(2) or ""
            pkg_name = match.group(3)
            line_num = content[:match.start()].count('\n') + 1
            
            entity_type = "package_body" if is_body else "package_spec"
            
            # Count procedures/functions in package
            pkg_end = content.find('END ' + pkg_name, match.end())
            if pkg_end == -1:
                pkg_end = len(content)
            
            pkg_content = content[match.end():pkg_end]
            proc_count = len(re.findall(r'PROCEDURE\s+\w+', pkg_content, re.IGNORECASE))
            func_count = len(re.findall(r'FUNCTION\s+\w+', pkg_content, re.IGNORECASE))
            
            facts.append(RawEntity(
                name=pkg_name,
                entity_type=entity_type,
                file_path=file_path,
                description=f"Package {'body' if is_body else 'spec'}: {pkg_name} ({proc_count} procs, {func_count} funcs)",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 100,
                    reason=f"CREATE PACKAGE {'BODY ' if is_body else ''}{pkg_name}",
                ),
                schema=schema,
                tags=[f"{proc_count}_procedures", f"{func_count}_functions"],
            ))
        
        return facts
    
    def _extract_triggers(self, file_path: Path, content: str) -> List[RawEntity]:
        """Extract trigger definitions."""
        facts = []
        
        # CREATE [OR REPLACE] TRIGGER [schema.]name BEFORE/AFTER event ON table
        trigger_pattern = re.compile(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+'
            r'(?:(\w+)\.)?(\w+)\s+'
            r'(BEFORE|AFTER|INSTEAD\s+OF)\s+'
            r'(INSERT|UPDATE|DELETE)(?:\s+OR\s+(?:INSERT|UPDATE|DELETE))*\s+'
            r'ON\s+(?:(\w+)\.)?(\w+)',
            re.IGNORECASE
        )
        
        for match in trigger_pattern.finditer(content):
            schema = match.group(1) or ""
            trigger_name = match.group(2)
            timing = match.group(3)
            event = match.group(4)
            table_schema = match.group(5) or ""
            table_name = match.group(6)
            line_num = content[:match.start()].count('\n') + 1
            
            facts.append(RawEntity(
                name=trigger_name,
                entity_type="trigger",
                file_path=file_path,
                description=f"Trigger: {trigger_name} {timing} {event} ON {table_name}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 30,
                    reason=f"CREATE TRIGGER {trigger_name} ON {table_name}",
                ),
                schema=schema,
                tags=[timing.lower(), event.lower(), f"on_{table_name.lower()}"],
            ))
        
        return facts
    
    def _extract_dependencies(self, file_path: Path, content: str) -> List[RelationHint]:
        """Extract procedure/package dependencies."""
        relations = []
        
        # Find procedure/function that calls another
        # Look for: procedure_name(...) pattern after procedure definition
        
        # First, collect all defined procedure/function names
        defined = set()
        for match in re.finditer(r'(?:PROCEDURE|FUNCTION)\s+(\w+)', content, re.IGNORECASE):
            defined.add(match.group(1).upper())
        
        # Then find calls to these within procedure bodies
        current_proc = None
        for match in re.finditer(
            r'(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+(?:\w+\.)?(\w+))|'
            r'(\w+)\s*\(',
            content,
            re.IGNORECASE
        ):
            if match.group(1):
                current_proc = match.group(1)
            elif match.group(2) and current_proc:
                called = match.group(2).upper()
                if called in defined and called != current_proc.upper():
                    relations.append(RelationHint(
                        from_name=current_proc,
                        to_name=called,
                        relation_type="calls",
                        evidence=RawEvidence(
                            file_path=file_path,
                            line_start=content[:match.start()].count('\n') + 1,
                            line_end=content[:match.start()].count('\n') + 1,
                            reason=f"{current_proc} calls {called}",
                        ),
                    ))
        
        return relations
