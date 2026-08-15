"""
Case Event Repository for Missing Person Identification System (Phase 23).

Handles MongoDB persistence for db.case_events collection to store immutable
case lifecycle audit events and timeline records.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.database import get_database
from backend.models.case_event import CaseEvent

logger = logging.getLogger(__name__)


class CaseEventRepository:
    def __init__(self, db=None):
        self.db = db if db is not None else get_database()
        self.collection = self.db.case_events
        self.ensure_indexes()

    def ensure_indexes(self):
        """Ensures performance indexes on case_id, created_at, and event_type."""
        try:
            self.collection.create_index("case_id")
            self.collection.create_index("created_at")
            self.collection.create_index("event_type")
        except Exception as e:
            logger.warning("Failed to create case_events indexes: %s", e)

    def _get_next_id(self) -> int:
        try:
            last = self.collection.find_one(sort=[("id", -1)])
            if last and "id" in last and isinstance(last["id"], int):
                return last["id"] + 1
        except Exception:
            pass
        return 1

    def create_event(self, event: CaseEvent) -> CaseEvent:
        """Inserts a new CaseEvent into MongoDB."""
        if event.id is None:
            event.id = self._get_next_id()

        event.created_at = event.created_at or datetime.utcnow()
        doc = event.to_dict()
        doc["_id"] = event.id

        try:
            self.collection.insert_one(doc)
            return event
        except Exception as e:
            logger.error("Error creating case event in MongoDB: %s", e)
            raise e

    def get_case_events(self, case_id: int) -> List[CaseEvent]:
        """Retrieves all case events for a specific case_id sorted chronologically."""
        try:
            cursor = self.collection.find({"case_id": case_id}).sort("created_at", 1)
            return [CaseEvent.from_dict(doc) for doc in cursor if doc]
        except Exception as e:
            logger.error("Error fetching events for case_id %s: %s", case_id, e)
            return []

    def get_latest_event(self, case_id: int) -> Optional[CaseEvent]:
        """Retrieves the most recent CaseEvent for a specific case_id."""
        try:
            doc = self.collection.find_one({"case_id": case_id}, sort=[("created_at", -1)])
            return CaseEvent.from_dict(doc) if doc else None
        except Exception as e:
            logger.error("Error fetching latest event for case_id %s: %s", case_id, e)
            return None

    def count_events(self, case_id: Optional[int] = None) -> int:
        """Counts total case events, optionally filtered by case_id."""
        try:
            query = {"case_id": case_id} if case_id is not None else {}
            return self.collection.count_documents(query)
        except Exception as e:
            logger.error("Error counting case events: %s", e)
            return 0
