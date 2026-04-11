"""
AST Parser node: Extract function definitions, classes, and call graphs from code.
"""

import tempfile
import os
from pathlib import Path
from src.agent.state import AgentState
from src.utils.ast_analyzer import extract_changed_functions, parse_diff
from typing import Dict, Any


def parse_ast_node(state: AgentState) -> AgentState:
    """
    Parse the raw diff and extract AST-level context from changed Python files.
    
    This node:
    1. Parses the unified diff to identify changed files and line ranges
    2. For each Python file, runs AST analysis
    3. Extracts function/class definitions, signatures, type hints, call graphs
    4. Identifies which functions/classes were modified
    5. Builds structured context dict for LLM
    
    Args:
        state: Must contain raw_diff
    
    Returns:
        Updated state with ast_context populated
    """
    raw_diff = state.get("raw_diff", "")
    if not raw_diff:
        state["ast_context"] = {"error": "No raw_diff provided"}
        return state
    
    # Parse diff to get file paths and changed ranges
    changed_files = parse_diff(raw_diff)
    
    ast_context = {
        "files": {},
        "summary": {
            "total_files": len(changed_files),
            "total_changed_functions": 0,
        }
    }
    
    # For each Python file in the diff, perform AST analysis
    for file_path in changed_files:
        # Filter to Python files only
        if not file_path.endswith('.py'):
            continue
        
        # TODO: In production, fetch file content from GitHub/git history
        # For now, demonstrate the AST analysis structure
        file_analysis = {
            "path": file_path,
            "changed_ranges": changed_files[file_path],
            "functions": {},
            "classes": {},
            "changed_functions": [],
            "call_graph": [],
        }
        
        # Mock placeholder: In real implementation:
        # 1. Clone repo or get file from GitHub
        # 2. Read file content
        # 3. Call extract_changed_functions(source_code, diff_str, file_path)
        # 4. Populate file_analysis with results
        
        ast_context["files"][file_path] = file_analysis
    
    # Update state
    state["ast_context"] = ast_context
    return state


def _extract_ast_from_files(
    repo_path: str,
    changed_files: Dict[str, list],
    raw_diff: str,
) -> Dict[str, Any]:
    """
    Helper to extract AST from actual files on disk.
    
    Args:
        repo_path: Root directory of the repository
        changed_files: Mapping from parse_diff output
        raw_diff: Full unified diff string
    
    Returns:
        ast_context dict ready for LLM
    """
    ast_context = {"files": {}}
    
    for file_path, ranges in changed_files.items():
        if not file_path.endswith('.py'):
            continue
        
        full_path = os.path.join(repo_path, file_path)
        if not os.path.exists(full_path):
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            ast_context["files"][file_path] = {
                "error": f"Failed to read file: {str(e)}"
            }
            continue
        
        # Extract AST info for this file
        analysis = extract_changed_functions(source_code, raw_diff, file_path)
        
        file_info = {
            "path": file_path,
            "changed_ranges": ranges,
            "all_functions": analysis['all_functions'],
            "all_classes": analysis['all_classes'],
            "changed_functions": analysis['changed_functions'],
            "call_graph": analysis['all_calls'],
            "parse_error": analysis.get('parse_error'),
        }
        
        ast_context["files"][file_path] = file_info
    
    return ast_context
