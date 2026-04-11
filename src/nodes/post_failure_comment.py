"""
Post Failure Comment node: Comment on original PR with failure details.
"""

from src.agent.state import AgentState
from src.utils.github_client import GitHubClient


def post_failure_comment_node(state: AgentState) -> AgentState:
    """
    Post a comment on the original GitHub PR explaining what was tried and why it failed.
    
    This node:
    1. Formats a detailed comment with all attempts
    2. Includes test output from final attempt
    3. Posts comment to original PR
    4. Sets final_status to "failed_max_iterations" or "cannot_fix"
    
    Args:
        state: Must contain fix_history, current_patch, repo_full_name, pr_number
    
    Returns:
        Updated state with final_status set
    """
    
    current_patch = state.get("current_patch", "")
    fix_history = state.get("fix_history", [])
    pr_number = state.get("pr_number", 0)
    repo_full_name = state.get("repo_full_name", "")
    
    # Determine failure reason
    if current_patch == "CANNOT_FIX":
        state["final_status"] = "cannot_fix"
    else:
        state["final_status"] = "failed_max_iterations"
    
    # Post comment to GitHub PR
    if repo_full_name and pr_number:
        try:
            client = GitHubClient()
            comment_text = format_failure_comment(state)
            comment_url = client.post_comment(repo_full_name, pr_number, comment_text)
            state["test_output"] = f"Comment posted: {comment_url}"
        except Exception as e:
            state["test_output"] = f"Failed to post comment: {str(e)}"
    
    return state


def format_failure_comment(state: AgentState) -> str:
    """Format a GitHub comment with the failure details."""
    
    fix_history = state.get("fix_history", [])
    pr_number = state.get("pr_number", 0)
    current_patch = state.get("current_patch", "")
    
    lines = [
        "## ❌ Auto-Fix Attempt Failed",
        "",
        f"I attempted to automatically fix the failing tests for PR #{pr_number}, but was unable to.",
        "",
        f"### Attempts Made: {len(fix_history)}/3",
        "",
    ]
    
    for i, attempt in enumerate(fix_history, 1):
        status = "✅ PASSED" if attempt.get('tests_passed') else "❌ FAILED"
        lines.append(f"### Attempt {i}")
        lines.append(f"- **Status**: {status}")
        lines.append(f"- **Tokens used**: {attempt.get('tokens_used', 0)}")
        lines.append(f"- **LLM response**: {'Generated patch' if attempt.get('patch') else 'No patch generated'}")
        
        test_output = attempt.get('test_output', '')
        if test_output and len(test_output) > 500:
            lines.append(f"- **Test error** (truncated):")
            for line in test_output[:500].split('\n')[:5]:
                lines.append(f"  ```")
                lines.append(f"  {line}")
                lines.append(f"  ```")
        elif test_output:
            lines.append(f"- **Test output**:")
            for line in test_output.split('\n')[:10]:
                lines.append(f"  {line}")
        
        lines.append("")
    
    if current_patch == "CANNOT_FIX":
        lines.append("### Why It Failed")
        lines.append("The LLM was unable to determine a fix for the failing tests.")
        lines.append("This typically indicates:")
        lines.append("- The bug requires domain-specific knowledge")
        lines.append("- The test failure root cause is unclear from the diff")
        lines.append("- The fix may require architectural changes")
    else:
        lines.append("### Why It Failed")
        lines.append(f"Maximum iterations ({len(fix_history)}) reached without tests passing.")
    
    lines.append("")
    lines.append("### Recommendation")
    lines.append("Please review the failing tests and fix the code manually.")
    lines.append("The agent can provide valuable context but cannot replace human judgment.")
    
    return "\n".join(lines)
