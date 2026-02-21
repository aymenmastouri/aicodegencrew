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

from ..base import DimensionCollector, RawComponent


class AngularStateCollector(DimensionCollector):
    """Extracts Angular state management facts."""

    DIMENSION = "angular_state"

    def __init__(self, repo_path: Path, container_id: str = "frontend"):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self):
        """Collect state management facts."""
        self._log_start()

        # Find TypeScript files (using _find_files for SKIP_DIRS pruning)
        ts_files = self._find_files("*.ts")

        for ts_file in ts_files:
            # Skip test and spec files
            if ".spec." in ts_file.name or ".test." in ts_file.name:
                continue

            try:
                content = self._read_file_content(ts_file)

                # NgRx Store
                if "@ngrx/store" in content or "createReducer" in content:
                    self._extract_ngrx_store(ts_file, content)

                # NgRx Effects
                if "@ngrx/effects" in content or "createEffect" in content:
                    self._extract_ngrx_effects(ts_file, content)

                # NgRx Selectors
                if "createSelector" in content or "createFeatureSelector" in content:
                    self._extract_ngrx_selectors(ts_file, content)

                # Angular Signals
                if "signal(" in content or "computed(" in content:
                    self._extract_signals(ts_file, content)

                # BehaviorSubject state
                if "BehaviorSubject" in content and "state" in content.lower():
                    self._extract_behavior_subject_state(ts_file, content)

            except Exception:
                continue

        self._log_end()
        return self.output

    def _extract_ngrx_store(self, file_path: Path, content: str) -> None:
        """Extract NgRx store/reducer definitions."""
        rel_path = self._relative_path(file_path)

        # Find createReducer calls
        reducer_matches = re.finditer(r"export\s+const\s+(\w+)\s*=\s*createReducer", content)

        for match in reducer_matches:
            reducer_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            comp = RawComponent(
                name=reducer_name,
                stereotype="ngrx_reducer",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["ngrx", "state"],
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 30,
                reason=f"createReducer: {reducer_name}",
            )
            self.output.add_fact(comp)

        # Find feature key
        feature_match = re.search(r"featureKey\s*=\s*['\"](\w+)['\"]", content)
        if feature_match:
            feature_name = feature_match.group(1)
            line_num = content[: feature_match.start()].count("\n") + 1

            comp = RawComponent(
                name=f"{feature_name}_feature",
                stereotype="ngrx_feature",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["ngrx", "feature"],
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"featureKey: {feature_name}",
            )
            self.output.add_fact(comp)

    def _extract_ngrx_effects(self, file_path: Path, content: str) -> None:
        """Extract NgRx effects."""
        rel_path = self._relative_path(file_path)

        # Find Effects class
        class_match = re.search(r"class\s+(\w+Effects)", content)
        if class_match:
            class_name = class_match.group(1)
            line_num = content[: class_match.start()].count("\n") + 1

            # Count individual effects
            effect_count = content.count("createEffect")

            comp = RawComponent(
                name=class_name,
                stereotype="ngrx_effects",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["ngrx", "effects"],
                metadata={"effect_count": effect_count},
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 50,
                reason=f"Effects class: {class_name}",
            )
            self.output.add_fact(comp)

    def _extract_ngrx_selectors(self, file_path: Path, content: str) -> None:
        """Extract NgRx selectors."""
        rel_path = self._relative_path(file_path)

        # Count selectors
        selector_matches = list(re.finditer(r"export\s+const\s+(select\w+)\s*=\s*createSelector", content))

        if selector_matches:
            comp = RawComponent(
                name=file_path.stem,
                stereotype="ngrx_selectors",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["ngrx", "selectors"],
                metadata={"selector_count": len(selector_matches)},
            )
            comp.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=len(content.split("\n")),
                reason=f"Selectors: {', '.join(m.group(1) for m in selector_matches[:5])}",
            )
            self.output.add_fact(comp)

    def _extract_signals(self, file_path: Path, content: str) -> None:
        """Extract Angular Signals usage."""
        rel_path = self._relative_path(file_path)

        # Find signal declarations
        signal_matches = list(re.finditer(r"(\w+)\s*=\s*signal\s*[<(]", content))
        computed_matches = list(re.finditer(r"(\w+)\s*=\s*computed\s*\(", content))

        if signal_matches or computed_matches:
            signal_names = [m.group(1) for m in signal_matches[:5]]
            computed_names = [m.group(1) for m in computed_matches[:5]]

            # Find class/component name
            class_match = re.search(r"class\s+(\w+)", content)
            class_name = class_match.group(1) if class_match else file_path.stem

            comp = RawComponent(
                name=f"{class_name}_signals",
                stereotype="angular_signals",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["signals", "reactive"],
                metadata={"signal_count": len(signal_matches), "computed_count": len(computed_matches)},
            )
            comp.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=50,
                reason=f"Signals: {signal_names}, Computed: {computed_names}",
            )
            self.output.add_fact(comp)

    def _extract_behavior_subject_state(self, file_path: Path, content: str) -> None:
        """Extract BehaviorSubject-based state management."""
        rel_path = self._relative_path(file_path)

        # Find BehaviorSubject state patterns
        state_matches = list(re.finditer(r"private\s+(\w*[Ss]tate\w*)\s*=\s*new\s+BehaviorSubject", content))

        if state_matches:
            class_match = re.search(r"class\s+(\w+)", content)
            class_name = class_match.group(1) if class_match else file_path.stem

            state_names = [m.group(1) for m in state_matches]
            line_num = content[: state_matches[0].start()].count("\n") + 1

            comp = RawComponent(
                name=f"{class_name}_state",
                stereotype="behavior_subject_state",
                file_path=rel_path,
                container_hint=self.container_id,
                tags=["rxjs", "state"],
                metadata={"state_subjects": state_names},
            )
            comp.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 20,
                reason=f"BehaviorSubject state in {class_name}",
            )
            self.output.add_fact(comp)
