"""
Database operations for logging review results.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.db.models import Review, IterationRecord, get_session
from src.agent.state import AgentState


async def create_review_session(
    pr_number: int,
    repo: str,
) -> int:
    """
    Create a new review session in the database.
    
    Args:
        pr_number: GitHub PR number
        repo: Repository full name
    
    Returns:
        review_id
    """
    session = await get_session()
    
    review = Review(
        pr_number=pr_number,
        repo=repo,
        status="pending",
        iterations=0,
        tokens_used=0,
        cost_usd=0.0,
    )
    
    session.add(review)
    await session.commit()
    await session.refresh(review)
    
    review_id = review.id
    await session.close()
    
    return review_id


async def log_iteration(
    review_id: int,
    iteration_num: int,
    patch: str,
    test_output: str,
    tests_passed: bool,
    tokens_used: int,
) -> None:
    """
    Log a single iteration attempt to the database.
    
    Args:
        review_id: Review session ID
        iteration_num: Iteration number (0-indexed)
        patch: Patch content
        test_output: Test execution output
        tests_passed: Whether tests passed
        tokens_used: LLM tokens used
    """
    session = await get_session()
    
    record = IterationRecord(
        review_id=review_id,
        iteration_num=iteration_num,
        patch=patch,
        test_output=test_output,
        tests_passed=tests_passed,
        tokens_used=tokens_used,
    )
    
    session.add(record)
    await session.commit()
    await session.close()


async def finalize_review(
    review_id: int,
    state: AgentState,
) -> None:
    """
    Mark a review session as complete.
    
    Args:
        review_id: Review session ID
        state: Final agent state
    """
    session = await get_session()
    
    # Update review record
    stmt = update(Review).where(
        Review.id == review_id
    ).values(
        status=state.get("final_status", "pending"),
        iterations=state.get("iteration", 0),
        tokens_used=state.get("tokens_used", 0),
        fix_pr_url=state.get("fix_pr_url"),
        completed_at=datetime.utcnow(),
    )
    
    await session.execute(stmt)
    await session.commit()
    await session.close()


async def get_review_summary(review_id: int) -> dict:
    """
    Get summary of a review session.
    
    Args:
        review_id: Review session ID
    
    Returns:
        Dictionary with review details and iteration records
    """
    session = await get_session()
    
    # Fetch review
    stmt = select(Review).where(Review.id == review_id)
    result = await session.execute(stmt)
    review = result.scalar_one_or_none()
    
    if not review:
        await session.close()
        return None
    
    # Fetch iterations
    stmt = select(IterationRecord).where(IterationRecord.review_id == review_id)
    result = await session.execute(stmt)
    iterations = result.scalars().all()
    
    summary = review.to_dict()
    summary['iterations_detail'] = [it.to_dict() for it in iterations]
    
    await session.close()
    
    return summary


async def get_all_reviews(limit: int = 100) -> list:
    """
    Get all review sessions (for dashboard/reporting).
    
    Args:
        limit: Maximum number of reviews to return
    
    Returns:
        List of review dictionaries
    """
    session = await get_session()
    
    stmt = select(Review).order_by(Review.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    reviews = result.scalars().all()
    
    review_dicts = [r.to_dict() for r in reviews]
    
    await session.close()
    
    return review_dicts
