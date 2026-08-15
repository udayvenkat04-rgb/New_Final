from typing import List, Optional
import numpy as np
from backend.database import get_database
from backend.models import FaceVector


class FaceRepository:
    """MongoDB repository layer for face vector documents."""

    def __init__(self, db=None):
        self.db = db if db is not None else get_database()
        self.collection = self.db.face_vectors

    def create(self, face: FaceVector) -> FaceVector:
        """Create and insert a new FaceVector document."""
        if face.id is None:
            max_doc = self.collection.find_one(sort=[("id", -1)])
            next_id = (max_doc.get("id") + 1) if (max_doc and max_doc.get("id") is not None) else 1
            face.id = next_id

        doc = face.to_dict()
        self.collection.insert_one(doc)
        return face

    def save_face_vector(self, face_vector: FaceVector) -> FaceVector:
        """Alias for save/create face vector."""
        return self.create(face_vector)

    def save_vector(self, face_vector: FaceVector) -> FaceVector:
        """Backward-compatible alias for save_face_vector."""
        return self.save_face_vector(face_vector)

    def get_by_id(self, face_id: int) -> Optional[FaceVector]:
        """Retrieve a face vector by its integer id."""
        data = self.collection.find_one({"id": int(face_id)})
        return FaceVector.from_dict(data) if data else None

    def get_face_vector_by_case(self, case_id: int) -> Optional[FaceVector]:
        """Retrieve the primary/most recent face vector for a case."""
        data = self.collection.find_one({"case_id": int(case_id)}, sort=[("id", -1)])
        return FaceVector.from_dict(data) if data else None

    def get_by_case(self, case_id: int) -> List[FaceVector]:
        """Backward-compatible alias for get_face_vectors_by_case."""
        return self.get_face_vectors_by_case(case_id)

    def get_face_vectors_by_case(self, case_id: int) -> List[FaceVector]:
        """Retrieve all face vectors belonging to a missing person case."""
        docs = self.collection.find({"case_id": int(case_id)})
        return [FaceVector.from_dict(doc) for doc in docs]

    def delete_face_vectors_by_case(self, case_id: int) -> int:
        """Delete all face vectors associated with a case. Returns deleted count."""
        res = self.collection.delete_many({"case_id": int(case_id)})
        return res.deleted_count

    def delete_by_case(self, case_id: int) -> bool:
        """Backward-compatible alias for delete_face_vectors_by_case."""
        return self.delete_face_vectors_by_case(case_id) > 0

    def count_face_vectors(self, case_id: Optional[int] = None) -> int:
        """Count total stored face vectors (or count for a specific case_id)."""
        query = {"case_id": int(case_id)} if case_id is not None else {}
        return self.collection.count_documents(query)

    def get_all_face_vectors(self) -> List[FaceVector]:
        """Retrieve all stored face vectors."""
        docs = self.collection.find()
        return [FaceVector.from_dict(doc) for doc in docs]

    def get_all_registered(self) -> List[FaceVector]:
        """Retrieve face vectors that have a non-null case_id."""
        docs = self.collection.find({"case_id": {"$ne": None}})
        return [FaceVector.from_dict(doc) for doc in docs]

    def list_all(self) -> List[FaceVector]:
        """Backward-compatible alias for get_all_face_vectors."""
        return self.get_all_face_vectors()

    def find_duplicate(
        self, case_id: int, vector: List[float], atol: float = 1e-5
    ) -> Optional[FaceVector]:
        """Check if a vector numerically close to ``vector`` already exists for ``case_id``."""
        existing_vectors = self.get_face_vectors_by_case(case_id)
        target_arr = np.asarray(vector, dtype=np.float32)

        for fv in existing_vectors:
            if not fv.vector or len(fv.vector) != len(vector):
                continue
            curr_arr = np.asarray(fv.vector, dtype=np.float32)
            if np.allclose(curr_arr, target_arr, atol=atol):
                return fv
        return None


