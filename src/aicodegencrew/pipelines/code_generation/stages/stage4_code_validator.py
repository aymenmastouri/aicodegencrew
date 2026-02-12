"""
Stage 4: Code Validator

Validates generated code: syntax, patterns, security.
Generates unified diffs for modified files.

Duration: 1-3s (deterministic)
"""

import difflib
import re

from ....shared.utils.logger import setup_logger
from ..schemas import FileValidationResult, GeneratedFile, ValidationResult

logger = setup_logger(__name__)

# Security anti-patterns
SECURITY_PATTERNS = [
    (re.compile(r"eval\s*\("), "eval() usage detected"),
    (re.compile(r"exec\s*\("), "exec() usage detected"),
    (re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.I), "Hardcoded password detected"),
    (re.compile(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', re.I), "Hardcoded API key detected"),
    (re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.I), "Hardcoded secret detected"),
    (re.compile(r'\+\s*["\'].*SELECT\s', re.I), "Possible SQL concatenation"),
    (re.compile(r"innerHTML\s*="), "innerHTML assignment (XSS risk)"),
]


class CodeValidatorStage:
    """Validate generated code before writing."""

    def run(self, generated_files: list[GeneratedFile]) -> ValidationResult:
        """
        Validate all generated files.

        Args:
            generated_files: Files from Stage 3.

        Returns:
            ValidationResult with per-file results.
        """
        logger.info(f"[Stage4] Validating {len(generated_files)} files")

        file_results = []
        total_valid = 0
        total_invalid = 0
        all_security_issues = []

        for gf in generated_files:
            if gf.error:
                # Already failed in Stage 3
                file_results.append(
                    FileValidationResult(
                        file_path=gf.file_path,
                        is_valid=False,
                        errors=[f"Generation failed: {gf.error}"],
                    )
                )
                total_invalid += 1
                continue

            if gf.action == "delete":
                file_results.append(FileValidationResult(file_path=gf.file_path, is_valid=True))
                total_valid += 1
                continue

            result = self._validate_file(gf)
            file_results.append(result)

            if result.is_valid:
                total_valid += 1
            else:
                total_invalid += 1

            all_security_issues.extend(
                f"{gf.file_path}: {issue}"
                for issue in result.errors
                if "security" in issue.lower() or "hardcoded" in issue.lower()
            )

            # Generate diff for modified files
            if gf.action == "modify" and gf.original_content and not gf.diff:
                gf.diff = self._generate_diff(gf.original_content, gf.content, gf.file_path)

        result = ValidationResult(
            file_results=file_results,
            total_valid=total_valid,
            total_invalid=total_invalid,
            security_issues=all_security_issues,
        )

        logger.info(
            f"[Stage4] Validation: {total_valid} valid, {total_invalid} invalid, "
            f"{len(all_security_issues)} security issues"
        )

        return result

    def _validate_file(self, gf: GeneratedFile) -> FileValidationResult:
        """Validate a single generated file."""
        errors = []
        warnings = []

        syntax_ok = True
        pattern_ok = True
        security_ok = True

        # Syntax validation
        syntax_errors = self._check_syntax(gf.content, gf.language)
        if syntax_errors:
            syntax_ok = False
            errors.extend(syntax_errors)

        # Pattern compliance
        pattern_warnings = self._check_patterns(gf)
        if pattern_warnings:
            pattern_ok = False
            warnings.extend(pattern_warnings)

        # Security scan
        security_issues = self._check_security(gf.content)
        if security_issues:
            security_ok = False
            errors.extend(security_issues)

        is_valid = syntax_ok and security_ok

        return FileValidationResult(
            file_path=gf.file_path,
            is_valid=is_valid,
            syntax_ok=syntax_ok,
            pattern_ok=pattern_ok,
            security_ok=security_ok,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _check_syntax(content: str, language: str) -> list[str]:
        """Basic syntax checks per language."""
        errors = []

        if not content.strip():
            errors.append("Empty file content")
            return errors

        if language in ("java", "typescript"):
            # Check balanced braces
            open_braces = content.count("{")
            close_braces = content.count("}")
            if open_braces != close_braces:
                errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")

            # Check balanced parentheses
            open_parens = content.count("(")
            close_parens = content.count(")")
            if open_parens != close_parens:
                errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")

        if language == "java":
            # Java-specific: check class/interface declaration
            if "class " not in content and "interface " not in content and "enum " not in content:
                if "package " in content:
                    errors.append("Java file has package but no class/interface/enum")

        if language == "scss":
            open_braces = content.count("{")
            close_braces = content.count("}")
            if open_braces != close_braces:
                errors.append(f"Unbalanced braces in SCSS: {open_braces} open, {close_braces} close")

        return errors

    @staticmethod
    def _check_patterns(gf: GeneratedFile) -> list[str]:
        """Check if generated code follows existing naming patterns."""
        warnings = []

        if gf.language == "java":
            # Check class name matches file name
            from pathlib import Path

            expected_class = Path(gf.file_path).stem
            if expected_class and f"class {expected_class}" not in gf.content:
                if f"interface {expected_class}" not in gf.content:
                    if f"enum {expected_class}" not in gf.content:
                        warnings.append(f"Class name may not match file name: {expected_class}")

        if gf.language == "typescript":
            # Check for export
            if gf.action == "create" and "export " not in gf.content:
                warnings.append("New TypeScript file has no exports")

        return warnings

    @staticmethod
    def _check_security(content: str) -> list[str]:
        """Scan for security anti-patterns."""
        issues = []
        for pattern, message in SECURITY_PATTERNS:
            if pattern.search(content):
                issues.append(f"[security] {message}")
        return issues

    @staticmethod
    def _generate_diff(original: str, modified: str, file_path: str) -> str:
        """Generate unified diff between original and modified content."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        return "".join(diff)
