"""
Phase 14 Test Suite — Face Vector Storage & Retrieval.

Tests:
 1. Store valid 1,404-D vector.
 2. Retrieve vector.
 3. Round-trip validation (original vector vs retrieved vector).
 4. Invalid vector dimensions error handling.
 5. NaN vector error handling.
 6. Infinite vector error handling.
 7. Missing case error handling.
 8. Duplicate vector handling.
 9. Delete vector by case.
10. Retrieve vector for case.
11. MongoDB failure / connection error handling.
12. Repository methods (save, get, list, count, delete).
13. Service orchestration end-to-end.
"""
import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from database import get_database
from models import MissingPerson, FaceVector
from repositories.case_repository import CaseRepository
from repositories.face_repository import FaceRepository
from services.face_storage_service import (
    FaceStorageService,
    FaceStorageError,
    CaseNotFoundError,
    InvalidVectorError,
    DuplicateVectorError,
)


@pytest.fixture
def test_db():
    return get_database()


@pytest.fixture
def case_repo(test_db):
    return CaseRepository(db=test_db)


@pytest.fixture
def face_repo(test_db):
    return FaceRepository(db=test_db)


@pytest.fixture
def storage_service(face_repo, case_repo):
    return FaceStorageService(face_repo=face_repo, case_repo=case_repo)


@pytest.fixture
def sample_case(case_repo, face_repo):
    """Creates a temporary test missing person case."""
    case = case_repo.create(
        MissingPerson(
            name="Storage Test Person",
            age=25,
            gender="Male",
            last_seen_location="Test City",
            contact_number="1234567890",
            description="Test case for face vector storage",
            photo_path="data/faces/placeholder.png",
            status="Missing",
        )
    )
    face_repo.delete_face_vectors_by_case(case.id)
    yield case
    # Cleanup after test
    face_repo.delete_face_vectors_by_case(case.id)
    case_repo.delete(case.id)


@pytest.fixture
def valid_1404_vector():
    """Generates a valid 1,404-D float32 vector with finite values."""
    np.random.seed(123)
    return np.random.uniform(-1.0, 1.0, size=(1404,)).astype(np.float32)


# ---------------------------------------------------------------------------
# Test 1: Store valid 1,404-D vector
# ---------------------------------------------------------------------------
def test_store_valid_1404_vector(storage_service, sample_case, valid_1404_vector):
    saved_doc = storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=False,
    )
    assert saved_doc is not None
    assert saved_doc.id is not None
    assert saved_doc.case_id == sample_case.id
    assert saved_doc.dimensions == 1404
    assert len(saved_doc.vector) == 1404
    assert isinstance(saved_doc.created_at, datetime)


# ---------------------------------------------------------------------------
# Test 2: Retrieve vector
# ---------------------------------------------------------------------------
def test_retrieve_vector(storage_service, sample_case, valid_1404_vector):
    storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=False,
    )
    retrieved = storage_service.get_face_vector_for_case(sample_case.id)
    assert retrieved is not None
    assert isinstance(retrieved, np.ndarray)
    assert retrieved.shape == (1404,)
    assert retrieved.dtype == np.float32


# ---------------------------------------------------------------------------
# Test 3: Round-trip validation
# ---------------------------------------------------------------------------
def test_round_trip_validation(storage_service, sample_case, valid_1404_vector):
    storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=False,
    )
    retrieved = storage_service.get_face_vector_for_case(sample_case.id)
    is_valid = storage_service.validate_round_trip(valid_1404_vector, retrieved)
    assert is_valid is True
    assert np.allclose(valid_1404_vector, retrieved, atol=1e-5)


# ---------------------------------------------------------------------------
# Test 4: Invalid vector dimensions
# ---------------------------------------------------------------------------
def test_invalid_vector_dimensions(storage_service, sample_case):
    invalid_500_vec = np.zeros(500, dtype=np.float32)
    with pytest.raises(InvalidVectorError, match="Shape mismatch"):
        storage_service.store_face_vector(
            case_id=sample_case.id,
            vector=invalid_500_vec,
        )


# ---------------------------------------------------------------------------
# Test 5: NaN vector
# ---------------------------------------------------------------------------
def test_nan_vector(storage_service, sample_case, valid_1404_vector):
    nan_vector = valid_1404_vector.copy()
    nan_vector[10] = np.nan
    with pytest.raises(InvalidVectorError, match="contains NaN"):
        storage_service.store_face_vector(
            case_id=sample_case.id,
            vector=nan_vector,
        )


# ---------------------------------------------------------------------------
# Test 6: Infinite vector
# ---------------------------------------------------------------------------
def test_infinite_vector(storage_service, sample_case, valid_1404_vector):
    inf_vector = valid_1404_vector.copy()
    inf_vector[42] = np.inf
    with pytest.raises(InvalidVectorError, match="contains Inf"):
        storage_service.store_face_vector(
            case_id=sample_case.id,
            vector=inf_vector,
        )


# ---------------------------------------------------------------------------
# Test 7: Missing case
# ---------------------------------------------------------------------------
def test_missing_case(storage_service, valid_1404_vector):
    non_existent_case_id = 99999999
    with pytest.raises(CaseNotFoundError, match="does not exist"):
        storage_service.store_face_vector(
            case_id=non_existent_case_id,
            vector=valid_1404_vector,
        )


# ---------------------------------------------------------------------------
# Test 8: Duplicate vector handling
# ---------------------------------------------------------------------------
def test_duplicate_vector_handling(storage_service, sample_case, valid_1404_vector):
    # First storage
    doc1 = storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=True,
    )
    # Second storage of identical vector
    doc2 = storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=True,
    )
    # Should return existing document without adding duplicate
    assert doc1.id == doc2.id
    count = storage_service.face_repo.count_face_vectors(sample_case.id)
    assert count == 1


# ---------------------------------------------------------------------------
# Test 9: Delete vector
# ---------------------------------------------------------------------------
def test_delete_vector(storage_service, sample_case, valid_1404_vector):
    storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=False,
    )
    assert storage_service.face_repo.count_face_vectors(sample_case.id) == 1
    deleted_count = storage_service.delete_vectors_for_case(sample_case.id)
    assert deleted_count == 1
    assert storage_service.face_repo.count_face_vectors(sample_case.id) == 0


# ---------------------------------------------------------------------------
# Test 10: Retrieve vector for case
# ---------------------------------------------------------------------------
def test_retrieve_vector_for_case(storage_service, sample_case, valid_1404_vector):
    storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=False,
    )
    vectors = storage_service.get_all_vectors_for_case(sample_case.id)
    assert len(vectors) == 1
    assert vectors[0].shape == (1404,)


# ---------------------------------------------------------------------------
# Test 11: MongoDB failure handling
# ---------------------------------------------------------------------------
def test_mongodb_failure_handling(storage_service, sample_case, valid_1404_vector):
    with patch.object(
        storage_service.face_repo,
        "save_face_vector",
        side_effect=ServerSelectionTimeoutError("Connection timed out"),
    ):
        with pytest.raises(FaceStorageError, match="Database insertion failed"):
            storage_service.store_face_vector(
                case_id=sample_case.id,
                vector=valid_1404_vector,
                prevent_duplicates=False,
            )


# ---------------------------------------------------------------------------
# Test 12: Repository methods
# ---------------------------------------------------------------------------
def test_repository_methods(face_repo, sample_case, valid_1404_vector):
    face_repo.delete_face_vectors_by_case(sample_case.id)

    # Create
    fv = FaceVector(case_id=sample_case.id, vector=valid_1404_vector.tolist())
    saved = face_repo.save_face_vector(fv)
    assert saved.id is not None

    # Get by ID
    retrieved_by_id = face_repo.get_by_id(saved.id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.case_id == sample_case.id

    # Get by Case
    retrieved_by_case = face_repo.get_face_vector_by_case(sample_case.id)
    assert retrieved_by_case is not None
    assert retrieved_by_case.id == saved.id

    # List all vectors for case
    all_case_vecs = face_repo.get_face_vectors_by_case(sample_case.id)
    assert len(all_case_vecs) >= 1

    # Count
    cnt = face_repo.count_face_vectors(sample_case.id)
    assert cnt >= 1

    # Find duplicate
    dup = face_repo.find_duplicate(sample_case.id, valid_1404_vector.tolist())
    assert dup is not None
    assert dup.id == saved.id

    # Delete
    del_count = face_repo.delete_face_vectors_by_case(sample_case.id)
    assert del_count >= 1


# ---------------------------------------------------------------------------
# Test 13: Service orchestration
# ---------------------------------------------------------------------------
def test_service_orchestration(storage_service, sample_case, valid_1404_vector):
    # Test end-to-end storing and round-trip verification using fixture vector
    saved_doc = storage_service.store_face_vector(
        case_id=sample_case.id,
        vector=valid_1404_vector,
        prevent_duplicates=True,
    )
    retrieved = storage_service.get_face_vector_for_case(sample_case.id)
    assert storage_service.validate_round_trip(valid_1404_vector, retrieved) is True
