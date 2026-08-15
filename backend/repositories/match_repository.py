from backend.database import get_database
from backend.models import MatchResult
from pymongo import DESCENDING

class MatchRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db.match_results

    def create(self, match: MatchResult) -> MatchResult:
        max_doc = self.collection.find_one(sort=[("id", -1)])
        next_id = (max_doc.get("id") + 1) if max_doc else 1
        match.id = next_id
        self.collection.insert_one(match.to_dict())
        return match

    def get_by_id(self, match_id: int) -> MatchResult:
        data = self.collection.find_one({"id": match_id})
        return MatchResult.from_dict(data) if data else None

    def find_match(self, match_id: int) -> MatchResult:
        return self.get_by_id(match_id)

    def list_potential_matches(self) -> list:
        return self.get_all({"status": "Pending Review"})

    def list_by_case(self, case_id: int) -> list:
        return self.get_by_case(case_id)

    def update_status(self, match_id: int, status: str) -> bool:
        res = self.collection.update_one({"id": match_id}, {"$set": {"status": status}})
        return res.modified_count > 0

    def get_by_case(self, case_id: int):
        docs = self.collection.find({"case_id": case_id}).sort("created_at", DESCENDING)
        # Fallback to matched_at sort just in case
        if not docs:
            docs = self.collection.find({"case_id": case_id}).sort("matched_at", DESCENDING)
        return [MatchResult.from_dict(doc) for doc in docs]

    def get_all(self, filter_query: dict = None):
        if filter_query is None:
            filter_query = {}
        docs = self.collection.find(filter_query).sort("created_at", DESCENDING)
        # Fallback to matched_at sort just in case
        if not docs:
            docs = self.collection.find(filter_query).sort("matched_at", DESCENDING)
        return [MatchResult.from_dict(doc) for doc in docs]

    def delete_by_case(self, case_id: int) -> bool:
        res = self.collection.delete_many({"case_id": case_id})
        return res.deleted_count > 0

    def count(self, filter_query: dict = None) -> int:
        if filter_query is None:
            filter_query = {}
        return self.collection.count_documents(filter_query)

    def count_by_status(self) -> dict:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        results = list(self.collection.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results if r["_id"]}

    def get_recent(self, limit: int = 5):
        docs = self.collection.find({}).sort("created_at", DESCENDING).limit(limit)
        return [MatchResult.from_dict(doc) for doc in docs]

    # Phase 19 Compatibility Aliases
    def get_review_by_id(self, review_id: int):
        return self.get_by_id(review_id)

    def get_pending_reviews(self):
        return self.get_all({"status": {"$in": ["Pending Review", "PENDING_REVIEW"]}})

    def get_all_reviews(self, filter_query: dict = None):
        return self.get_all(filter_query)

    def update_review_decision(self, review_id: int, review_status: str, review_decision: str, reviewed_by: str, review_notes: str = None) -> bool:
        return self.update_status(review_id, review_status)

    def count_reviews_by_status(self) -> dict:
        return self.count_by_status()

    def create_audit_record(self, audit):
        return audit

    def get_review_history(self, review_id: int):
        return []


