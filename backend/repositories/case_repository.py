from datetime import datetime
from backend.database import get_database
from backend.models import MissingPerson, CaseHistory
from pymongo import DESCENDING

class CaseRepository:
    def __init__(self, db=None):
        self.db = db if db is not None else get_database()
        self.collection = self.db.missing_persons
        self.history_collection = self.db.case_history
        # Ensure unique case_number index is present so duplicates are impossible
        # at the database level even if we have a race in Python.
        try:
            self.collection.create_index("case_number", unique=True, sparse=True)
        except Exception:
            # Index already exists or is being built — acceptable
            pass

    def _exclude_deleted(self, query: dict) -> dict:
        """Appends is_deleted != True to a query unless explicitly overridden."""
        if query is None:
            query = {}
        if "is_deleted" not in query:
            query["is_deleted"] = {"$ne": True}
        return query

    def get_next_id(self) -> int:
        """Returns the next unused auto-incrementing `id`."""
        max_doc = self.collection.find_one(sort=[("id", -1)])
        return (max_doc.get("id") + 1) if max_doc and max_doc.get("id") is not None else 1

    def get_next_case_number(self, year: int | None = None) -> str:
        """
        Generates a unique case number in the format MP-YYYY-XXXXX.
        Uniqueness is double-guaranteed:
          1. We find the highest existing suffix for the target year and +1 it
          2. The database has a unique sparse index on case_number so collisions
             raise a DuplicateKeyError we catch+retry at the service layer.
        """
        if year is None:
            year = datetime.utcnow().year
        prefix = f"MP-{year}-"
        # Find the lexicographically largest case_number with this prefix
        top = self.collection.find_one(
            {"case_number": {"$regex": f"^{prefix}\\d{{5}}$"}},
            sort=[("case_number", DESCENDING)],
        )
        if top and top.get("case_number"):
            suffix_str = top["case_number"].split("-")[-1]
            try:
                next_suffix = int(suffix_str) + 1
            except (ValueError, TypeError):
                next_suffix = 1
        else:
            next_suffix = 1
        return f"{prefix}{next_suffix:05d}"

    def create(self, case: MissingPerson) -> MissingPerson:
        if case.id is None:
            case.id = self.get_next_id()
        self.collection.insert_one(case.to_dict())
        return case

    def get_by_id(self, case_id: int, include_deleted: bool = False) -> MissingPerson:
        query = {"id": case_id}
        if not include_deleted:
            query = self._exclude_deleted(query)
        data = self.collection.find_one(query)
        return MissingPerson.from_dict(data) if data else None

    def get_by_case_number(self, case_number: str, include_deleted: bool = False) -> MissingPerson:
        query = {"case_number": case_number}
        if not include_deleted:
            query = self._exclude_deleted(query)
        data = self.collection.find_one(query)
        return MissingPerson.from_dict(data) if data else None

    def case_number_exists(self, case_number: str) -> bool:
        return self.collection.count_documents({"case_number": case_number}) > 0

    def update(self, case: MissingPerson) -> MissingPerson:
        case.updated_at = datetime.utcnow()
        self.collection.replace_one({"id": case.id}, case.to_dict())
        return case

    def update_status(self, case_id: int, status: str) -> bool:
        res = self.collection.update_one(
            {"id": case_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        return res.modified_count > 0

    def soft_delete(self, case_id: int) -> bool:
        """Marks a case as deleted (soft delete) instead of removing it permanently."""
        res = self.collection.update_one(
            {"id": case_id},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )
        return res.modified_count > 0

    def delete(self, case_id: int) -> bool:
        res = self.collection.delete_one({"id": case_id})
        return res.deleted_count > 0

    def list_all(self):
        return self.get_all()

    def get_by_officer(self, officer_username: str) -> list:
        return self.get_all({"created_by": officer_username})

    def filter_by_status(self, status: str) -> list:
        return self.get_all({"status": status})

    def filter_by_location(self, city: str = None, state: str = None) -> list:
        query = {}
        if city:
            query["last_seen_city"] = city
        if state:
            query["last_seen_state"] = state
        return self.get_all(query)

    def get_all(self, filter_query: dict = None, include_deleted: bool = False):
        if filter_query is None:
            filter_query = {}
        if not include_deleted:
            filter_query = self._exclude_deleted(filter_query)
        docs = self.collection.find(filter_query).sort("created_at", DESCENDING)
        return [MissingPerson.from_dict(doc) for doc in docs]

    def search(self, search_term: str, filter_query: dict = None, include_deleted: bool = False) -> list:
        """
        Searches cases by case_number, person name, city, or state.
        Applies the soft-delete filter and any additional filter_query.
        """
        if filter_query is None:
            filter_query = {}
        if not include_deleted:
            filter_query = self._exclude_deleted(filter_query)

        if search_term and search_term.strip():
            term = search_term.strip()
            regex = {"$regex": term, "$options": "i"}
            filter_query["$or"] = [
                {"case_number": regex},
                {"name": regex},
                {"last_seen_city": regex},
                {"last_seen_state": regex},
            ]

        docs = self.collection.find(filter_query).sort("created_at", DESCENDING)
        return [MissingPerson.from_dict(doc) for doc in docs]

    def build_filter_query(
        self,
        status: str = None,
        gender: str = None,
        state: str = None,
        city: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> dict:
        """
        Builds a MongoDB filter dict from the provided filter criteria.
        Does NOT apply is_deleted — caller decides via get_all/search.
        """
        query = {}
        if status:
            query["status"] = status
        if gender:
            query["gender"] = gender
        if state:
            query["last_seen_state"] = state
        if city:
            query["last_seen_city"] = city
        if date_from or date_to:
            date_range = {}
            if date_from:
                date_range["$gte"] = date_from
            if date_to:
                date_range["$lte"] = date_to
            query["last_seen_date"] = date_range
        return query

    def get_unique_states(self) -> list:
        """Returns sorted list of distinct non-empty last_seen_state values."""
        states = self.collection.distinct("last_seen_state", {"last_seen_state": {"$ne": None, "$nin": ["", None]}})
        return sorted([s for s in states if s])

    def get_unique_cities(self, state: str = None) -> list:
        """Returns sorted list of distinct non-empty last_seen_city values, optionally filtered by state."""
        query = {"last_seen_city": {"$ne": None, "$nin": ["", None]}}
        if state:
            query["last_seen_state"] = state
        cities = self.collection.distinct("last_seen_city", query)
        return sorted([c for c in cities if c])

    def log_history(self, history: CaseHistory) -> CaseHistory:
        max_doc = self.history_collection.find_one(sort=[("id", -1)])
        next_id = (max_doc.get("id") + 1) if max_doc and max_doc.get("id") is not None else 1
        history.id = next_id
        self.history_collection.insert_one(history.to_dict())
        return history

    def get_history_by_case(self, case_id: int):
        docs = self.history_collection.find({"case_id": case_id}).sort("created_at", DESCENDING)
        # Sort fallback to timestamp just in case
        if not docs:
            docs = self.history_collection.find({"case_id": case_id}).sort("timestamp", DESCENDING)
        return [CaseHistory.from_dict(doc) for doc in docs]

    def count(self, filter_query: dict = None, include_deleted: bool = False) -> int:
        if filter_query is None:
            filter_query = {}
        if not include_deleted:
            filter_query = self._exclude_deleted(filter_query)
        return self.collection.count_documents(filter_query)

    def count_by_status(self) -> dict:
        pipeline = [
            {"$match": self._exclude_deleted({})},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        results = list(self.collection.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results if r["_id"]}

    def get_recent(self, limit: int = 5):
        query = self._exclude_deleted({})
        docs = self.collection.find(query).sort("created_at", DESCENDING).limit(limit)
        return [MissingPerson.from_dict(doc) for doc in docs]

