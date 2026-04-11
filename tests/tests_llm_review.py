"""
Tests for LLM review utilities and context formatting.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.utils.llm_review import create_llm_context, estimate_cost


class TestLLMContext(unittest.TestCase):
    """Test LLM context formatting."""
    
    def test_basic_context_formatting(self):
        """Test basic context creation."""
        diff = "--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-old\n+new"
        ast_context = {
            "files": {
                "test.py": {
                    "changed_functions": ["my_func"],
                    "changed_ranges": [(5, 10)],
                }
            }
        }
        
        context = create_llm_context(diff, ast_context)
        
        assert "CODE REVIEW CONTEXT" in context
        assert "test.py" in context
        assert "UNIFIED DIFF" in context
        assert "AST ANALYSIS" in context
        assert "my_func" in context
        
        print("✓ Basic context formatting works")
    
    def test_context_with_iteration_info(self):
        """Test context includes iteration number."""
        context = create_llm_context("diff", {}, iteration=2)
        
        assert "Iteration 2" in context
        
        print("✓ Iteration info included")
    
    def test_context_with_previous_patch(self):
        """Test context includes previous attempt info on retry."""
        diff = "--- a/file.py\n+++ b/file.py"
        prev_patch = "--- a/test.py"
        test_output = "FAILED test_main"
        
        context = create_llm_context(
            diff,
            {},
            previous_patch=prev_patch,
            test_output=test_output,
            iteration=1,
        )
        
        assert "PREVIOUS ATTEMPT" in context
        assert "Previous patch tried" in context
        assert "Test output from previous attempt" in context
        
        print("✓ Previous attempt info included on retry")
    
    def test_cost_estimation(self):
        """Test cost estimation function."""
        # 1000 input tokens + 500 output tokens
        cost = estimate_cost(1000, 500)
        
        # Expected: 1000 * (0.015 / 1000) + 500 * (0.06 / 1000)
        # = 0.015 + 0.03 = 0.045
        assert cost == 0.045
        
        print("✓ Cost estimation works")
    
    def test_empty_context(self):
        """Test context handles empty inputs gracefully."""
        context = create_llm_context("", {})
        
        assert "CODE REVIEW CONTEXT" in context
        assert "no diff provided" in context
        
        print("✓ Empty context handling works")
    
    def test_large_ast_context(self):
        """Test context handles large AST structures."""
        ast_context = {
            "files": {
                "main.py": {
                    "changed_functions": ["func_a", "func_b", "func_c"],
                    "all_functions": {
                        "func_a": {"name": "func_a"},
                        "func_b": {"name": "func_b"},
                    },
                    "all_classes": {
                        "MyClass": {"name": "MyClass"},
                    },
                    "changed_ranges": [(10, 20), (30, 40)],
                }
            }
        }
        
        context = create_llm_context("diff", ast_context)
        
        assert "func_a" in context
        assert "MyClass" in context
        assert "main.py" in context
        
        print("✓ Large AST context handling works")


class TestLLMReview(unittest.TestCase):
    """Test LLM review node logic."""
    
    @patch('src.utils.llm_review.OpenAI')
    def test_gpt4o_call_success(self, mock_openai_class):
        """Test successful GPT-4o call."""
        from src.utils.llm_review import call_gpt4o_for_review
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-old\n+new"
        mock_response.usage.total_tokens = 500
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 200
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            patch_str, tokens, cost = call_gpt4o_for_review(
                raw_diff="diff",
                ast_context={},
            )
        
        assert "---" in patch_str  # Valid diff format
        assert tokens == 500
        assert cost > 0
        
        print("✓ GPT-4o call success")
    
    @patch('src.utils.llm_review.OpenAI')
    def test_gpt4o_cannot_fix_response(self, mock_openai_class):
        """Test handling of CANNOT_FIX response."""
        from src.utils.llm_review import call_gpt4o_for_review
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "CANNOT_FIX"
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 80
        mock_response.usage.completion_tokens = 20
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            patch_str, tokens, cost = call_gpt4o_for_review(
                raw_diff="diff",
                ast_context={},
            )
        
        assert patch_str == "CANNOT_FIX"
        
        print("✓ CANNOT_FIX handling works")
    
    def test_missing_api_key(self):
        """Test error handling when API key is missing."""
        from src.utils.llm_review import call_gpt4o_for_review
        
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                call_gpt4o_for_review("diff", {})
        
        print("✓ Missing API key error handling works")


if __name__ == "__main__":
    unittest.main(verbosity=2)
