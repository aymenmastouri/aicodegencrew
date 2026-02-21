"""
Stage 3: Pattern Matcher

Matches test, security, validation, and error handling patterns using:
- TF-IDF similarity for test patterns
- Rule-based matching for security/validation/error

Duration: 1-3 seconds (pure algorithms)
NO LLM REQUIRED
"""

from pathlib import Path
from typing import Any

from ....shared.utils.logger import setup_logger
from ..schemas import (
    ErrorHandlingPattern,
    SecurityPattern,
    TaskInput,
    TestPattern,
    ValidationPattern,
    WorkflowContext,
)

logger = setup_logger(__name__)


class PatternMatcherStage:
    """
    Match patterns from architecture_facts.json using algorithms.
    """

    def __init__(self, facts: dict, repo_path: str = None):
        """
        Initialize pattern matcher.

        Args:
            facts: architecture_facts.json (from Phase 1)
            repo_path: Target repository path (for upgrade code scanning)
        """
        self.facts = facts
        self.repo_path = repo_path

        self.tests = facts.get("tests", [])
        self.security_details = facts.get("security_details", [])
        self.validations = facts.get("validation", [])
        self.error_handling = facts.get("error_handling", [])
        self.workflows = facts.get("workflows", [])

    def run(
        self,
        task: TaskInput,
        components: list[dict[str, Any]],
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Match all pattern types.

        Args:
            task: Task input
            components: Discovered components from Stage 2
            top_k: Number of patterns to return per category

        Returns:
            Dict with test_patterns, security_patterns, etc.
        """
        logger.info(f"[Stage3] Matching patterns for {len(components)} components")

        component_names = [c["name"] for c in components]
        component_paths = [c["file_path"] for c in components]
        entity_names = [c["name"] for c in components if c["stereotype"] == "entity"]

        # Match test patterns (TF-IDF)
        test_patterns = self._match_test_patterns(task.description, component_names, top_k=top_k)

        # Match security patterns (rule-based)
        security_patterns = self._match_security_patterns(component_paths, top_k=top_k)

        # Match validation patterns (rule-based)
        validation_patterns = self._match_validation_patterns(entity_names, top_k=top_k)

        # Match error handling patterns (rule-based)
        error_patterns = self._match_error_patterns(task.description, top_k=top_k)

        # Match workflow context (rule-based)
        workflow_context = self._match_workflows(component_names, top_k=top_k)

        # Match upgrade patterns (if upgrade task)
        upgrade_assessment = {}
        if task.task_type == "upgrade":
            upgrade_assessment = self._match_upgrade_patterns(task, components)

        logger.info(
            f"[Stage3] Found {len(test_patterns)} test patterns, "
            f"{len(security_patterns)} security patterns, "
            f"{len(validation_patterns)} validation patterns, "
            f"{len(error_patterns)} error patterns, "
            f"{len(workflow_context)} workflows"
            + (
                f", upgrade: {upgrade_assessment.get('summary', {}).get('total_rules_triggered', 0)} rules"
                if upgrade_assessment
                else ""
            )
        )

        return {
            "test_patterns": [p.model_dump() for p in test_patterns],
            "security_patterns": [p.model_dump() for p in security_patterns],
            "validation_patterns": [p.model_dump() for p in validation_patterns],
            "error_patterns": [p.model_dump() for p in error_patterns],
            "workflow_context": [w.model_dump() for w in workflow_context],
            "upgrade_assessment": upgrade_assessment,
        }

    def _match_test_patterns(
        self,
        task_description: str,
        component_names: list[str],
        top_k: int = 5,
    ) -> list[TestPattern]:
        """Match test patterns using TF-IDF similarity."""
        if not self.tests:
            return []

        try:
            import numpy as np
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            logger.warning("[Stage3] scikit-learn not installed, using simple matching")
            return self._simple_test_matching(task_description, component_names, top_k)

        # Filter candidate tests by component names
        candidate_tests = []
        for test in self.tests:
            test_path = test.get("file_path", "").lower()

            # Check if any component name is in test path
            if any(comp.lower() in test_path for comp in component_names):
                candidate_tests.append(test)

        if not candidate_tests:
            # Fallback: use all tests
            candidate_tests = self.tests[:100]  # Limit for performance

        if not candidate_tests:
            return []

        # Build corpus
        corpus = [task_description]  # Query
        test_texts = []

        for test in candidate_tests:
            # Facts may have "name", "scenarios", or "targets" — use all available fields
            parts = []
            if test.get("name"):
                parts.append(test["name"])
            if test.get("scenarios"):
                parts.extend(test["scenarios"])
            if test.get("targets"):
                parts.extend(test["targets"])
            if test.get("file_path"):
                parts.append(test["file_path"])
            test_texts.append(" ".join(parts) if parts else test.get("file_path", ""))

        corpus.extend(test_texts)

        # TF-IDF
        vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Cosine similarity
        query_vector = tfidf_matrix[0]
        test_vectors = tfidf_matrix[1:]

        similarities = cosine_similarity(query_vector, test_vectors).flatten()

        # Top K
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Build results
        results = []
        for idx in top_indices:
            test = candidate_tests[idx]
            similarity = float(similarities[idx])

            if similarity > 0.1:  # Threshold
                # Derive name from file_path if not present
                test_name = test.get("name") or Path(test.get("file_path", "")).stem
                results.append(
                    TestPattern(
                        name=test_name,
                        file_path=test.get("file_path", ""),
                        test_type=test.get("test_type", "unit"),
                        framework=test.get("framework", "unknown"),
                        scenarios=test.get("scenarios", test.get("targets", [])),
                        relevance_score=round(similarity, 3),
                        pattern_description=f"Similar {test.get('test_type', 'unit')} test using {test.get('framework', 'unknown')}",
                    )
                )

        return results

    def _simple_test_matching(
        self,
        task_description: str,
        component_names: list[str],
        top_k: int,
    ) -> list[TestPattern]:
        """Simple keyword-based test matching (fallback)."""
        results = []

        for test in self.tests[:100]:  # Limit
            test_path = test.get("file_path", "").lower()
            test_name = test.get("name", "").lower()

            # Score by component name match
            score = 0
            for comp in component_names:
                if comp.lower() in test_path or comp.lower() in test_name:
                    score += 1

            if score > 0:
                results.append(
                    TestPattern(
                        name=test.get("name", ""),
                        file_path=test.get("file_path", ""),
                        test_type=test.get("test_type", "unit"),
                        framework=test.get("framework", "unknown"),
                        scenarios=test.get("scenarios", []),
                        relevance_score=min(score / len(component_names), 1.0),
                        pattern_description=f"{test.get('test_type', 'unit')} test",
                    )
                )

        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:top_k]

    def _match_security_patterns(
        self,
        component_paths: list[str],
        top_k: int = 5,
    ) -> list[SecurityPattern]:
        """Match security patterns by file path."""
        if not self.security_details:
            return []

        results = []

        for sec in self.security_details:
            sec_path = sec.get("file_path", "")

            # Check if security config is in same path as components
            for comp_path in component_paths:
                if comp_path and sec_path:
                    # Check if in same package
                    comp_package = "/".join(comp_path.split("/")[:-1])
                    sec_package = "/".join(sec_path.split("/")[:-1])

                    if comp_package and comp_package in sec_package:
                        results.append(
                            SecurityPattern(
                                security_type=sec.get("security_type", "unknown"),
                                class_name=sec.get("class_name", ""),
                                pattern_name=sec.get("name", ""),
                                file_path=sec_path,
                                recommendation=self._generate_security_recommendation(sec.get("security_type", "")),
                            )
                        )
                        break

        # If no matches, return common security patterns
        if not results and self.security_details:
            for sec in self.security_details[:top_k]:
                results.append(
                    SecurityPattern(
                        security_type=sec.get("security_type", "unknown"),
                        class_name=sec.get("class_name", ""),
                        pattern_name=sec.get("name", ""),
                        file_path=sec.get("file_path", ""),
                        recommendation=self._generate_security_recommendation(sec.get("security_type", "")),
                    )
                )

        return results[:top_k]

    def _match_validation_patterns(
        self,
        entity_names: list[str],
        top_k: int = 5,
    ) -> list[ValidationPattern]:
        """Match validation patterns by entity names."""
        if not self.validations:
            return []

        results = []
        validation_counts = {}

        for val in self.validations:
            target_class = val.get("target_class", "")

            # Check if validation is for one of our entities
            if any(entity in target_class for entity in entity_names):
                val_type = val.get("validation_type", "")

                # Count usage
                validation_counts[val_type] = validation_counts.get(val_type, 0) + 1

                results.append(
                    ValidationPattern(
                        validation_type=val_type,
                        target_class=target_class,
                        field_hint=self._extract_field_hint(val.get("name", "")),
                        pattern_name=val.get("name", ""),
                        recommendation=self._generate_validation_recommendation(val_type),
                        usage_count=validation_counts[val_type],
                    )
                )

        # If no entity-specific matches, return common patterns
        if not results and self.validations:
            common_validations = {}
            for val in self.validations:
                val_type = val.get("validation_type", "")
                if val_type not in common_validations:
                    common_validations[val_type] = val

            for val_type, val in list(common_validations.items())[:top_k]:
                results.append(
                    ValidationPattern(
                        validation_type=val_type,
                        target_class=val.get("target_class", ""),
                        field_hint=self._extract_field_hint(val.get("name", "")),
                        pattern_name=val.get("name", ""),
                        recommendation=self._generate_validation_recommendation(val_type),
                        usage_count=1,
                    )
                )

        return results[:top_k]

    def _match_error_patterns(
        self,
        task_description: str,
        top_k: int = 5,
    ) -> list[ErrorHandlingPattern]:
        """Match error handling patterns."""
        if not self.error_handling:
            return []

        results = []

        # Detect error types in task description
        desc_lower = task_description.lower()

        for err in self.error_handling:
            exception_class = err.get("exception_class", "")
            handling_type = err.get("handling_type", "")

            # Score by keyword match
            score = 0
            keywords = exception_class.lower().split("exception")[0]

            if keywords and keywords in desc_lower:
                score = 1.0
            elif "error" in desc_lower or "exception" in desc_lower:
                score = 0.5

            if score > 0:
                results.append(
                    ErrorHandlingPattern(
                        handling_type=handling_type,
                        exception_class=exception_class,
                        handler_method=err.get("handler_method"),
                        pattern_name=err.get("name", ""),
                        recommendation=self._generate_error_recommendation(handling_type, exception_class),
                    )
                )

        # If no matches, return common patterns
        if not results and self.error_handling:
            for err in self.error_handling[:top_k]:
                results.append(
                    ErrorHandlingPattern(
                        handling_type=err.get("handling_type", ""),
                        exception_class=err.get("exception_class", ""),
                        handler_method=err.get("handler_method"),
                        pattern_name=err.get("name", ""),
                        recommendation=self._generate_error_recommendation(
                            err.get("handling_type", ""), err.get("exception_class", "")
                        ),
                    )
                )

        return results[:top_k]

    def _match_workflows(
        self,
        component_names: list[str],
        top_k: int = 5,
    ) -> list[WorkflowContext]:
        """Match business workflows."""
        if not self.workflows:
            return []

        results = []

        for wf in self.workflows:
            wf_name = wf.get("name", "")
            wf_components = wf.get("components_involved", [])

            # Check if any of our components are involved
            if any(comp in str(wf_components) for comp in component_names):
                results.append(
                    WorkflowContext(
                        workflow_name=wf_name,
                        steps=wf.get("steps", []),
                        components_involved=wf_components,
                        impact=f"This change affects the {wf_name} workflow",
                    )
                )

        return results[:top_k]

    # Helper methods

    @staticmethod
    def _generate_security_recommendation(security_type: str) -> str:
        """Generate security recommendation."""
        recommendations = {
            "cors": "Ensure CORS configuration allows only trusted origins",
            "csrf": "Verify CSRF protection is enabled for state-changing operations",
            "authentication": "Add @PreAuthorize annotation if endpoint requires authentication",
            "authorization": "Implement role-based access control (RBAC)",
        }
        return recommendations.get(security_type, f"Apply {security_type} security pattern")

    @staticmethod
    def _generate_validation_recommendation(validation_type: str) -> str:
        """Generate validation recommendation."""
        recommendations = {
            "not_null": "Add @NotNull annotation to prevent null values",
            "email": "Add @Email annotation for email format validation",
            "size": "Add @Size annotation to enforce length constraints",
            "pattern": "Add @Pattern annotation for regex validation",
        }
        return recommendations.get(validation_type, f"Add @{validation_type.title()} annotation")

    @staticmethod
    def _generate_error_recommendation(handling_type: str, exception_class: str) -> str:
        """Generate error handling recommendation."""
        if handling_type == "custom_exception":
            return f"Create custom {exception_class} or reuse existing exception"
        elif handling_type == "exception_handler":
            return f"Add @ExceptionHandler for {exception_class} in global exception handler"
        else:
            return f"Handle {exception_class} appropriately"

    @staticmethod
    def _extract_field_hint(pattern_name: str) -> str:
        """Extract field name from pattern name."""
        # Pattern: "ClassName.field_name"
        if "." in pattern_name:
            return pattern_name.split(".")[-1]
        return ""

    def _match_upgrade_patterns(
        self,
        task: TaskInput,
        components: list,
    ) -> dict:
        """Run upgrade rules engine for framework upgrade tasks."""
        try:
            from ..upgrade_rules import UpgradeRulesEngine

            engine = UpgradeRulesEngine(
                facts=self.facts,
                repo_path=self.repo_path,
            )

            context = engine.detect_upgrade_context(
                task.description,
                task.labels,
            )
            if not context:
                logger.warning("[Stage3] Could not detect upgrade context")
                return {}

            rule_sets = engine.get_applicable_rules(
                framework=context["framework"],
                current_version=context["current_version"],
                target_version=context["target_version"],
            )
            if not rule_sets:
                logger.warning("[Stage3] No upgrade rules found for version range")
                return {}

            assessment = engine.scan_and_assess(rule_sets)
            assessment["upgrade_context"] = context

            # Strategy enrichment: validate dependency compatibility
            try:
                from ...code_generation.strategies import get_strategy

                strategy = get_strategy("upgrade")
                enrichment = strategy.enrich_plan(
                    plan_data={
                        "upgrade_plan": {
                            "framework": context.get("framework", ""),
                            "from_version": context.get("current_version", ""),
                            "to_version": context.get("target_version", ""),
                        },
                    },
                    facts=self.facts,
                )
                if enrichment.compatibility_checks:
                    assessment["compatibility_report"] = {
                        "checks": enrichment.compatibility_checks,
                        "warnings": enrichment.warnings,
                        **enrichment.additional_context,
                    }
            except Exception as e:
                logger.warning("[Stage3] Strategy enrichment failed: %s", e)

            return assessment

        except Exception as e:
            logger.error(f"[Stage3] Upgrade pattern matching failed: {e}")
            return {}
