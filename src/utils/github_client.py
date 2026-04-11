"""
GitHub API integration utilities using PyGithub.
"""

import os
from typing import Tuple, Optional
from github import Github, Repository, PullRequest


class GitHubClient:
    """
    Wrapper around PyGithub for PR management.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (defaults to GITHUB_TOKEN env var)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required (GITHUB_TOKEN env var)")
        
        self.client = Github(self.token)
    
    def get_repo(self, repo_full_name: str) -> Repository.Repository:
        """Get repository object by full name (owner/repo)."""
        return self.client.get_repo(repo_full_name)
    
    def get_pr(self, repo_full_name: str, pr_number: int) -> PullRequest.PullRequest:
        """Get a specific pull request."""
        repo = self.get_repo(repo_full_name)
        return repo.get_pull(pr_number)
    
    def get_pr_raw_diff(self, repo_full_name: str, pr_number: int) -> str:
        """
        Get the raw unified diff for a PR.
        
        Returns:
            Unified diff string in `patch -p1` format
        """
        repo = self.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        
        # Get the diff by accessing the PR's patch
        return pr.as_pull_request_json().get('patch', '')
    
    def create_fix_branch(
        self,
        repo_full_name: str,
        base_sha: str,
        new_branch_name: str,
    ) -> str:
        """
        Create a new branch from an existing commit.
        
        Args:
            repo_full_name: Full repository name
            base_sha: SHA to branch from
            new_branch_name: Name of the new branch
        
        Returns:
            New branch SHA
        """
        repo = self.get_repo(repo_full_name)
        ref = repo.create_git_ref(f"refs/heads/{new_branch_name}", base_sha)
        return ref.object.sha
    
    def commit_patch(
        self,
        repo_full_name: str,
        branch_name: str,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> str:
        """
        Commit changes to a branch.
        
        Args:
            repo_full_name: Full repository name
            branch_name: Branch to commit to
            file_path: File path to update
            content: New file content
            commit_message: Commit message
        
        Returns:
            Commit SHA
        """
        repo = self.get_repo(repo_full_name)
        
        try:
            # Try to get existing file
            existing = repo.get_contents(file_path, ref=branch_name)
            result = repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=existing.sha,
                branch=branch_name,
            )
        except:
            # File doesn't exist, create it
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch_name,
            )
        
        return result['commit'].sha
    
    def open_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ) -> Tuple[str, str]:
        """
        Open a new pull request.
        
        Args:
            repo_full_name: Full repository name
            title: PR title
            body: PR description
            head_branch: Feature branch name
            base_branch: Target branch (usually 'main' or 'master')
        
        Returns:
            (pr_number, pr_url)
        """
        repo = self.get_repo(repo_full_name)
        
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
        )
        
        return pr.number, pr.html_url
    
    def post_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        comment_text: str,
    ) -> str:
        """
        Post a comment on a PR.
        
        Args:
            repo_full_name: Full repository name
            pr_number: PR number
            comment_text: Comment body
        
        Returns:
            Comment URL
        """
        pr = self.get_pr(repo_full_name, pr_number)
        comment = pr.create_issue_comment(comment_text)
        return comment.html_url
    
    def get_pr_base_branch(self, repo_full_name: str, pr_number: int) -> str:
        """Get the base branch name for a PR."""
        pr = self.get_pr(repo_full_name, pr_number)
        return pr.base.ref
    
    def get_pr_head_sha(self, repo_full_name: str, pr_number: int) -> str:
        """Get the HEAD commit SHA for a PR."""
        pr = self.get_pr(repo_full_name, pr_number)
        return pr.head.sha
