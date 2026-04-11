"""
Tests for database models and operations.
"""

import unittest
from datetime import datetime
from src.db.models import Review, IterationRecord, Base


class TestDatabaseModels(unittest.TestCase):
    """Test SQLAlchemy ORM models."""
    
    def test_review_model_fields(self):
        """Test Review model has all required fields."""
        review = Review(
            pr_number=123,
            repo="owner/repo",
            status="pending",
            iterations=0,
            tokens_used=0,
            cost_usd=0.0,
        )
        
        assert review.pr_number == 123
        assert review.repo == "owner/repo"
        assert review.status == "pending"
        assert review.iterations == 0
        
        print("✓ Review model fields work")
    
    def test_review_to_dict(self):
        """Test Review serialization."""
        review = Review(
            id=1,
            pr_number=123,
            repo="owner/repo",
            status="fixed",
            iterations=2,
            tokens_used=1000,
            cost_usd=0.15,
            fix_pr_url="https://github.com/owner/repo/pull/456",
        )
        
        d = review.to_dict()
        
        assert d['id'] == 1
        assert d['pr_number'] == 123
        assert d['status'] == "fixed"
        assert d['cost_usd'] == 0.15
        
        print("✓ Review serialization works")
    
    def test_iteration_record_model(self):
        """Test IterationRecord model."""
        record = IterationRecord(
            review_id=1,
            iteration_num=0,
            patch="--- a/file.py\n+++ b/file.py",
            test_output="PASSED",
            tests_passed=True,
            tokens_used=500,
        )
        
        assert record.review_id == 1
        assert record.iteration_num == 0
        assert record.tests_passed is True
        
        print("✓ IterationRecord model works")
    
    def test_iteration_to_dict(self):
        """Test IterationRecord serialization."""
        record = IterationRecord(
            id=1,
            review_id=1,
            iteration_num=0,
            patch="patch content",
            test_output="test output",
            tests_passed=True,
            tokens_used=500,
        )
        
        d = record.to_dict()
        
        assert d['id'] == 1
        assert d['review_id'] == 1
        assert d['tests_passed'] is True
        assert d['tokens_used'] == 500
        
        print("✓ IterationRecord serialization works")
    
    def test_review_iteration_relationship(self):
        """Test relationship between Review and IterationRecord."""
        review = Review(
            pr_number=123,
            repo="owner/repo",
            status="pending",
        )
        
        record1 = IterationRecord(
            iteration_num=0,
            tests_passed=False,
        )
        record2 = IterationRecord(
            iteration_num=1,
            tests_passed=True,
        )
        
        review.iteration_records = [record1, record2]
        
        assert len(review.iteration_records) == 2
        assert review.iteration_records[0].iteration_num == 0
        assert review.iteration_records[1].iteration_num == 1
        
        print("✓ Review-IterationRecord relationship works")
    
    def test_status_enum_values(self):
        """Test that various status values are valid."""
        statuses = ["fixed", "failed_max_iterations", "cannot_fix", "pending", "failed_pr_creation"]
        
        for status in statuses:
            review = Review(
                pr_number=1,
                repo="test/repo",
                status=status,
            )
            assert review.status == status
        
        print("✓ All status values accepted")
    
    def test_datetime_fields(self):
        """Test that datetime fields work correctly."""
        now = datetime.utcnow()
        
        review = Review(
            pr_number=1,
            repo="test/repo",
            status="pending",
            created_at=now,
            completed_at=now,
        )
        
        assert review.created_at == now
        assert review.completed_at == now
        
        print("✓ Datetime fields work")


if __name__ == "__main__":
    unittest.main(verbosity=2)
