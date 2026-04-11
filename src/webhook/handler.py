"""
FastAPI webhook receiver for GitHub PR events.
"""

import os
import json
from fastapi import FastAPI, Request, HTTPException, Header
from typing import Optional

from src.utils.github_webhook import verify_webhook_signature, parse_pr_event
from src.agent.state import create_initial_state


app = FastAPI(title="Code Review Agent")


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
):
    """
    Receive GitHub PR webhook events.
    
    Args:
        request: FastAPI request object
        x_hub_signature_256: GitHub webhook signature header
    
    Returns:
        Status message
    """
    
    # Get webhook secret from environment
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    # Read request body
    body = await request.body()
    
    # Verify webhook signature
    if not verify_webhook_signature(body, x_hub_signature_256 or "", webhook_secret):
        raise HTTPException(status_code=401, detail="Webhook signature invalid")
    
    # Parse event
    try:
        event_data = json.loads(body.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Extract PR info
    pr_info = parse_pr_event(event_data)
    if not pr_info:
        # Not a PR opened event, just acknowledge
        return {"status": "ignored"}
    
    # TODO: Implement proper job queue (Redis + Celery or RQ)
    # Currently processes one PR at a time, which blocks.
    # For production: need queuing to handle burst traffic.
    # For now, create initial state that would be used
    initial_state = create_initial_state(
        pr_number=pr_info['pr_number'],
        repo_full_name=pr_info['repo_full_name'],
        pr_title=pr_info['pr_title'],
        pr_base_branch=pr_info['pr_base_branch'],
        raw_diff="",  # Will be fetched by parse_pr node
    )
    
    return {
        "status": "accepted",
        "pr_number": pr_info['pr_number'],
        "repo": pr_info['repo_full_name'],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8000))
    
    uvicorn.run(app, host=host, port=port)
