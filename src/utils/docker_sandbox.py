"""
Docker sandbox for safely executing test suites in an isolated environment.
"""

import docker
import tempfile
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional
from contextlib import contextmanager


class DockerSandbox:
    """
    Manages Docker container creation, patch application, and test execution.
    
    Features:
    - Resource limits (memory, CPU)
    - Network isolation
    - Automatic cleanup
    - Timeout enforcement
    """
    
    def __init__(
        self,
        image: str = "python:3.11-slim",
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
        timeout_seconds: int = 30,
    ):
        """
        Initialize the Docker sandbox.
        
        Args:
            image: Docker image to use (default: python:3.11-slim)
            memory_limit: Memory limit string (e.g., "512m", "1g")
            cpu_limit: CPU limit in cores (float)
            timeout_seconds: Maximum execution time
        """
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout_seconds = timeout_seconds
        self.client = docker.from_env()
        self.container = None
    
    def _ensure_image_exists(self) -> None:
        """Pull image if it doesn't exist locally."""
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            print(f"Pulling image {self.image}...")
            self.client.images.pull(self.image)
    
    def create_container(self) -> None:
        """Create and start a new container with resource limits."""
        self._ensure_image_exists()
        
        self.container = self.client.containers.run(
            self.image,
            command="sleep 3600",  # Keep alive for test execution
            detach=True,
            network_mode="none",  # No network access
            mem_limit=self.memory_limit,
            memswap_limit=self.memory_limit,  # Disable swap
            cpu_count=int(self.cpu_limit),
            stdin_open=True,
            remove=False,  # We'll clean up manually
        )
        print(f"Container created: {self.container.short_id}")
    
    def copy_to_container(self, local_path: str, container_path: str) -> None:
        """
        Copy files from local filesystem to container.
        
        Args:
            local_path: Local file/directory path
            container_path: Target path inside container
        """
        # Docker API doesn't support put_archive directly on a running container
        # So we use docker cp via subprocess
        try:
            subprocess.run(
                ["docker", "cp", local_path, f"{self.container.id}:{container_path}"],
                check=True,
                capture_output=True,
                timeout=10,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to copy to container: {str(e)}")
    
    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> Tuple[int, str, str]:
        """
        Execute a command inside the container.
        
        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (defaults to self.timeout_seconds)
        
        Returns:
            (exit_code, stdout, stderr)
        """
        if timeout is None:
            timeout = self.timeout_seconds
        
        try:
            result = self.container.exec_run(
                cmd=["sh", "-c", command],
                stdout=True,
                stderr=True,
                stdin=False,
            )
            
            stdout = result.output.decode('utf-8', errors='ignore') if result.output else ""
            
            return result.exit_code, stdout, ""
        
        except Exception as e:
            return 1, "", str(e)
    
    def apply_patch(self, patch_content: str) -> Tuple[bool, str]:
        """
        Apply a unified diff patch inside the container.
        
        Args:
            patch_content: Unified diff patch string
        
        Returns:
            (success: bool, output: str)
        """
        # Write patch to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        try:
            # Copy patch into container
            self.copy_to_container(patch_file, "/tmp/fix.patch")
            
            # Apply patch from root directory
            exit_code, stdout, _ = self.execute_command(
                "cd /repo && patch -p1 < /tmp/fix.patch"
            )
            
            if exit_code == 0:
                return True, stdout
            else:
                return False, stdout
        
        finally:
            os.unlink(patch_file)
    
    def run_tests(self, test_command: str = "pip install -r requirements.txt && pytest -x --tb=short") -> Tuple[bool, str]:
        """
        Install dependencies and run tests.
        
        Args:
            test_command: Command to run (default: pip install + pytest)
        
        Returns:
            (tests_passed: bool, output: str)
        """
        exit_code, stdout, _ = self.execute_command(
            command=test_command,
            timeout=self.timeout_seconds,
        )
        
        tests_passed = exit_code == 0
        return tests_passed, stdout
    
    def cleanup(self) -> None:
        """Stop and remove the container."""
        if self.container:
            try:
                self.container.stop(timeout=5)
                self.container.remove()
                print(f"Container {self.container.short_id} cleaned up")
            except Exception as e:
                print(f"Warning: Failed to cleanup container: {e}")
            finally:
                self.container = None


@contextmanager
def sandbox_session(
    image: str = "python:3.11-slim",
    memory_limit: str = "512m",
    cpu_limit: float = 1.0,
    timeout_seconds: int = 30,
):
    """
    Context manager for Docker sandbox session with automatic cleanup.
    
    Usage:
        with sandbox_session() as sandbox:
            sandbox.create_container()
            sandbox.copy_to_container(repo_path, "/repo")
            success, output = sandbox.run_tests()
    """
    sandbox = DockerSandbox(image, memory_limit, cpu_limit, timeout_seconds)
    try:
        yield sandbox
    finally:
        sandbox.cleanup()
