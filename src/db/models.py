"""
SQLAlchemy ORM models for tracking code review sessions.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

Base = declarative_base()


class Review(Base):
    """Tracks a single PR review session."""
    
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_number = Column(Integer, nullable=False, index=True)
    repo = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False)  # "fixed", "failed_max_iterations", "cannot_fix", "pending"
    iterations = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    fix_pr_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    iteration_records = relationship("IterationRecord", back_populates="review", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'pr_number': self.pr_number,
            'repo': self.repo,
            'status': self.status,
            'iterations': self.iterations,
            'tokens_used': self.tokens_used,
            'cost_usd': self.cost_usd,
            'fix_pr_url': self.fix_pr_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class IterationRecord(Base):
    """Tracks a single fix attempt within a review."""
    
    __tablename__ = "iterations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    iteration_num = Column(Integer, nullable=False)
    patch = Column(Text, nullable=True)  # The unified diff patch
    test_output = Column(Text, nullable=True)  # pytest output
    tests_passed = Column(Boolean, nullable=False, default=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    review = relationship("Review", back_populates="iteration_records")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'review_id': self.review_id,
            'iteration_num': self.iteration_num,
            'patch': self.patch,
            'test_output': self.test_output[:500] if self.test_output else None,  # Truncate for API
            'tests_passed': self.tests_passed,
            'tokens_used': self.tokens_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


async def get_database_url() -> str:
    """Get database URL from environment or default."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Default to SQLite for development
        return "sqlite+aiosqlite:///./code_review.db"
    
    # Convert postgres URL to asyncpg
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    return db_url


async def init_database():
    """Initialize database (create tables)."""
    db_url = await get_database_url()
    engine = create_async_engine(db_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()


async def get_session() -> AsyncSession:
    """Get an async database session."""
    db_url = await get_database_url()
    engine = create_async_engine(db_url, echo=False)
    
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    return async_session()
