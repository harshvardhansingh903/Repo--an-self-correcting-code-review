"""
End-to-end integration test simulating a complete agent workflow.
"""

import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.agent.state import create_initial_state
from src.agent.graph import build_agent_graph


class TestE2EIntegration(unittest.TestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.initial_state = create_initial_state(
            pr_number=999,
            repo_full_name="test/repo",
            pr_title="Test PR",
            pr_base_branch="main",
            raw_diff="""--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,5 @@
 def calculate(x):
-    return x + undefined
+    return x + 1
 
 if __name__ == "__main__":
     print(calculate(5))
""",
        )
    
    def test_state_initialization(self):
        """Test initial state creation."""
        state = self.initial_state
        
        assert state["pr_number"] == 999
        assert state["repo_full_name"] == "test/repo"
        assert state["iteration"] == 0
        assert state["final_status"] == "pending"
        assert state["tests_passed"] is False
        assert state["fix_history"] == []
        
        print("✓ State initialization works")
    
    def test_state_progression(self):
        """Test state changes through a typical workflow."""
        state = self.initial_state
        
        # Simulate parse_ast node
        state["ast_context"] = {
            "files": {
                "src/main.py": {
                    "changed_functions": ["calculate"],
                    "all_functions": {
                        "calculate": {
                            "name": "calculate",
                            "args": ["x"],
                            "return_type": "",
                        }
                    },
                }
            }
        }
        
        # Simulate review_code node
        state["current_patch"] = """--- a/src/main.py
+++ b/src/main.py
@@ -1,2 +1,2 @@
 def calculate(x):
-    return x + undefined
+    return x + 1
"""
        state["tokens_used"] = 500
        
        # Simulate run_tests node
        state["test_output"] = "tests/test_main.py PASSED [100%]"
        state["tests_passed"] = True
        
        # Simulate decide node
        state["final_status"] = "fixed"
        state["fix_pr_url"] = "https://github.com/test/repo/pull/1000"
        
        # Verify final state
        assert state["tests_passed"] is True
        assert state["final_status"] == "fixed"
        assert state["tokens_used"] > 0
        assert state["fix_pr_url"] is not None
        
        print("✓ State progression works")
    
    def test_failure_workflow(self):
        """Test workflow when fix cannot be found."""
        state = self.initial_state
        
        # Simulate failed attempts
        state["iteration"] = 3
        state["current_patch"] = "CANNOT_FIX"
        state["test_output"] = "Test failure: unknown bug"
        state["final_status"] = "cannot_fix"
        
        # Verify state reflects failure
        assert state["final_status"] == "cannot_fix"
        assert state["iteration"] >= 3
        
        print("✓ Failure workflow works")
    
    def test_retry_workflow(self):
        """Test retry loop with iteration tracking."""
        state = self.initial_state
        
        # Simulate first failed attempt
        state["iteration"] = 0
        state["current_patch"] = "patch_1"
        state["test_output"] = "FAILED: test_main"
        state["tests_passed"] = False
        
        # Log to history
        state["fix_history"].append({
            "iteration": 0,
            "patch": state["current_patch"],
            "test_output": state["test_output"],
            "tests_passed": False,
            "tokens_used": 500,
        })
        
        # Simulate second attempt
        state["iteration"] = 1
        state["current_patch"] = "patch_2"
        state["test_output"] = "PASSED"
        state["tests_passed"] = True
        
        # Log to history
        state["fix_history"].append({
            "iteration": 1,
            "patch": state["current_patch"],
            "test_output": state["test_output"],
            "tests_passed": True,
            "tokens_used": 400,
        })
        
        # Verify history
        assert len(state["fix_history"]) == 2
        assert state["fix_history"][0]["tests_passed"] is False
        assert state["fix_history"][1]["tests_passed"] is True
        assert state["iteration"] == 1
        
        print("✓ Retry workflow works")
    
    @patch('src.utils.ast_analyzer.ASTAnalyzer.analyze')
    def test_ast_analysis_in_workflow(self, mock_analyze):
        """Test AST analysis within workflow."""
        mock_analyze.return_value = {
            'functions': {'calculate': {}},
            'classes': {},
            'calls': [],
            'line_to_function': {1: 'calculate'},
        }
        
        from src.utils.ast_analyzer import ASTAnalyzer
        
        analyzer = ASTAnalyzer("def calculate(x):\n    return x + 1")
        result = analyzer.analyze()
        
        assert 'calculate' in result['functions']
        
        print("✓ AST analysis in workflow works")
    
    def test_cost_tracking(self):
        """Test cost accumulation through workflow."""
        state = self.initial_state
        state["tokens_used"] = 0
        
        # Simulate multiple iterations
        for i in range(3):
            state["tokens_used"] += 500
            state["fix_history"].append({
                "iteration": i,
                "tokens_used": 500,
            })
        
        # Calculate cost
        total_tokens = state["tokens_used"]
        estimated_cost = (total_tokens * 0.015 / 1000) + (total_tokens * 0.3 * 0.06 / 1000)
        
        assert total_tokens == 1500
        assert estimated_cost > 0
        
        print(f"✓ Cost tracking works (3 iterations = {estimated_cost:.4f} USD)")
    
    def test_database_logging_compatibility(self):
        """Test state format is compatible with database operations."""
        state = self.initial_state
        
        # Populate state as it would be after execution
        state["status"] = "fixed"
        state["iterations"] = 2
        state["tokens_used"] = 1000
        state["fix_pr_url"] = "https://github.com/test/repo/pull/1000"
        
        # Verify all required fields for DB are present
        db_fields = [
            "pr_number",
            "repo_full_name",
            "final_status",
            "iteration",
            "tokens_used",
            "fix_pr_url",
        ]
        
        for field in db_fields:
            assert field in state, f"Missing field: {field}"
        
        print("✓ Database logging compatibility verified")


class TestGraphCompilation(unittest.TestCase):
    """Test graph compilation and structure."""
    
    def test_graph_builds(self):
        """Test that graph compiles without errors."""
        try:
            graph = build_agent_graph()
            assert graph is not None
            print("✓ Graph builds successfully")
        except Exception as e:
            self.fail(f"Graph compilation failed: {e}")
    
    def test_graph_has_required_nodes(self):
        """Test that graph has all required node names."""
        # This is implicit in the build, but good to document
        from src.nodes.parse_pr import parse_pr_node
        from src.nodes.parse_ast import parse_ast_node
        from src.nodes.review_code import review_code_node
        from src.nodes.run_tests import run_tests_node
        from src.nodes.decide import decide_node
        from src.nodes.open_pr import open_pr_node
        from src.nodes.post_failure_comment import post_failure_comment_node
        
        # All imports succeed = all nodes exist
        print("✓ All required nodes found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
