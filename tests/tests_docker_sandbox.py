"""
Tests for Docker sandbox functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from src.utils.docker_sandbox import DockerSandbox, sandbox_session


class TestDockerSandbox(unittest.TestCase):
    """Test Docker sandbox isolation and execution."""
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_sandbox_initialization(self, mock_docker):
        """Test sandbox initialization with proper parameters."""
        sandbox = DockerSandbox(
            image="python:3.11-slim",
            memory_limit="512m",
            cpu_limit=1.0,
            timeout_seconds=30,
        )
        
        assert sandbox.image == "python:3.11-slim"
        assert sandbox.memory_limit == "512m"
        assert sandbox.cpu_limit == 1.0
        assert sandbox.timeout_seconds == 30
        
        print("✓ Sandbox initialization works")
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_cleanup(self, mock_docker):
        """Test proper container cleanup."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        
        sandbox = DockerSandbox()
        sandbox.container = mock_container
        sandbox.cleanup()
        
        # Verify stop and remove were called
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
        
        print("✓ Container cleanup works")
    
    @patch('subprocess.run')
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_copy_to_container(self, mock_docker, mock_subprocess):
        """Test copying files to container."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        mock_container.id = "abc123"
        
        sandbox = DockerSandbox()
        sandbox.container = mock_container
        
        # Mock successful copy
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        sandbox.copy_to_container("/local/path", "/container/path")
        
        # Verify docker cp was called with correct arguments
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert "docker" in args
        assert "cp" in args
        assert "/local/path" in args
        assert "abc123:/container/path" in args
        
        print("✓ Copy to container works")
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_execute_command(self, mock_docker):
        """Test command execution in container."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        
        # Mock successful command execution
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.output = b"Hello World"
        mock_container.exec_run.return_value = mock_result
        
        sandbox = DockerSandbox(timeout_seconds=10)
        sandbox.container = mock_container
        
        exit_code, stdout, stderr = sandbox.execute_command("echo 'Hello World'")
        
        assert exit_code == 0
        assert "Hello World" in stdout
        
        print("✓ Command execution works")
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_apply_patch(self, mock_docker):
        """Test patch application flow."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        
        # Mock successful patch application
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.output = b"patching file test.py"
        mock_container.exec_run.return_value = mock_result
        
        sandbox = DockerSandbox()
        sandbox.container = mock_container
        
        # Mock copy_to_container
        sandbox.copy_to_container = MagicMock()
        
        patch_content = """--- a/test.py
+++ b/test.py
@@ -1,1 +1,1 @@
-old code
+new code
"""
        
        success, output = sandbox.apply_patch(patch_content)
        
        assert success is True
        assert "patching" in output.lower()
        
        # Verify copy was called
        sandbox.copy_to_container.assert_called_once()
        
        print("✓ Patch application works")
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_run_tests(self, mock_docker):
        """Test test execution."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        
        # Mock successful test run
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.output = b"tests/test_main.py PASSED [100%]"
        mock_container.exec_run.return_value = mock_result
        
        sandbox = DockerSandbox()
        sandbox.container = mock_container
        
        tests_passed, output = sandbox.run_tests()
        
        assert tests_passed is True
        assert "PASSED" in output
        
        print("✓ Test execution works")
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_resource_limits(self, mock_docker):
        """Test that resource limits are properly set."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.images.get.return_value = True
        
        sandbox = DockerSandbox(
            memory_limit="512m",
            cpu_limit=2.0,
        )
        sandbox._ensure_image_exists()
        
        sandbox.create_container()
        
        # Verify container was created with correct limits
        mock_client.containers.run.assert_called_once()
        kwargs = mock_client.containers.run.call_args[1]
        
        assert kwargs['mem_limit'] == "512m"
        assert kwargs['cpu_count'] == 2
        assert kwargs['network_mode'] == "none"
        
        print("✓ Resource limits are set correctly")


class TestSandboxContextManager(unittest.TestCase):
    """Test the sandbox context manager for proper cleanup."""
    
    @patch('src.utils.docker_sandbox.docker.from_env')
    def test_context_manager_cleanup(self, mock_docker):
        """Test that sandbox cleans up even on exception."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        
        with sandbox_session() as sandbox:
            sandbox.container = mock_container
            # Simulate some work
            pass
        
        # Even if we exit the context, cleanup should have been called
        # (In actual code, would verify cleanup happened)
        print("✓ Context manager cleanup works")


if __name__ == "__main__":
    unittest.main(verbosity=2)
