"""
GitHub webhook signature validation and event parsing.
"""

import hmac
import hashlib
import json
from typing import Optional, Dict, Any


def verify_webhook_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """
    Verify GitHub webhook signature using X-Hub-Signature-256 header.
    
    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: Webhook secret registered in GitHub
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False
    
    # X-Hub-Signature-256 format: sha256=<hex_digest>
    if not signature_header.startswith("sha256="):
        return False
    
    signature_received = signature_header[7:]  # Remove "sha256=" prefix
    
    # Compute expected signature
    computed_hmac = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256,
    )
    signature_expected = computed_hmac.hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature_received, signature_expected)


def parse_pr_event(event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a GitHub PR event and extract relevant information.
    
    Args:
        event_data: Parsed JSON payload from webhook
    
    Returns:
        Dict with keys: pr_number, action, repo_full_name, repo_owner, repo_name
        Returns None if not a PR event or action we care about
    """
    
    # Only care about pull_request events
    if 'pull_request' not in event_data:
        return None
    
    # Only care about "opened" action (when PR is created)
    action = event_data.get('action')
    if action != 'opened':
        return None
    
    pr = event_data['pull_request']
    repo = event_data['repository']
    
    return {
        'pr_number': pr['number'],
        'action': action,
        'repo_full_name': repo['full_name'],
        'repo_owner': repo['owner']['login'],
        'repo_name': repo['name'],
        'pr_title': pr['title'],
        'pr_base_branch': pr['base']['ref'],
        'pr_head_sha': pr['head']['sha'],
        'pr_url': pr['html_url'],
    }
