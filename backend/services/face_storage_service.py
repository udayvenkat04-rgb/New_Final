"""
Face Storage Service — Phase 14.

Orchestrates:
    Missing Person Case
           ↓
    Reference Photograph
           ↓
    MediaPipe Face Detection (Phase 12)
           ↓
    1,404-D Face Vector Generation (Phase 13)
           ↓
    Vector & Case Validation
           ↓
    Duplicate Prevention
           ↓
    Face Repository / MongoDB Storage
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Union

import numpy as np

from backend.models.face_vector import FaceVector
from backend.repositories.case_repository import CaseRepository
from backend.repositories.face_repository import FaceRepository
from backend.services.face_detection import (
    FaceDetectionResult,
    detect_faces,
)
from backend.services.face_embedding import (
    DEFAULT_VECTOR_DIM,
    DEFAULT_VECTOR_DTYPE,
    FaceEmbeddingError,
    NoFacesDetectedError,
    FaceIndexOutOfRangeError,
    generate_face_vector_by_index,
    validate_face_vector,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FaceStorageError(Exception):
    """Base exception for FaceStorageService errors."""


class CaseNotFoundError(FaceStorageError):
    """Raised when the specified case_id does not exist in MongoDB."""


class InvalidVectorError(FaceStorageError):
    """Raised when vector shape, dimensions, or numerical validity fails."""


class DuplicateVectorError(FaceStorageError):
    """Raised when an identical or nearly identical vector already exists for a case."""


# ---------------------------------------------------------------------------
# Service Implementation
# ---------------------------------------------------------------------------

class FaceStorageService:
    """Service layer managing storage, retrieval, and validation of face vectors."""

    def __init__(
        self,
        face_repo: Optional[FaceRepository] = None,
        case_repo: Optional[CaseRepository] = None,
    ):
        self.face_repo = face_repo or FaceRepository()
        self.case_repo = case_repo or CaseRepository()

    # -----------------------------------------------------------------------
    # Case & Vector Validation
    # -----------------------------------------------------------------------

    def validate_case_exists(self, case_id: int) -> None:
        """Verify that the case_id exists in the database and is active."""
        if case_id is None:
            raise CaseNotFoundError("case_id cannot be None.")

        try:
            case = self.case_repo.get_by_id(int(case_id))
        except Exception as exc:
            logger.error("Database error while looking up case_id=%s: %s", case_id, exc)
            raise FaceStorageError(f"Database error checking case {case_id}: {exc}") from exc

        if case is None or getattr(case, "is_deleted", False):
            raise CaseNotFoundError(f"Missing-person case with ID '{case_id}' does not exist.")

    def validate_vector_values(
        self,
        vector: Union[List[float], np.ndarray],
        expected_dim: int = DEFAULT_VECTOR_DIM,
    ) -> np.ndarray:
        """Validate shape (expected_dim,), numeric dtype, and finite values.

        Returns
        -------
        np.ndarray
            Validated 1-D float32 numpy array.

        Raises
        ------
        InvalidVectorError
            If validation fails.
        """
        if vector is None:
            raise InvalidVectorError("Vector cannot be None.")

        arr = np.asarray(vector, dtype=DEFAULT_VECTOR_DTYPE)
        report = validate_face_vector(arr, expected_dim=expected_dim)

        if not report.is_valid:
            error_msg = "; ".join(report.errors)
            raise InvalidVectorError(f"Vector validation failed: {error_msg}")

        return arr

    # -----------------------------------------------------------------------
    # Storage & Processing Operations
    # -----------------------------------------------------------------------

    def store_face_vector(
        self,
        case_id: int,
        vector: Union[List[float], np.ndarray],
        expected_dim: int = DEFAULT_VECTOR_DIM,
        prevent_duplicates: bool = True,
        atol: float = 1e-5,
    ) -> FaceVector:
        """Store a pre-generated face vector into MongoDB.

        1. Validate case_id exists.
        2. Validate vector shape and finite values.
        3. Prevent duplicate vector insertion if enabled.
        4. Save to MongoDB via FaceRepository.
        """
        # 1. Validate case
        self.validate_case_exists(case_id)

        # 2. Validate vector
        arr = self.validate_vector_values(vector, expected_dim=expected_dim)
        vector_list = [float(x) for x in arr.tolist()]

        # 3. Duplicate check
        if prevent_duplicates:
            dup = self.face_repo.find_duplicate(case_id, vector_list, atol=atol)
            if dup is not None:
                logger.info(
                    "Duplicate face vector detected for case_id=%s (vector ID=%s). Skipping insert.",
                    case_id,
                    dup.id,
                )
                return dup

        # 4. Construct and save FaceVector model
        face_doc = FaceVector(
            case_id=case_id,
            vector=vector_list,
            dimensions=len(vector_list),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        try:
            saved = self.face_repo.save_face_vector(face_doc)
            logger.info(
                "Successfully stored %s-D face vector for case_id=%s (ID=%s).",
                saved.dimensions,
                case_id,
                saved.id,
            )
            return saved
        except Exception as exc:
            logger.error("Failed to store face vector for case_id=%s in MongoDB: %s", case_id, exc)
            raise FaceStorageError(f"Database insertion failed: {exc}") from exc

    def process_and_store_image(
        self,
        case_id: int,
        image_input: Union[str, bytes, np.ndarray],
        face_index: int = 0,
        prevent_duplicates: bool = True,
    ) -> Tuple[FaceVector, FaceDetectionResult]:
        """Full pipeline: Case -> Face Detection -> 1,404-D Vector -> Storage.

        Returns
        -------
        Tuple[FaceVector, FaceDetectionResult]
            The saved FaceVector document and Phase 12 detection result.
        """
        # Step 1: Validate case exists
        self.validate_case_exists(case_id)

        # Step 2: MediaPipe Face Detection (Phase 12)
        detection = detect_faces(image_input)
        if not detection.success:
            raise FaceStorageError(
                f"Face detection failed for case_id={case_id}: {detection.error_message}"
            )
        if detection.num_faces == 0:
            raise NoFacesDetectedError(
                f"No face detected in reference photo for case_id={case_id}."
            )

        # Step 3: Vector Generation (Phase 13)
        try:
            vector_np = generate_face_vector_by_index(
                detection, face_index=face_index, expected_landmarks=468
            )
        except (FaceIndexOutOfRangeError, FaceEmbeddingError) as exc:
            raise FaceStorageError(
                f"Vector generation failed for case_id={case_id}: {exc}"
            ) from exc

        # Step 4: Validate and Store (Phase 14)
        saved_doc = self.store_face_vector(
            case_id=case_id,
            vector=vector_np,
            expected_dim=DEFAULT_VECTOR_DIM,
            prevent_duplicates=prevent_duplicates,
        )

        return saved_doc, detection

    # -----------------------------------------------------------------------
    # Retrieval & Reconstruction
    # -----------------------------------------------------------------------

    def reconstruct_vector_as_numpy(
        self,
        face_vector: Union[FaceVector, dict],
        expected_dim: int = DEFAULT_VECTOR_DIM,
    ) -> np.ndarray:
        """Convert stored vector list into (1404,) float32 NumPy array with full validation.

        Returns
        -------
        np.ndarray
            Shape (1404,), dtype float32.
        """
        if isinstance(face_vector, dict):
            raw_list = face_vector.get("vector") or face_vector.get("embedding")
        elif isinstance(face_vector, FaceVector):
            raw_list = face_vector.vector
        else:
            raise InvalidVectorError(
                f"Expected FaceVector instance or dict, got {type(face_vector).__name__}."
            )

        if raw_list is None or len(raw_list) == 0:
            raise InvalidVectorError("Stored vector is empty or None.")

        arr = np.asarray(raw_list, dtype=DEFAULT_VECTOR_DTYPE)
        report = validate_face_vector(arr, expected_dim=expected_dim)

        if not report.is_valid:
            raise InvalidVectorError(
                "Retrieved vector failed validation: " + "; ".join(report.errors)
            )

        return arr

    def get_face_vector_for_case(
        self, case_id: int, expected_dim: int = DEFAULT_VECTOR_DIM
    ) -> Optional[np.ndarray]:
        """Retrieve the primary face vector for a case as a NumPy float32 array.

        Returns
        -------
        Optional[np.ndarray]
            Shape (1404,), dtype float32, or None if no vector exists.
        """
        self.validate_case_exists(case_id)
        face_doc = self.face_repo.get_face_vector_by_case(case_id)
        if not face_doc:
            return None
        return self.reconstruct_vector_as_numpy(face_doc, expected_dim=expected_dim)

    def get_all_vectors_for_case(
        self, case_id: int, expected_dim: int = DEFAULT_VECTOR_DIM
    ) -> List[np.ndarray]:
        """Retrieve all face vectors for a case as NumPy float32 arrays."""
        self.validate_case_exists(case_id)
        docs = self.face_repo.get_face_vectors_by_case(case_id)
        return [self.reconstruct_vector_as_numpy(d, expected_dim=expected_dim) for d in docs]

    def delete_vectors_for_case(self, case_id: int) -> int:
        """Delete all face vectors associated with case_id."""
        self.validate_case_exists(case_id)
        return self.face_repo.delete_face_vectors_by_case(case_id)

    # -----------------------------------------------------------------------
    # Round-trip Validation
    # -----------------------------------------------------------------------

    def validate_round_trip(
        self,
        original_vector: np.ndarray,
        retrieved_vector: np.ndarray,
        atol: float = 1e-5,
    ) -> bool:
        """Verify original and retrieved vectors match in shape, order, and values.

        Returns
        -------
        bool
            True if vectors are numerically equivalent within tolerance.
        """
        if original_vector.shape != retrieved_vector.shape:
            logger.error(
                "Round-trip shape mismatch: original %s vs retrieved %s",
                original_vector.shape,
                retrieved_vector.shape,
            )
            return False

        if original_vector.dtype != retrieved_vector.dtype:
            logger.warning(
                "Round-trip dtype difference: original %s vs retrieved %s",
                original_vector.dtype,
                retrieved_vector.dtype,
            )

        is_close = np.allclose(original_vector, retrieved_vector, atol=atol)
        if not is_close:
            max_diff = float(np.max(np.abs(original_vector - retrieved_vector)))
            logger.error(
                "Round-trip value mismatch! Max diff between vectors = %f", max_diff
            )
            return False

        return True
