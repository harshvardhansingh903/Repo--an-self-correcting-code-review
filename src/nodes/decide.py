"""
Decide node: Determine next action based on test results.

Decision logic:
  - If tests_passed: open a new PR with the fix
  - If iteration >= 3: post failure comment on original PR
  - Otherwise: loop back to review_code with incremented iteration
"""

from src.agent.state import AgentState


def decide_node(state: AgentState) -> str:
    """
    Determine the next node based on test results and iteration count.
    
    Args:
        state: Current agent state with tests_passed and iteration
    
    Returns:
        Next node name: "open_pr" | "post_failure_comment" | "review_code"
    """
    
    tests_passed = state.get("tests_passed", False)
    iteration = state.get("iteration", 0)
    current_patch = state.get("current_patch", "")
    
    # Success: tests passed
    if tests_passed:
        return "open_pr"
    
    # LLM gave up
    if current_patch == "CANNOT_FIX":
        return "post_failure_comment"
    
    # Max iterations reached
    if iteration >= 3:
        return "post_failure_comment"
    
    # Continue fixing: loop back to review
    return "review_code"


def increment_iteration(state: AgentState) -> AgentState:
    """
    Increment iteration counter and record current attempt in fix_history.
    
    Called before looping back to review_code.
    """
    iteration = state.get("iteration", 0)
    current_patch = state.get("current_patch", "")
    test_output = state.get("test_output", "")
    tokens_used = state.get("tokens_used", 0)
    
    # Record this attempt
    fix_history = state.get("fix_history", [])
    fix_history.append({
        "iteration": iteration,
        "patch": current_patch,
        "test_output": test_output,
        "tests_passed": state.get("tests_passed", False),
        "tokens_used": tokens_used,
    })
    
    # Increment for next iteration
    state["iteration"] = iteration + 1
    state["fix_history"] = fix_history
    
    # Reset patch for next attempt
    state["current_patch"] = ""
    state["test_output"] = ""
    
    return state
