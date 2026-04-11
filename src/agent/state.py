"""
LangGraph AgentState schema for the self-correcting code review agent.
"""

from typing import TypedDict
from dataclasses import dataclass, field


class AgentState(TypedDict, total=False):
    """
    State object passed between all LangGraph nodes.
    
    This TypedDict holds the complete context for a code review session,
    including the PR details, AST analysis, patches, test results, and
    historical data for iterative refinement.
    """
    
    # GitHub PR Context
    pr_number: int
    repo_full_name: str  # e.g., "owner/repo"
    pr_title: str
    pr_base_branch: str
    
    # Code Analysis
    raw_diff: str  # The full unified diff from the PR
    ast_context: dict  # Extracted AST analysis {file_path: {functions, classes, call_graph, ...}}
    
    # Patching & Testing
    current_patch: str  # LLM-generated unified diff patch for current iteration
    test_output: str  # stdout + stderr from pytest execution
    tests_passed: bool
    
    # Iteration Tracking
    iteration: int  # 0-indexed, max 3
    fix_history: list  # [{patch: str, test_output: str, iteration: int, passed: bool}, ...]
    
    # Final Status
    final_status: str  # "fixed" | "failed_max_iterations" | "cannot_fix" | "pending"
    
    # Metadata
    tokens_used: int
    created_at: str
    fix_pr_url: str  # URL of the corrected PR opened by the agent


class IterationRecord(TypedDict):
    """Record of a single fix attempt."""
    iteration: int
    patch: str
    test_output: str
    tests_passed: bool
    tokens_used: int


# Helper to create initial state from PR info
def create_initial_state(
    pr_number: int,
    repo_full_name: str,
    pr_title: str,
    pr_base_branch: str,
    raw_diff: str,
) -> AgentState:
    """Factory function to create a new AgentState from PR metadata."""
    return AgentState(
        pr_number=pr_number,
        repo_full_name=repo_full_name,
        pr_title=pr_title,
        pr_base_branch=pr_base_branch,
        raw_diff=raw_diff,
        ast_context={},
        current_patch="",
        test_output="",
        tests_passed=False,
        iteration=0,
        fix_history=[],
        final_status="pending",
        tokens_used=0,
        created_at="",
        fix_pr_url="",
    )
