"""
Angular State Collector - Extracts state management facts.

Detects:
- NgRx Store
- NgRx Effects
- NgRx Selectors
- Angular Signals
- BehaviorSubjects as state

Output: State management components for components.json
"""

import re
from pathlib import Path
from typing import List

from ..base import DimensionCollector, CollectorOutput, RawComponent, RawEvidence, RelationHint


class AngularStateCollector(DimensionCollector):
    """Extracts Angular state management facts."""
    
    def collect(self) -> CollectorOutput:
        """Collect state management facts."""
        facts: List[RawComponent] = []
        relations: List[RelationHint] = []
        
        # Find TypeScript files
        ts_files = list(self.repo_path.rglob("*.ts"))
        
        for ts_file in ts_files:
            # Skip test and spec files
            if '.spec.' in ts_file.name or '.test.' in ts_file.name:
                continue
            
            try:
                content = ts_file.read_text(encoding='utf-8', errors='ignore')
                
                # NgRx Store
                if '@ngrx/store' in content or 'createReducer' in content:
                    facts.extend(self._extract_ngrx_store(ts_file, content))
                
                # NgRx Effects
                if '@ngrx/effects' in content or 'createEffect' in content:
                    facts.extend(self._extract_ngrx_effects(ts_file, content))
                
                # NgRx Selectors
                if 'createSelector' in content or 'createFeatureSelector' in content:
                    facts.extend(self._extract_ngrx_selectors(ts_file, content))
                
                # Angular Signals
                if 'signal(' in content or 'computed(' in content:
                    facts.extend(self._extract_signals(ts_file, content))
                
                # BehaviorSubject state
                if 'BehaviorSubject' in content and 'state' in content.lower():
                    facts.extend(self._extract_behavior_subject_state(ts_file, content))
                    
            except Exception:
                continue
        
        return CollectorOutput(facts=facts, relations=relations)
    
    def _extract_ngrx_store(self, file_path: Path, content: str) -> List[RawComponent]:
        """Extract NgRx store/reducer definitions."""
        facts = []
        
        # Find createReducer calls
        reducer_matches = re.finditer(
            r'export\s+const\s+(\w+)\s*=\s*createReducer',
            content
        )
        
        for match in reducer_matches:
            reducer_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            facts.append(RawComponent(
                name=reducer_name,
                component_type="ngrx_reducer",
                file_path=file_path,
                description=f"NgRx reducer: {reducer_name}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 30,
                    reason=f"createReducer: {reducer_name}",
                ),
                tags=["ngrx", "state"],
            ))
        
        # Find feature key
        feature_match = re.search(r"featureKey\s*=\s*['\"](\w+)['\"]", content)
        if feature_match:
            feature_name = feature_match.group(1)
            line_num = content[:feature_match.start()].count('\n') + 1
            
            facts.append(RawComponent(
                name=f"{feature_name}_feature",
                component_type="ngrx_feature",
                file_path=file_path,
                description=f"NgRx feature: {feature_name}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 5,
                    reason=f"featureKey: {feature_name}",
                ),
                tags=["ngrx", "feature"],
            ))
        
        return facts
    
    def _extract_ngrx_effects(self, file_path: Path, content: str) -> List[RawComponent]:
        """Extract NgRx effects."""
        facts = []
        
        # Find Effects class
        class_match = re.search(r'class\s+(\w+Effects)', content)
        if class_match:
            class_name = class_match.group(1)
            line_num = content[:class_match.start()].count('\n') + 1
            
            # Count individual effects
            effect_count = content.count('createEffect')
            
            facts.append(RawComponent(
                name=class_name,
                component_type="ngrx_effects",
                file_path=file_path,
                description=f"NgRx effects class with {effect_count} effects",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 50,
                    reason=f"Effects class: {class_name}",
                ),
                tags=["ngrx", "effects"],
            ))
        
        return facts
    
    def _extract_ngrx_selectors(self, file_path: Path, content: str) -> List[RawComponent]:
        """Extract NgRx selectors."""
        facts = []
        
        # Count selectors
        selector_matches = list(re.finditer(
            r'export\s+const\s+(select\w+)\s*=\s*createSelector',
            content
        ))
        
        if selector_matches:
            # Create one fact for the selectors file
            facts.append(RawComponent(
                name=file_path.stem,
                component_type="ngrx_selectors",
                file_path=file_path,
                description=f"NgRx selectors file with {len(selector_matches)} selectors",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=1,
                    line_end=len(content.split('\n')),
                    reason=f"Selectors: {', '.join(m.group(1) for m in selector_matches[:5])}",
                ),
                tags=["ngrx", "selectors"],
            ))
        
        return facts
    
    def _extract_signals(self, file_path: Path, content: str) -> List[RawComponent]:
        """Extract Angular Signals usage."""
        facts = []
        
        # Find signal declarations
        signal_matches = list(re.finditer(
            r'(\w+)\s*=\s*signal\s*[<(]',
            content
        ))
        
        computed_matches = list(re.finditer(
            r'(\w+)\s*=\s*computed\s*\(',
            content
        ))
        
        if signal_matches or computed_matches:
            signal_names = [m.group(1) for m in signal_matches[:5]]
            computed_names = [m.group(1) for m in computed_matches[:5]]
            
            # Find class/component name
            class_match = re.search(r'class\s+(\w+)', content)
            class_name = class_match.group(1) if class_match else file_path.stem
            
            facts.append(RawComponent(
                name=f"{class_name}_signals",
                component_type="angular_signals",
                file_path=file_path,
                description=f"Signals: {len(signal_matches)}, Computed: {len(computed_matches)}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=1,
                    line_end=50,
                    reason=f"Signals: {signal_names}, Computed: {computed_names}",
                ),
                tags=["signals", "reactive"],
            ))
        
        return facts
    
    def _extract_behavior_subject_state(self, file_path: Path, content: str) -> List[RawComponent]:
        """Extract BehaviorSubject-based state management."""
        facts = []
        
        # Find BehaviorSubject state patterns
        state_matches = list(re.finditer(
            r'private\s+(\w*[Ss]tate\w*)\s*=\s*new\s+BehaviorSubject',
            content
        ))
        
        if state_matches:
            class_match = re.search(r'class\s+(\w+)', content)
            class_name = class_match.group(1) if class_match else file_path.stem
            
            state_names = [m.group(1) for m in state_matches]
            line_num = content[:state_matches[0].start()].count('\n') + 1
            
            facts.append(RawComponent(
                name=f"{class_name}_state",
                component_type="behavior_subject_state",
                file_path=file_path,
                description=f"BehaviorSubject state: {', '.join(state_names)}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num + 20,
                    reason=f"BehaviorSubject state in {class_name}",
                ),
                tags=["rxjs", "state"],
            ))
        
        return facts
