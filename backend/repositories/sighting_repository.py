from backend.database import get_database
from backend.models import Sighting
from pymongo import DESCENDING

class SightingRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db.sightings

    def create(self, sighting: Sighting) -> Sighting:
        max_doc = self.collection.find_one(sort=[("id", -1)])
        next_id = (max_doc.get("id") + 1) if max_doc else 1
        sighting.id = next_id
        self.collection.insert_one(sighting.to_dict())
        return sighting

    def get_by_id(self, sighting_id: int) -> Sighting:
        data = self.collection.find_one({"id": sighting_id})
        return Sighting.from_dict(data) if data else None

    def find_sightings(self, filter_query: dict = None) -> list:
        return self.get_all(filter_query)

    def get_by_case(self, case_id: int) -> list:
        return self.get_all({"case_id": case_id})

    def update_status(self, sighting_id: int, status: str) -> bool:
        res = self.collection.update_one({"id": sighting_id}, {"$set": {"status": status}})
        return res.modified_count > 0

    def delete(self, sighting_id: int) -> bool:
        res = self.collection.delete_one({"id": sighting_id})
        return res.deleted_count > 0

    def get_all(self, filter_query: dict = None):
        if filter_query is None:
            filter_query = {}
        docs = self.collection.find(filter_query).sort("sighting_time", DESCENDING)
        return [Sighting.from_dict(doc) for doc in docs]

    def link_case(self, sighting_id: int, case_id: int) -> bool:
        res = self.collection.update_one({"id": sighting_id}, {"$set": {"case_id": case_id, "status": "Verified"}})
        return res.modified_count > 0

    def count(self, filter_query: dict = None) -> int:
        if filter_query is None:
            filter_query = {}
        return self.collection.count_documents(filter_query)

    def count_video_sightings(self) -> int:
        return self.collection.count_documents({"video_path": {"$exists": True, "$ne": None, "$nin": ["", None]}})

    def count_by_status(self) -> dict:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        results = list(self.collection.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results if r["_id"]}

    def get_recent(self, limit: int = 5):
        docs = self.collection.find({}).sort("sighting_time", DESCENDING).limit(limit)
        return [Sighting.from_dict(doc) for doc in docs]

