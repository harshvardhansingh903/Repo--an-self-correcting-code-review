"""
Tests for GitHub integration utilities.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.utils.github_webhook import verify_webhook_signature, parse_pr_event


class TestWebhookSignature(unittest.TestCase):
    """Test GitHub webhook signature verification."""
    
    def test_valid_signature(self):
        """Test validation of correct signature."""
        secret = "test-secret"
        payload = b'{"action":"opened"}'
        
        # Generate correct signature
        import hmac
        import hashlib
        
        signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        result = verify_webhook_signature(payload, signature, secret)
        assert result is True
        
        print("✓ Valid signature verification works")
    
    def test_invalid_signature(self):
        """Test rejection of invalid signature."""
        secret = "test-secret"
        payload = b'{"action":"opened"}'
        invalid_signature = "sha256=invalid"
        
        result = verify_webhook_signature(payload, invalid_signature, secret)
        assert result is False
        
        print("✓ Invalid signature rejection works")
    
    def test_missing_sha256_prefix(self):
        """Test rejection of malformed signature."""
        result = verify_webhook_signature(b"payload", "invalid", "secret")
        assert result is False
        
        print("✓ Malformed signature rejection works")
    
    def test_empty_header(self):
        """Test handling of empty signature header."""
        result = verify_webhook_signature(b"payload", "", "secret")
        assert result is False
        
        print("✓ Empty header rejection works")


class TestPREventParsing(unittest.TestCase):
    """Test GitHub PR event parsing."""
    
    def test_parse_pr_opened_event(self):
        """Test parsing of PR opened event."""
        event = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Fix bug",
                "base": {"ref": "main"},
                "head": {"sha": "abc123"},
                "html_url": "https://github.com/owner/repo/pull/123",
            },
            "repository": {
                "full_name": "owner/repo",
                "name": "repo",
                "owner": {"login": "owner"},
            }
        }
        
        result = parse_pr_event(event)
        
        assert result is not None
        assert result["pr_number"] == 123
        assert result["repo_full_name"] == "owner/repo"
        assert result["action"] == "opened"
        assert result["pr_title"] == "Fix bug"
        
        print("✓ PR opened event parsing works")
    
    def test_ignore_pr_closed_event(self):
        """Test that non-opened PR events are ignored."""
        event = {
            "action": "closed",
            "pull_request": {"number": 123},
            "repository": {"full_name": "owner/repo"},
        }
        
        result = parse_pr_event(event)
        assert result is None
        
        print("✓ PR closed event is ignored")
    
    def test_ignore_non_pr_event(self):
        """Test that non-PR events are ignored."""
        event = {
            "action": "opened",
            "issue": {"number": 123},  # Not a PR
            "repository": {"full_name": "owner/repo"},
        }
        
        result = parse_pr_event(event)
        assert result is None
        
        print("✓ Non-PR events are ignored")
    
    def test_parse_pr_synced_event(self):
        """Test that only 'opened' action is processed."""
        event = {
            "action": "synchronize",  # PR updated with new commits
            "pull_request": {"number": 123},
            "repository": {"full_name": "owner/repo"},
        }
        
        result = parse_pr_event(event)
        assert result is None
        
        print("✓ PR synchronize event is ignored")


class TestGitHubClient(unittest.TestCase):
    """Test GitHub API client (mocked)."""
    
    @patch('src.utils.github_client.Github')
    def test_client_initialization(self, mock_github_class):
        """Test GitHub client initialization."""
        from src.utils.github_client import GitHubClient
        
        mock_github_class.return_value = MagicMock()
        
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}):
            client = GitHubClient()
            assert client.token == 'test-token'
        
        print("✓ GitHub client initialization works")
    
    def test_missing_token(self):
        """Test error when GitHub token is missing."""
        from src.utils.github_client import GitHubClient
        
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                GitHubClient()
        
        print("✓ Missing token error handling works")


if __name__ == "__main__":
    unittest.main(verbosity=2)
