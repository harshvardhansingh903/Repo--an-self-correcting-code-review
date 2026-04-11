"""
Code Review node: Use GPT-4o to generate a patch fix.
"""

from src.agent.state import AgentState
from src.utils.llm_review import call_gpt4o_for_review
from typing import Optional


def review_code_node(state: AgentState) -> AgentState:
    """
    Analyze code and test failures using GPT-4o to generate a fix patch.
    
    This node:
    1. Takes the raw diff and AST analysis
    2. On first iteration: focuses on identifying the bug
    3. On retry: includes previous patch attempt + test failure output
    4. Calls GPT-4o to generate a unified diff patch
    5. Handles "CANNOT_FIX" response
    6. Tracks tokens and cost
    
    Args:
        state: Must contain raw_diff, ast_context, iteration
               On retry: test_output and previous patch in fix_history
    
    Returns:
        Updated state with current_patch populated and tokens_used incremented
    """
    
    raw_diff = state.get("raw_diff", "")
    ast_context = state.get("ast_context", {})
    iteration = state.get("iteration", 0)
    test_output = state.get("test_output", "")
    fix_history = state.get("fix_history", [])
    
    # Determine if this is a retry with previous failures
    previous_patch = None
    if iteration > 0 and fix_history:
        # Get the last failure from history
        previous_patch = fix_history[-1].get("patch", "")
    
    try:
        # Call GPT-4o
        patch, tokens_used, cost = call_gpt4o_for_review(
            raw_diff=raw_diff,
            ast_context=ast_context,
            previous_patch=previous_patch,
            test_output=test_output,
            iteration=iteration,
        )
        
        state["current_patch"] = patch
        state["tokens_used"] = state.get("tokens_used", 0) + tokens_used
        
        return state
    
    except Exception as e:
        # Mark as unable to fix if API fails
        state["current_patch"] = "CANNOT_FIX"
        state["test_output"] = f"LLM review failed: {str(e)}"
        return state
