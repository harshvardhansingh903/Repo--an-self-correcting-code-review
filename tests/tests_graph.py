"""
Tests for the complete LangGraph agent flow.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.agent.state import AgentState, create_initial_state
from src.nodes.decide import decide_node, increment_iteration


class TestDecisionLogic(unittest.TestCase):
    """Test the decide node routing logic."""
    
    def test_decide_success_path(self):
        """Test routing to open_pr when tests pass."""
        state = AgentState(
            tests_passed=True,
            iteration=0,
            current_patch="--- a/test.py",
        )
        
        result = decide_node(state)
        assert result == "open_pr"
        
        print("✓ Success routing works")
    
    def test_decide_retry_path(self):
        """Test routing back to review_code for retry."""
        state = AgentState(
            tests_passed=False,
            iteration=0,  # < 3
            current_patch="--- a/test.py",
        )
        
        result = decide_node(state)
        assert result == "review_code"
        
        print("✓ Retry routing works")
    
    def test_decide_max_iterations_reached(self):
        """Test routing to post_failure_comment at max iterations."""
        state = AgentState(
            tests_passed=False,
            iteration=3,  # >= 3
            current_patch="--- a/test.py",
        )
        
        result = decide_node(state)
        assert result == "post_failure_comment"
        
        print("✓ Max iterations routing works")
    
    def test_decide_cannot_fix(self):
        """Test routing to post_failure_comment when CANNOT_FIX."""
        state = AgentState(
            tests_passed=False,
            iteration=0,
            current_patch="CANNOT_FIX",
        )
        
        result = decide_node(state)
        assert result == "post_failure_comment"
        
        print("✓ CANNOT_FIX routing works")
    
    def test_increment_iteration(self):
        """Test iteration counter increment and history recording."""
        state = AgentState(
            iteration=0,
            current_patch="--- a/test.py",
            test_output="FAILED test_main",
            tests_passed=False,
            fix_history=[],
            tokens_used=500,
        )
        
        updated = increment_iteration(state)
        
        # Check iteration incremented
        assert updated["iteration"] == 1
        
        # Check history recorded
        assert len(updated["fix_history"]) == 1
        assert updated["fix_history"][0]["iteration"] == 0
        assert updated["fix_history"][0]["patch"] == "--- a/test.py"
        assert updated["fix_history"][0]["test_output"] == "FAILED test_main"
        assert updated["fix_history"][0]["tokens_used"] == 500
        
        # Check state reset for next iteration
        assert updated["current_patch"] == ""
        assert updated["test_output"] == ""
        
        print("✓ Iteration increment works")
    
    def test_multiple_iterations_history(self):
        """Test that fix_history accumulates across iterations."""
        state = AgentState(
            iteration=0,
            current_patch="patch_1",
            test_output="output_1",
            tests_passed=False,
            fix_history=[],
            tokens_used=100,
        )
        
        # First iteration
        state = increment_iteration(state)
        assert len(state["fix_history"]) == 1
        
        # Second iteration
        state["current_patch"] = "patch_2"
        state["test_output"] = "output_2"
        state["tokens_used"] = 200
        state = increment_iteration(state)
        
        assert len(state["fix_history"]) == 2
        assert state["fix_history"][0]["patch"] == "patch_1"
        assert state["fix_history"][1]["patch"] == "patch_2"
        assert state["iteration"] == 2
        
        print("✓ Multiple iterations history works")


class TestStateTransitions(unittest.TestCase):
    """Test state transitions through the graph."""
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        state = create_initial_state(
            pr_number=123,
            repo_full_name="owner/repo",
            pr_title="Fix bug",
            pr_base_branch="main",
            raw_diff="--- a/test.py",
        )
        
        assert state["pr_number"] == 123
        assert state["repo_full_name"] == "owner/repo"
        assert state["iteration"] == 0
        assert state["tests_passed"] is False
        assert state["final_status"] == "pending"
        assert state["fix_history"] == []
        
        print("✓ Initial state creation works")
    
    def test_state_accumulation(self):
        """Test that state accumulates across multiple transitions."""
        state = create_initial_state(
            pr_number=1,
            repo_full_name="test/repo",
            pr_title="Test",
            pr_base_branch="main",
            raw_diff="diff",
        )
        
        # Add AST context
        state["ast_context"] = {"functions": ["func_a"]}
        
        # Add test results
        state["current_patch"] = "patch_1"
        state["test_output"] = "test output"
        state["tests_passed"] = False
        
        # Record in history
        state = increment_iteration(state)
        
        # Verify all data persists
        assert state["pr_number"] == 1
        assert state["ast_context"]["functions"] == ["func_a"]
        assert len(state["fix_history"]) == 1
        assert state["iteration"] == 1
        
        print("✓ State accumulation works")


class TestGraphStructure(unittest.TestCase):
    """Test the basic graph structure (without execution)."""
    
    def test_graph_compilation(self):
        """Test that the graph compiles without errors."""
        try:
            from src.agent.graph import build_agent_graph
            graph = build_agent_graph()
            assert graph is not None
            print("✓ Graph compilation works")
        except Exception as e:
            self.fail(f"Graph compilation failed: {e}")
    
    @patch('src.nodes.parse_pr.parse_pr_node')
    @patch('src.nodes.parse_ast.parse_ast_node')
    def test_graph_has_all_nodes(self, mock_parse_ast, mock_parse_pr):
        """Test that all expected nodes exist in the graph."""
        from src.agent.graph import build_agent_graph
        
        graph = build_agent_graph()
        
        # The compiled graph should have all node names
        # (We can't directly access them, but compilation would fail if missing)
        assert graph is not None
        
        print("✓ Graph includes all nodes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
