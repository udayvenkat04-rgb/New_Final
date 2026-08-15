"""
Match Review Repository — Phase 19

Manages MongoDB persistence for match_reviews and match_review_audits collections.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pymongo import DESCENDING

from backend.database import get_database
from backend.models.match_review import MatchReview, MatchReviewAudit


class MatchReviewRepository:
    """Repository handling database operations for MatchReview and MatchReviewAudit."""

    def __init__(self):
        self.db = get_database()
        self.collection = self.db.match_reviews
        self.audit_collection = self.db.match_review_audits

    def create_review(self, review: MatchReview) -> MatchReview:
        """Creates a new MatchReview document with auto-incrementing integer ID."""
        if review.id is None:
            max_doc = self.collection.find_one(sort=[("id", -1)])
            next_id = (max_doc.get("id") + 1) if (max_doc and isinstance(max_doc.get("id"), int)) else 1
            review.id = next_id

        self.collection.insert_one(review.to_dict())
        return review

    def get_review_by_id(self, review_id: int) -> Optional[MatchReview]:
        """Retrieves a MatchReview by ID."""
        data = self.collection.find_one({"id": review_id})
        return MatchReview.from_dict(data) if data else None

    def get_pending_reviews(self) -> List[MatchReview]:
        """Returns all reviews with status PENDING_REVIEW."""
        return self.get_all_reviews({"review_status": {"$in": ["PENDING_REVIEW", "Pending Review"]}})

    def get_all_reviews(self, filter_query: Optional[dict] = None) -> List[MatchReview]:
        """Returns all match reviews matching filter_query, sorted by created_at descending."""
        if filter_query is None:
            filter_query = {}
        docs = self.collection.find(filter_query).sort("created_at", DESCENDING)
        return [MatchReview.from_dict(doc) for doc in docs if doc]

    def get_reviews_by_case(self, case_id: Union[str, int]) -> List[MatchReview]:
        """Returns all match reviews for a given case_id."""
        query = {"$or": [{"case_id": case_id}, {"case_id": str(case_id)}]}
        try:
            query["$or"].append({"case_id": int(case_id)})
        except Exception:
            pass

        docs = self.collection.find(query).sort("created_at", DESCENDING)
        return [MatchReview.from_dict(doc) for doc in docs if doc]

    def update_review_decision(
        self,
        review_id: int,
        review_status: str,
        review_decision: str,
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> bool:
        """Updates the status, decision, reviewer, timestamp, and notes of a match review."""
        now = datetime.utcnow()
        update_data = {
            "review_status": review_status,
            "status": review_status,  # backwards-comp
            "review_decision": review_decision,
            "reviewed_by": reviewed_by,
            "reviewed_at": now,
            "updated_at": now,
        }
        if review_notes is not None:
            update_data["review_notes"] = review_notes

        res = self.collection.update_one({"id": review_id}, {"$set": update_data})
        return res.modified_count > 0

    def count_reviews_by_status(self) -> Dict[str, int]:
        """Returns count dictionary of review statuses."""
        pipeline = [
            {"$group": {"_id": "$review_status", "count": {"$sum": 1}}}
        ]
        results = list(self.collection.aggregate(pipeline))
        counts = {
            "PENDING_REVIEW": 0,
            "CONFIRMED": 0,
            "REJECTED": 0,
            "NEEDS_FURTHER_REVIEW": 0,
        }
        for r in results:
            k = r.get("_id")
            if k:
                # Map legacy values if present
                if k in ("Pending Review", "PENDING_REVIEW"):
                    counts["PENDING_REVIEW"] += r["count"]
                elif k in ("Confirmed Match", "CONFIRMED"):
                    counts["CONFIRMED"] += r["count"]
                elif k in ("False Positive", "REJECTED"):
                    counts["REJECTED"] += r["count"]
                elif k in ("NEEDS_FURTHER_REVIEW", "Needs Further Review"):
                    counts["NEEDS_FURTHER_REVIEW"] += r["count"]
                else:
                    counts[k] = r["count"]
        return counts

    def create_audit_record(self, audit: MatchReviewAudit) -> MatchReviewAudit:
        """Inserts an immutable audit log entry into db.match_review_audits."""
        if audit.id is None:
            max_doc = self.audit_collection.find_one(sort=[("id", -1)])
            next_id = (max_doc.get("id") + 1) if (max_doc and isinstance(max_doc.get("id"), int)) else 1
            audit.id = next_id

        self.audit_collection.insert_one(audit.to_dict())
        return audit

    def get_review_history(self, review_id: int) -> List[MatchReviewAudit]:
        """Returns full audit history for a given match_review_id."""
        docs = self.audit_collection.find({"match_review_id": review_id}).sort("timestamp", DESCENDING)
        return [MatchReviewAudit.from_dict(doc) for doc in docs if doc]

    def delete_by_case(self, case_id: Union[str, int]) -> bool:
        """Deletes reviews associated with a case ID."""
        query = {"$or": [{"case_id": case_id}, {"case_id": str(case_id)}]}
        res = self.collection.delete_many(query)
        return res.deleted_count > 0
