"""
LLM utilities for calling GPT-4o with structured context.
"""

import os
import json
from typing import Tuple, Optional
from openai import OpenAI, APIError


def create_llm_context(
    raw_diff: str,
    ast_context: dict,
    previous_patch: Optional[str] = None,
    test_output: Optional[str] = None,
    iteration: int = 0,
) -> str:
    """
    Format code review context for the LLM.
    
    Args:
        raw_diff: The unified diff from the PR
        ast_context: Extracted AST analysis dict
        previous_patch: On retry, the previous patch that failed
        test_output: On retry, the test failure output
        iteration: Current iteration number (0-indexed)
    
    Returns:
        Formatted context string for LLM
    """
    
    context_parts = []
    
    # Header
    context_parts.append("=" * 80)
    context_parts.append(f"CODE REVIEW CONTEXT - Iteration {iteration}")
    context_parts.append("=" * 80)
    context_parts.append("")
    
    # Raw Diff
    context_parts.append("## UNIFIED DIFF")
    context_parts.append("-" * 40)
    context_parts.append(raw_diff if raw_diff else "(no diff provided)")
    context_parts.append("")
    
    # AST Analysis
    if ast_context:
        context_parts.append("## AST ANALYSIS")
        context_parts.append("-" * 40)
        
        files = ast_context.get("files", {})
        if files:
            for file_path, file_info in files.items():
                context_parts.append(f"\n### File: {file_path}")
                
                # Changed ranges
                if "changed_ranges" in file_info:
                    context_parts.append(f"  Changed lines: {file_info['changed_ranges']}")
                
                # Changed functions
                if "changed_functions" in file_info:
                    context_parts.append(f"  Changed functions: {file_info['changed_functions']}")
                
                # All functions
                if "all_functions" in file_info:
                    funcs = file_info['all_functions']
                    if funcs:
                        context_parts.append(f"  All functions in file: {list(funcs.keys())}")
                
                # All classes
                if "all_classes" in file_info:
                    classes = file_info['all_classes']
                    if classes:
                        context_parts.append(f"  Classes in file: {list(classes.keys())}")
        
        context_parts.append("")
    
    # Previous attempt info (on retry)
    if iteration > 0 and previous_patch:
        context_parts.append("## PREVIOUS ATTEMPT")
        context_parts.append("-" * 40)
        context_parts.append("Previous patch tried:")
        context_parts.append(previous_patch[:500])  # Truncate for context length
        context_parts.append("")
        
        if test_output:
            context_parts.append("Test output from previous attempt:")
            context_parts.append(test_output[:1000])  # Truncate for context
            context_parts.append("")
    
    return "\n".join(context_parts)


def call_gpt4o_for_review(
    raw_diff: str,
    ast_context: dict,
    previous_patch: Optional[str] = None,
    test_output: Optional[str] = None,
    iteration: int = 0,
) -> Tuple[str, int, float]:
    """
    Call GPT-4o to generate a fix patch.
    
    Args:
        raw_diff: Unified diff
        ast_context: AST analysis
        previous_patch: (Optional) Previous failed patch
        test_output: (Optional) Test failure output
        iteration: Current iteration
    
    Returns:
        (patch: str, tokens_used: int, cost: float)
        patch will be "CANNOT_FIX" if the model cannot determine the fix.
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = OpenAI(api_key=api_key)
    
    # System prompt
    system_prompt = """You are a senior Python engineer doing a code review.
You will receive a git diff and AST analysis of changed code.
Your job is to identify the most likely bug causing test failures and produce a minimal unified diff patch that fixes it.

Rules:
- Only change what is necessary to fix the bug
- Do not reformat unrelated code
- Output ONLY a valid unified diff, nothing else
- If you cannot determine the fix, respond with exactly: CANNOT_FIX
- The diff should be applicable with the `patch -p1` command"""
    
    # Build user context
    user_message = create_llm_context(
        raw_diff=raw_diff,
        ast_context=ast_context,
        previous_patch=previous_patch,
        test_output=test_output,
        iteration=iteration,
    )
    
    # Call GPT-4o
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,  # Deterministic output
            max_tokens=2048,
        )
        
        patch = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens
        
        # Rough cost estimate: GPT-4o input $0.015 per 1K/output $0.06 per 1K (as of April 2026)
        input_cost = response.usage.prompt_tokens * (0.015 / 1000)
        output_cost = response.usage.completion_tokens * (0.06 / 1000)
        cost = input_cost + output_cost
        
        return patch, tokens_used, cost
    
    except APIError as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")


# Token estimation for cost tracking
GPT4O_INPUT_PRICE_PER_1K = 0.015
GPT4O_OUTPUT_PRICE_PER_1K = 0.06


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for GPT-4o call."""
    return (input_tokens * GPT4O_INPUT_PRICE_PER_1K / 1000) + \
           (output_tokens * GPT4O_OUTPUT_PRICE_PER_1K / 1000)
