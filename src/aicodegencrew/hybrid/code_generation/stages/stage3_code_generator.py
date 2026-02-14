"""
Stage 3: Code Generator

Uses LLM to generate/modify code — 1 call per file.

Duration: 10-30s per file (LLM)
"""

import os
import time

from ....shared.utils.logger import setup_logger
from ..schemas import CodegenPlanInput, CollectedContext, FileContext, GeneratedFile
from ..strategies.base import BaseStrategy

logger = setup_logger(__name__)

# Delay between LLM calls (seconds) to respect on-prem rate limits
CALL_DELAY = float(os.getenv("CODEGEN_CALL_DELAY", "2"))

# Max retries per file
MAX_RETRIES = int(os.getenv("CODEGEN_MAX_RETRIES", "2"))


class CodeGeneratorStage:
    """Generate code using LLM — 1 call per file."""

    def __init__(self):
        self._model = os.getenv("MODEL", "gpt-oss-120b")
        self.llm = self._create_llm()
        self.total_tokens = 0
        self.total_calls = 0

    def _create_llm(self):
        """Create OpenAI-compatible LLM client."""
        from openai import OpenAI

        provider = os.getenv("LLM_PROVIDER", "onprem")
        api_base = os.getenv("API_BASE", "http://sov-ai-platform.nue.local.vm:4000/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key")

        client = OpenAI(base_url=api_base, api_key=api_key)
        logger.info(f"[Stage3] Created LLM: {provider}/{self._model}")
        return client

    def run(
        self,
        plan: CodegenPlanInput,
        context: CollectedContext,
        strategy: BaseStrategy,
    ) -> list[GeneratedFile]:
        """
        Generate code for all files in context.

        Args:
            plan: Validated plan from Stage 1.
            context: Collected file contexts from Stage 2.
            strategy: Task-type-specific strategy.

        Returns:
            List of GeneratedFile with generated/modified content.
        """
        logger.info(f"[Stage3] Generating code for {context.total_files} files using {strategy.__class__.__name__}")

        generated = []

        for i, file_ctx in enumerate(context.file_contexts, 1):
            logger.info(
                f"[Stage3] File {i}/{context.total_files}: "
                f"{file_ctx.file_path} ({file_ctx.component.change_type if file_ctx.component else 'modify'})"
            )

            result = self._generate_single(file_ctx, plan, strategy)
            generated.append(result)

            # Rate limiting between calls
            if i < context.total_files:
                time.sleep(CALL_DELAY)

        succeeded = sum(1 for g in generated if not g.error)
        failed = sum(1 for g in generated if g.error)

        logger.info(
            f"[Stage3] Generation complete: {succeeded} succeeded, {failed} failed, "
            f"{self.total_calls} LLM calls, ~{self.total_tokens} tokens"
        )

        return generated

    def _generate_single(
        self,
        file_ctx: FileContext,
        plan: CodegenPlanInput,
        strategy: BaseStrategy,
    ) -> GeneratedFile:
        """Generate code for a single file with retry."""
        action = "create" if not file_ctx.content else "modify"
        if file_ctx.component:
            action = file_ctx.component.change_type

        # Handle delete action — no LLM needed
        if action == "delete":
            return GeneratedFile(
                file_path=file_ctx.file_path,
                content="",
                original_content=file_ctx.content,
                action="delete",
                confidence=1.0,
                language=file_ctx.language,
            )

        # Build prompt
        prompt = strategy.build_prompt(file_ctx, plan)

        # LLM call with retries
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.llm.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=8000,
                )

                self.total_calls += 1

                # Track tokens
                usage = getattr(response, "usage", None)
                if usage:
                    self.total_tokens += getattr(usage, "total_tokens", 0)

                raw_output = response.choices[0].message.content or ""

                # Post-process with strategy
                code = strategy.post_process(raw_output, file_ctx)

                if not code.strip():
                    raise ValueError("LLM returned empty content")

                return GeneratedFile(
                    file_path=file_ctx.file_path,
                    content=code,
                    original_content=file_ctx.content,
                    action=action,
                    confidence=0.7,
                    language=file_ctx.language,
                )

            except Exception as e:
                logger.warning(f"[Stage3] Attempt {attempt}/{MAX_RETRIES} failed for {file_ctx.file_path}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(5 * (2 ** (attempt - 1)))

        # All retries failed
        logger.error(f"[Stage3] All retries failed for {file_ctx.file_path}")
        return GeneratedFile(
            file_path=file_ctx.file_path,
            content="",
            original_content=file_ctx.content,
            action=action,
            confidence=0.0,
            language=file_ctx.language,
            error=f"LLM generation failed after {MAX_RETRIES} retries",
        )
