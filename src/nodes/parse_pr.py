"""
Parse PR node: Fetch GitHub PR details and extract raw diff.
"""

from src.agent.state import AgentState
from src.utils.github_client import GitHubClient
from typing import Optional


def parse_pr_node(state: AgentState) -> AgentState:
    """
    Fetch the PR from GitHub and extract the raw unified diff.
    
    Provides the raw_diff for AST analysis in the next node.
    
    Args:
        state: Current agent state with pr_number and repo_full_name
    
    Returns:
        Updated state with raw_diff populated
    """
    
    pr_number = state.get("pr_number")
    repo_full_name = state.get("repo_full_name")
    
    if not pr_number or not repo_full_name:
        state["raw_diff"] = ""
        return state
    
    try:
        client = GitHubClient()
        
        # Get PR diff
        pr = client.get_pr(repo_full_name, pr_number)
        
        # Get full raw diff
        raw_diff = pr.as_pull_request_json().get('diff', '')
        
        state["raw_diff"] = raw_diff
        
        return state
    
    except Exception as e:
        state["raw_diff"] = ""
        state["test_output"] = f"Failed to fetch PR: {str(e)}"
        return state
