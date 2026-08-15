"""
Map Repository for Missing Person Identification System (Phase 21).

Provides optimized MongoDB queries and aggregation pipelines for geographic case mapping,
state-level density statistics, city-level markers, and status breakdowns.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.database import get_database, check_connection

logger = logging.getLogger(__name__)


class MapRepository:
    def __init__(self, db=None):
        if db is not None:
            self.db = db
        else:
            self.db = get_database()
        self.collection = self.db.missing_persons
        self.ensure_indexes()

    def ensure_indexes(self):
        """Creates indexes for geographic and status queries."""
        try:
            self.collection.create_index("last_seen_state")
            self.collection.create_index("last_seen_city")
            self.collection.create_index("status")
            self.collection.create_index("created_at")
            self.collection.create_index([("last_seen_state", 1), ("last_seen_city", 1)])
        except Exception as e:
            logger.warning("Failed to create map indexes on MongoDB: %s", e)

    def _build_match_query(
        self,
        status: Optional[str] = None,
        days: Optional[int] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds MongoDB filter criteria."""
        query: Dict[str, Any] = {"is_deleted": {"$ne": True}}

        if status and status != "All":
            if status.lower() == "active":
                query["status"] = "Missing"
            elif status.lower() == "resolved":
                query["status"] = "Found"
            else:
                query["status"] = status

        if state and state != "All India" and state != "All":
            query["last_seen_state"] = state

        if days and isinstance(days, int) and days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query["created_at"] = {"$gte": cutoff}

        return query

    def get_case_locations(
        self,
        status: Optional[str] = None,
        days: Optional[int] = None,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves cases containing geographic metadata matching filter criteria."""
        query = self._build_match_query(status=status, days=days, state=state)
        projection = {
            "_id": 1,
            "id": 1,
            "case_number": 1,
            "name": 1,
            "last_seen_city": 1,
            "last_seen_state": 1,
            "last_seen_location": 1,
            "latitude": 1,
            "longitude": 1,
            "status": 1,
            "created_at": 1,
            "last_seen_date": 1,
        }
        try:
            cursor = self.collection.find(query, projection)
            cases = list(cursor)
            for c in cases:
                if "_id" in c and "id" not in c:
                    c["id"] = c["_id"]
            return cases
        except Exception as e:
            logger.error("Error retrieving case locations from MongoDB: %s", e)
            return []

    def get_case_counts_by_state(
        self,
        status: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates case counts grouped by state.
        Returns list of dicts: {"state": str, "total_cases": int, "active_cases": int, "resolved_cases": int}
        """
        query = self._build_match_query(status=status, days=days)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": {"$ifNull": ["$last_seen_state", "Unknown State"]},
                    "total_cases": {"$sum": 1},
                    "active_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Missing"]}, 1, 0]}
                    },
                    "resolved_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Found"]}, 1, 0]}
                    },
                }
            },
            {"$sort": {"total_cases": -1}},
        ]
        try:
            results = list(self.collection.aggregate(pipeline))
            return [
                {
                    "state": r["_id"],
                    "total_cases": r["total_cases"],
                    "active_cases": r["active_cases"],
                    "resolved_cases": r["resolved_cases"],
                }
                for r in results
            ]
        except Exception as e:
            logger.error("Error aggregating case counts by state: %s", e)
            return []

    def get_case_counts_by_city(
        self,
        status: Optional[str] = None,
        days: Optional[int] = None,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates case counts grouped by city and state.
        Returns list of dicts: {"city": str, "state": str, "total_cases": int, "active_cases": int, "resolved_cases": int, "latitude": float, "longitude": float}
        """
        query = self._build_match_query(status=status, days=days, state=state)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": {
                        "city": {"$ifNull": ["$last_seen_city", "Unknown City"]},
                        "state": {"$ifNull": ["$last_seen_state", "Unknown State"]},
                    },
                    "total_cases": {"$sum": 1},
                    "active_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Missing"]}, 1, 0]}
                    },
                    "resolved_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Found"]}, 1, 0]}
                    },
                    "latitude": {"$first": "$latitude"},
                    "longitude": {"$first": "$longitude"},
                }
            },
            {"$sort": {"total_cases": -1}},
        ]
        try:
            results = list(self.collection.aggregate(pipeline))
            return [
                {
                    "city": r["_id"]["city"],
                    "state": r["_id"]["state"],
                    "total_cases": r["total_cases"],
                    "active_cases": r["active_cases"],
                    "resolved_cases": r["resolved_cases"],
                    "latitude": r.get("latitude"),
                    "longitude": r.get("longitude"),
                }
                for r in results
            ]
        except Exception as e:
            logger.error("Error aggregating case counts by city: %s", e)
            return []

    def get_case_counts_by_status(
        self,
        days: Optional[int] = None,
        state: Optional[str] = None,
    ) -> Dict[str, int]:
        """Computes summary metrics for total, active (Missing), resolved (Found), and closed cases."""
        query = self._build_match_query(days=days, state=state)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_cases": {"$sum": 1},
                    "active_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Missing"]}, 1, 0]}
                    },
                    "resolved_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Found"]}, 1, 0]}
                    },
                    "closed_cases": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Closed"]}, 1, 0]}
                    },
                }
            },
        ]
        try:
            results = list(self.collection.aggregate(pipeline))
            if results:
                res = results[0]
                return {
                    "total_cases": res.get("total_cases", 0),
                    "active_cases": res.get("active_cases", 0),
                    "resolved_cases": res.get("resolved_cases", 0),
                    "closed_cases": res.get("closed_cases", 0),
                }
        except Exception as e:
            logger.error("Error computing status counts: %s", e)

        return {"total_cases": 0, "active_cases": 0, "resolved_cases": 0, "closed_cases": 0}
