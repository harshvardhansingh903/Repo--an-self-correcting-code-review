"""
LangGraph StateGraph definition for the self-correcting code review agent.

Graph flow:
  parse_pr (fetch PR details)
    ↓
  parse_ast (extract code structure)
    ↓
  review_code (LLM generates patch)
    ↓
  run_tests (Docker executes tests)
    ↓
  decide (conditional routing)
    ├─ tests_passed → open_pr → END
    ├─ cannot_fix → post_failure_comment → END
    ├─ max_iterations → post_failure_comment → END
    └─ retry → increment_iteration → review_code (loop back)
"""

from langgraph.graph import StateGraph, END
from src.agent.state import AgentState

# Import node implementations
from src.nodes.parse_pr import parse_pr_node
from src.nodes.parse_ast import parse_ast_node
from src.nodes.review_code import review_code_node
from src.nodes.run_tests import run_tests_node
from src.nodes.decide import decide_node, increment_iteration
from src.nodes.open_pr import open_pr_node
from src.nodes.post_failure_comment import post_failure_comment_node


def build_agent_graph():
    """
    Construct the LangGraph StateGraph for the code review agent.
    
    The graph implements the self-correcting loop:
    1. Parse PR metadata and raw diff
    2. Extract AST context from changed code
    3. Use LLM to generate fix patch
    4. Run tests in isolated Docker sandbox
    5. Decide: Success? Fail? Retry with context?
    
    Note: Originally tried using a dict-based state but TypedDict is better
    for type hints and editor autocomplete. Much better DX.
    
    Returns:
        CompiledGraph: Compiled graph ready for execution.
    """
    graph = StateGraph(AgentState)
    
    # Add all nodes
    graph.add_node("parse_pr", parse_pr_node)
    graph.add_node("parse_ast", parse_ast_node)
    graph.add_node("review_code", review_code_node)
    graph.add_node("run_tests", run_tests_node)
    graph.add_node("decide", decide_node)
    graph.add_node("open_pr", open_pr_node)
    graph.add_node("post_failure_comment", post_failure_comment_node)
    
    # Sequential edges (basic flow)
    graph.add_edge("parse_pr", "parse_ast")
    graph.add_edge("parse_ast", "review_code")
    graph.add_edge("review_code", "run_tests")
    graph.add_edge("run_tests", "decide")
    
    # Conditional edges from decide
    def decide_next_node(state: AgentState) -> str:
        """Route based on test results and iteration count."""
        return decide_node(state)
    
    graph.add_conditional_edges(
        "decide",
        decide_next_node,
        {
            "open_pr": "open_pr",
            "post_failure_comment": "post_failure_comment",
            "review_code": "increment_iteration_node",
        }
    )
    
    # Special node for incrementing iteration and looping back
    graph.add_node("increment_iteration_node", increment_iteration)
    graph.add_edge("increment_iteration_node", "review_code")
    
    # Terminal edges
    graph.add_edge("open_pr", END)
    graph.add_edge("post_failure_comment", END)
    
    # Set entry point
    graph.set_entry_point("parse_pr")
    
    # Compile and return
    return graph.compile()


if __name__ == "__main__":
    # Build graph for testing
    compiled_graph = build_agent_graph()
    print("✓ Agent graph compiled successfully")
    print(f"Graph structure: {compiled_graph}")
    
    # Print graph visualization description
    print("\nGraph Flow:")
    print("  parse_pr → parse_ast → review_code ↘")
    print("                              ↘ run_tests → decide →┐")
    print("                                                    ├→ open_pr → END")
    print("                                                    ├→ post_failure_comment → END")
    print("                                                    └→ increment_iteration_node → review_code (loop)")
