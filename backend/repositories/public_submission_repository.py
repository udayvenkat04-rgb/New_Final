"""
Public Submission Repository for Missing Person Identification System (Phase 22).

Handles MongoDB persistence for db.public_submissions and db.public_submission_audits collections.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_database
from backend.models.public_submission import PublicSubmission, PublicSubmissionAudit

logger = logging.getLogger(__name__)


class PublicSubmissionRepository:
    def __init__(self, db=None):
        self.db = db if db is not None else get_database()
        self.collection = self.db.public_submissions
        self.audit_collection = self.db.public_submission_audits
        self.ensure_indexes()

    def ensure_indexes(self):
        """Ensures unique submission_reference index and status/created_at indexes."""
        try:
            self.collection.create_index("submission_reference", unique=True)
            self.collection.create_index("status")
            self.collection.create_index("created_at")
            self.audit_collection.create_index("submission_id")
        except Exception as e:
            logger.warning("Failed to create public_submissions indexes: %s", e)

    def _get_next_id(self) -> int:
        try:
            last = self.collection.find_one(sort=[("id", -1)])
            if last and "id" in last and isinstance(last["id"], int):
                return last["id"] + 1
        except Exception:
            pass
        return 1

    def _get_next_audit_id(self) -> int:
        try:
            last = self.audit_collection.find_one(sort=[("id", -1)])
            if last and "id" in last and isinstance(last["id"], int):
                return last["id"] + 1
        except Exception:
            pass
        return 1

    def create_submission(self, submission: PublicSubmission) -> PublicSubmission:
        """Inserts a new public submission into MongoDB."""
        if submission.id is None:
            submission.id = self._get_next_id()

        now = datetime.utcnow()
        submission.created_at = submission.created_at or now
        submission.updated_at = now

        doc = submission.to_dict()
        doc["_id"] = submission.id

        try:
            self.collection.insert_one(doc)
            return submission
        except Exception as e:
            logger.error("Error creating public submission in MongoDB: %s", e)
            raise e

    def get_submission_by_id(self, submission_id: int) -> Optional[PublicSubmission]:
        """Retrieves submission by integer ID."""
        try:
            doc = self.collection.find_one({"$or": [{"id": submission_id}, {"_id": submission_id}]})
            return PublicSubmission.from_dict(doc) if doc else None
        except Exception as e:
            logger.error("Error fetching submission ID %s: %s", submission_id, e)
            return None

    def get_submission_by_reference(self, reference: str) -> Optional[PublicSubmission]:
        """Retrieves submission by public submission reference."""
        if not reference or not isinstance(reference, str):
            return None
        try:
            doc = self.collection.find_one({"submission_reference": reference.strip()})
            return PublicSubmission.from_dict(doc) if doc else None
        except Exception as e:
            logger.error("Error fetching submission reference %s: %s", reference, e)
            return None

    def get_pending_submissions(self) -> List[PublicSubmission]:
        """Retrieves all public submissions in PENDING_VERIFICATION or UNDER_REVIEW status."""
        return self.get_all_submissions(status="PENDING_VERIFICATION")

    def get_all_submissions(self, status: Optional[str] = None) -> List[PublicSubmission]:
        """Retrieves public submissions filtered by status or all if None."""
        query = {}
        if status and status != "All":
            query["status"] = status
        try:
            cursor = self.collection.find(query).sort("created_at", -1)
            return [PublicSubmission.from_dict(doc) for doc in cursor if doc]
        except Exception as e:
            logger.error("Error fetching public submissions list: %s", e)
            return []

    def update_submission_status(
        self,
        submission_id: int,
        status: str,
        reviewed_by: str,
        review_notes: Optional[str] = None,
        approved_case_id: Optional[int] = None,
    ) -> bool:
        """Updates submission status, reviewer metadata, and optional approved_case_id."""
        now = datetime.utcnow()
        update_fields: Dict[str, Any] = {
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": now,
            "updated_at": now,
        }
        if review_notes:
            update_fields["review_notes"] = review_notes
        if approved_case_id:
            update_fields["approved_case_id"] = approved_case_id

        try:
            res = self.collection.update_one(
                {"$or": [{"id": submission_id}, {"_id": submission_id}]},
                {"$set": update_fields},
            )
            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            logger.error("Error updating submission ID %s status to %s: %s", submission_id, status, e)
            return False

    def check_possible_duplicate(
        self,
        full_name: str,
        age: int,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> bool:
        """
        Checks if a submission resembles an existing submission or case by name, age, and city/state.
        Returns True if a probable match is found.
        """
        if not full_name:
            return False

        # Case-insensitive name match
        name_query = {"full_name": {"$regex": f"^{full_name.strip()}$", "$options": "i"}}
        try:
            # Check existing public submissions
            sub_match = self.collection.find_one(name_query)
            if sub_match:
                return True

            # Check official missing_persons collection
            mp_col = self.db.missing_persons
            mp_match = mp_col.find_one({
                "name": {"$regex": f"^{full_name.strip()}$", "$options": "i"},
                "is_deleted": {"$ne": True},
            })
            if mp_match:
                return True
        except Exception as e:
            logger.warning("Error performing duplicate check for %s: %s", full_name, e)

        return False

    def create_audit_record(self, audit: PublicSubmissionAudit) -> PublicSubmissionAudit:
        """Inserts an immutable audit record for public submission reviews."""
        if audit.id is None:
            audit.id = self._get_next_audit_id()

        audit.created_at = audit.created_at or datetime.utcnow()
        doc = audit.to_dict()
        doc["_id"] = audit.id

        try:
            self.audit_collection.insert_one(doc)
            return audit
        except Exception as e:
            logger.error("Error creating public submission audit record: %s", e)
            raise e

    def get_submission_history(self, submission_id: int) -> List[PublicSubmissionAudit]:
        """Retrieves audit trail records for a specific submission."""
        try:
            cursor = self.audit_collection.find({"submission_id": submission_id}).sort("created_at", 1)
            return [PublicSubmissionAudit.from_dict(doc) for doc in cursor if doc]
        except Exception as e:
            logger.error("Error fetching audit trail for submission ID %s: %s", submission_id, e)
            return []
