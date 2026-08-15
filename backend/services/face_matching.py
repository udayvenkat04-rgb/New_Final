"""
KNN Face Matching Engine — Phase 15.

Purpose
-------
Matches a 1,404-dimensional query face vector against all stored missing-person
reference face vectors in MongoDB using K-Nearest Neighbors (KNN).

Pipeline (Single Query Face)
-----------------------------
    Query Image / Query Vector (1,404-D)
               ↓
    Query Vector Validation (shape, numeric, finite)
               ↓
    Load Reference Vectors via FaceRepository
               ↓
    Stored Vector Validation & Filtering (skip malformed)
               ↓
    KNN Model Building (sklearn.neighbors.NearestNeighbors)
               ↓
    Ranked Candidates & Distance / Similarity Calculation
               ↓
    Thresholding & Decision ("POTENTIAL_MATCH" / "NO_POTENTIAL_MATCH")

Distance Metric Documentation
-----------------------------
We select **Euclidean distance** (L2 norm, ``metric='euclidean'``) as the primary
distance metric for comparing Phase 13 normalized facial landmark vectors.

*Technical Rationale*:
In Phase 13, face landmarks are mean-centered (translation invariant) and
scaled by the maximum XY radius from origin (scale invariant). Because all vectors
reside in a normalized spatial unit sphere, Euclidean distance
    d(u, v) = sqrt( sum( (u_i - v_i)^2 ) )
directly measures the physical spatial displacement of facial landmarks in 3D space
across all 468 points.

Similarity Score Calculation
----------------------------
KNN Euclidean distance `d >= 0` is converted into a 0.0 – 100.0% similarity score
for UI ranking and presentation purposes:
    similarity_score = max(0.0, 1.0 - (distance / 2.0)) * 100.0

*Note*: Similarity percentage is a heuristic ranking metric and is NOT a statistically
calibrated probability of identity. Final identity confirmation requires human review.
"""
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from sklearn.neighbors import NearestNeighbors

from backend.config.settings import FACE_MATCH_THRESHOLD, KNN_N_NEIGHBORS
from backend.models.face_vector import FaceVector
from backend.repositories.face_repository import FaceRepository
from backend.services.face_detection import FaceDetectionResult, detect_faces
from backend.services.face_embedding import (
    DEFAULT_VECTOR_DIM,
    DEFAULT_VECTOR_DTYPE,
    FaceEmbeddingError,
    NoFacesDetectedError,
    generate_face_vector_by_index,
    validate_face_vector,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FaceMatchingError(Exception):
    """Base exception for Face Matching Engine errors."""


class InvalidQueryVectorError(FaceMatchingError):
    """Raised when query vector shape, dimensions, or numerical validity fails."""


# ---------------------------------------------------------------------------
# Helper Pure Functions
# ---------------------------------------------------------------------------

def calculate_similarity(emb1: Sequence[float], emb2: Sequence[float]) -> float:
    """Calculate cosine similarity between two embedding vectors (-1.0 to 1.0)."""
    if not emb1 or not emb2 or len(emb1) != len(emb2):
        return 0.0

    vec1 = np.asarray(emb1, dtype=DEFAULT_VECTOR_DTYPE)
    vec2 = np.asarray(emb2, dtype=DEFAULT_VECTOR_DTYPE)

    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(vec1, vec2) / (norm_a * norm_b))


def distance_to_similarity_score(distance: float) -> float:
    """Convert Euclidean distance to a 0–100% similarity score."""
    if distance is None or np.isnan(distance) or np.isinf(distance):
        return 0.0
    # Euclidean distance on unit-scaled landmarks is bounded approx in [0, 2.0]
    score = max(0.0, 1.0 - (float(distance) / 2.0)) * 100.0
    return round(score, 2)


def validate_query_vector(
    vector: Union[List[float], np.ndarray],
    expected_dim: int = DEFAULT_VECTOR_DIM,
) -> np.ndarray:
    """Validate query vector type, shape, numeric dtype, and finite values.

    Returns
    -------
    np.ndarray
        1-D float32 numpy array of shape (expected_dim,).

    Raises
    ------
    InvalidQueryVectorError
        If validation fails.
    """
    if vector is None:
        raise InvalidQueryVectorError("Query vector cannot be None.")

    try:
        arr = np.asarray(vector, dtype=DEFAULT_VECTOR_DTYPE)
    except Exception as exc:
        raise InvalidQueryVectorError(f"Could not convert query vector to numpy array: {exc}") from exc

    report = validate_face_vector(arr, expected_dim=expected_dim)
    if not report.is_valid:
        error_msg = "; ".join(report.errors)
        raise InvalidQueryVectorError(f"Invalid query vector: {error_msg}")

    return arr


# ---------------------------------------------------------------------------
# KNN Face Matching Engine
# ---------------------------------------------------------------------------

class KNNFaceMatchingEngine:
    """Core KNN face matching service using scikit-learn NearestNeighbors."""

    def __init__(
        self,
        face_repo: Optional[FaceRepository] = None,
        default_k: int = KNN_N_NEIGHBORS,
        default_threshold: float = FACE_MATCH_THRESHOLD,
        metric: str = "euclidean",
    ):
        self.face_repo = face_repo or FaceRepository()
        self.default_k = default_k
        self.default_threshold = default_threshold
        self.metric = metric

    def _load_and_validate_stored_vectors(
        self, expected_dim: int = DEFAULT_VECTOR_DIM
    ) -> Tuple[List[FaceVector], np.ndarray]:
        """Load stored face vectors via FaceRepository and filter out invalid records.

        Returns
        -------
        Tuple[List[FaceVector], np.ndarray]
            Valid FaceVector objects and stacked (N, expected_dim) float32 matrix.
        """
        all_docs = self.face_repo.get_all_registered()
        valid_docs: List[FaceVector] = []
        valid_vectors: List[np.ndarray] = []

        for doc in all_docs:
            if not doc or not doc.vector:
                logger.warning("Skipping empty FaceVector record ID=%s", getattr(doc, "id", None))
                continue

            try:
                arr = np.asarray(doc.vector, dtype=DEFAULT_VECTOR_DTYPE)
                report = validate_face_vector(arr, expected_dim=expected_dim)
                if not report.is_valid:
                    logger.warning(
                        "Skipping invalid stored FaceVector ID=%s (case_id=%s): %s",
                        doc.id,
                        doc.case_id,
                        "; ".join(report.errors),
                    )
                    continue
                valid_docs.append(doc)
                valid_vectors.append(arr)
            except Exception as exc:
                logger.warning("Skipping malformed stored FaceVector ID=%s: %s", doc.id, exc)
                continue

        if not valid_vectors:
            return [], np.empty((0, expected_dim), dtype=DEFAULT_VECTOR_DTYPE)

        matrix = np.vstack(valid_vectors)
        return valid_docs, matrix

    def match_vector(
        self,
        query_vector: Union[List[float], np.ndarray],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        expected_dim: int = DEFAULT_VECTOR_DIM,
    ) -> Dict[str, Any]:
        """Perform KNN face vector matching against all registered database vectors.

        Parameters
        ----------
        query_vector:
            1,404-dimensional query vector.
        top_k:
            Number of nearest neighbors to return (default: self.default_k).
        threshold:
            Maximum Euclidean distance threshold for match decision.

        Returns
        -------
        Dict[str, Any]
            Structured result containing status, candidate list, and metadata.
        """
        k = top_k if top_k is not None else self.default_k
        thresh = threshold if threshold is not None else self.default_threshold

        # 1. Validate query vector
        q_arr = validate_query_vector(query_vector, expected_dim=expected_dim)

        # 2. Load reference vectors from MongoDB via FaceRepository
        valid_docs, matrix = self._load_and_validate_stored_vectors(expected_dim=expected_dim)

        num_ref = len(valid_docs)
        if num_ref == 0:
            return {
                "status": "NO_REFERENCE_VECTORS",
                "candidates": [],
                "best_candidate": None,
                "message": "No reference face vectors stored in database.",
                "num_reference_vectors": 0,
                "k_requested": k,
                "k_used": 0,
                "distance_metric": self.metric,
                "threshold": thresh,
            }

        # 3. Handle small datasets safely: cap K <= N
        effective_k = min(int(k), num_ref)

        # 4. Build KNN model and query
        nn = NearestNeighbors(n_neighbors=effective_k, metric=self.metric)
        nn.fit(matrix)

        distances, indices = nn.kneighbors(q_arr.reshape(1, -1))
        dist_row = distances[0]
        idx_row = indices[0]

        # 5. Format candidates list
        candidates: List[Dict[str, Any]] = []
        has_potential_match = False

        for rank_idx, (dist_val, ref_idx) in enumerate(zip(dist_row, idx_row), start=1):
            dist_float = round(float(dist_val), 6)
            sim_score = distance_to_similarity_score(dist_float)
            ref_doc = valid_docs[ref_idx]

            is_potential = bool(dist_float <= thresh)
            if is_potential:
                has_potential_match = True

            candidate_info = {
                "rank": rank_idx,
                "case_id": ref_doc.case_id,
                "vector_id": ref_doc.id,
                "distance": dist_float,
                "similarity_score": sim_score,
                "is_potential_match": is_potential,
                "match_decision": "POTENTIAL MATCH" if is_potential else "NO_POTENTIAL_MATCH",
                "created_at": ref_doc.created_at.isoformat() if ref_doc.created_at else None,
            }
            candidates.append(candidate_info)

        status_code = "POTENTIAL_MATCH" if has_potential_match else "NO_POTENTIAL_MATCH"
        message = (
            f"Found {sum(1 for c in candidates if c['is_potential_match'])} potential match(es)."
            if has_potential_match
            else "No candidate face vector met the match threshold."
        )

        return {
            "status": status_code,
            "candidates": candidates,
            "best_candidate": candidates[0] if candidates else None,
            "message": message,
            "num_reference_vectors": num_ref,
            "k_requested": k,
            "k_used": effective_k,
            "distance_metric": self.metric,
            "threshold": thresh,
        }

    def match_image(
        self,
        image_input: Union[str, bytes, np.ndarray],
        query_face_index: int = 0,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Full pipeline: Detect face -> Extract 1,404-D vector -> KNN Match."""
        detection = detect_faces(image_input)
        if not detection.success:
            raise FaceMatchingError(
                f"Face detection failed: {detection.error_message}"
            )
        if detection.num_faces == 0:
            raise NoFacesDetectedError("No face detected in query image.")

        q_vec = generate_face_vector_by_index(
            detection, face_index=query_face_index, expected_landmarks=468
        )

        res = self.match_vector(q_vec, top_k=top_k, threshold=threshold)
        res["query_face_index"] = query_face_index
        res["num_query_faces_detected"] = detection.num_faces
        return res


# ---------------------------------------------------------------------------
# Module-level API functions
# ---------------------------------------------------------------------------

def match_face_vector(
    query_vector: Union[List[float], np.ndarray],
    top_k: Optional[int] = KNN_N_NEIGHBORS,
    threshold: Optional[float] = FACE_MATCH_THRESHOLD,
    face_repo: Optional[FaceRepository] = None,
    metric: str = "euclidean",
) -> Dict[str, Any]:
    """Matches a 1,404-D query vector against stored MongoDB reference vectors."""
    engine = KNNFaceMatchingEngine(
        face_repo=face_repo,
        default_k=top_k,
        default_threshold=threshold,
        metric=metric,
    )
    return engine.match_vector(query_vector, top_k=top_k, threshold=threshold)


def match_query_image(
    image_input: Union[str, bytes, np.ndarray],
    query_face_index: int = 0,
    top_k: Optional[int] = KNN_N_NEIGHBORS,
    threshold: Optional[float] = FACE_MATCH_THRESHOLD,
    face_repo: Optional[FaceRepository] = None,
    metric: str = "euclidean",
) -> Dict[str, Any]:
    """Detects face in query image and matches its vector against stored database vectors."""
    engine = KNNFaceMatchingEngine(
        face_repo=face_repo,
        default_k=top_k,
        default_threshold=threshold,
        metric=metric,
    )
    return engine.match_image(
        image_input=image_input,
        query_face_index=query_face_index,
        top_k=top_k,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Backward Compatibility Wrappers
# ---------------------------------------------------------------------------

def match_face_embeddings(
    query_emb: List[float],
    db_records: List[Tuple[Any, List[float]]],
    threshold: float = None,
) -> List[Dict[str, Any]]:
    """Legacy helper for matching query embedding against list of tuples [(item, emb)]."""
    if threshold is None:
        threshold = FACE_MATCH_THRESHOLD

    results = []
    for item, emb in db_records:
        if not emb or len(emb) != len(query_emb):
            continue
        score = calculate_similarity(query_emb, emb)
        confidence = max(0.0, score)
        results.append({
            "record": item,
            "confidence": confidence,
            "match": confidence >= threshold,
        })
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def knn_match(
    query_emb: List[float],
    db_records: List[Tuple[Any, List[float]]],
    k: int = 3,
) -> List[Dict[str, Any]]:
    """Legacy helper for performing KNN matching on tuples [(item, emb)]."""
    if not query_emb or not db_records:
        return []

    vec_q = np.asarray(query_emb, dtype=DEFAULT_VECTOR_DTYPE)
    candidates = []

    for item, emb in db_records:
        if not emb or len(emb) != len(query_emb):
            continue
        vec_e = np.asarray(emb, dtype=DEFAULT_VECTOR_DTYPE)
        distance = float(np.linalg.norm(vec_q - vec_e))
        confidence = 1.0 / (1.0 + distance)
        candidates.append({
            "record": item,
            "distance": distance,
            "confidence": confidence,
        })

    candidates.sort(key=lambda x: x["distance"])
    return candidates[:k]


# Alias for service naming consistency
FaceMatchingService = KNNFaceMatchingEngine

