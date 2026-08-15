"""
Phase 15 Test Suite — KNN Face Matching Engine.

Tests:
 1. Valid query vector.
 2. Invalid query vector.
 3. Wrong vector dimensions error.
 4. NaN vector error.
 5. Infinite vector error.
 6. Empty reference database (NO_REFERENCE_VECTORS).
 7. One reference vector (N=1).
 8. Multiple reference vectors (N > 1).
 9. K greater than dataset size (K > N).
10. Top-K ranking.
11. Distance ordering (ascending).
12. Threshold behavior.
13. No-potential-match behavior (NO_POTENTIAL_MATCH).
14. Self-match behavior.
15. Invalid stored vector handling (skips malformed stored vector).
16. Multiple query faces support.
17. Deterministic result ordering.
"""
import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

from database import get_database
from models import MissingPerson, FaceVector
from repositories.case_repository import CaseRepository
from repositories.face_repository import FaceRepository
from services.face_matching import (
    KNNFaceMatchingEngine,
    FaceMatchingError,
    InvalidQueryVectorError,
    match_face_vector,
    distance_to_similarity_score,
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
def sample_face_repo(test_db):
    return FaceRepository(db=test_db)


@pytest.fixture
def mock_face_repo():
    return MagicMock(spec=FaceRepository)


@pytest.fixture
def valid_query_vector():
    np.random.seed(42)
    return np.random.uniform(-1.0, 1.0, size=(1404,)).astype(np.float32)


# ---------------------------------------------------------------------------
# Test 1: Valid query vector
# ---------------------------------------------------------------------------
def test_valid_query_vector(mock_face_repo, valid_query_vector):
    mock_doc = FaceVector(id=1, case_id=10, vector=valid_query_vector.tolist())
    mock_face_repo.get_all_registered.return_value = [mock_doc]

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=5)

    assert result["status"] == "POTENTIAL_MATCH"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["case_id"] == 10
    assert result["candidates"][0]["distance"] <= 1e-4


# ---------------------------------------------------------------------------
# Test 2: Invalid query vector type
# ---------------------------------------------------------------------------
def test_invalid_query_vector_type(mock_face_repo):
    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    with pytest.raises(InvalidQueryVectorError, match="cannot be None"):
        engine.match_vector(None)


# ---------------------------------------------------------------------------
# Test 3: Wrong vector dimensions
# ---------------------------------------------------------------------------
def test_wrong_vector_dimensions(mock_face_repo):
    wrong_vec = np.zeros(500, dtype=np.float32)
    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    with pytest.raises(InvalidQueryVectorError, match="Shape mismatch"):
        engine.match_vector(wrong_vec)


# ---------------------------------------------------------------------------
# Test 4: NaN vector
# ---------------------------------------------------------------------------
def test_nan_query_vector(mock_face_repo, valid_query_vector):
    nan_vec = valid_query_vector.copy()
    nan_vec[5] = np.nan
    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    with pytest.raises(InvalidQueryVectorError, match="contains NaN"):
        engine.match_vector(nan_vec)


# ---------------------------------------------------------------------------
# Test 5: Infinite vector
# ---------------------------------------------------------------------------
def test_infinite_query_vector(mock_face_repo, valid_query_vector):
    inf_vec = valid_query_vector.copy()
    inf_vec[12] = np.inf
    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    with pytest.raises(InvalidQueryVectorError, match="contains Inf"):
        engine.match_vector(inf_vec)


# ---------------------------------------------------------------------------
# Test 6: Empty reference database
# ---------------------------------------------------------------------------
def test_empty_reference_database(mock_face_repo, valid_query_vector):
    mock_face_repo.get_all_registered.return_value = []
    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)

    result = engine.match_vector(valid_query_vector)
    assert result["status"] == "NO_REFERENCE_VECTORS"
    assert result["candidates"] == []
    assert result["num_reference_vectors"] == 0


# ---------------------------------------------------------------------------
# Test 7: One reference vector (N=1)
# ---------------------------------------------------------------------------
def test_one_reference_vector(mock_face_repo, valid_query_vector):
    mock_doc = FaceVector(id=1, case_id=101, vector=valid_query_vector.tolist())
    mock_face_repo.get_all_registered.return_value = [mock_doc]

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=5)

    assert result["status"] == "POTENTIAL_MATCH"
    assert result["k_requested"] == 5
    assert result["k_used"] == 1
    assert len(result["candidates"]) == 1


# ---------------------------------------------------------------------------
# Test 8: Multiple reference vectors
# ---------------------------------------------------------------------------
def test_multiple_reference_vectors(mock_face_repo, valid_query_vector):
    docs = [
        FaceVector(id=i, case_id=100 + i, vector=(valid_query_vector + i * 0.1).tolist())
        for i in range(1, 4)
    ]
    mock_face_repo.get_all_registered.return_value = docs

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=3)

    assert len(result["candidates"]) == 3
    assert result["candidates"][0]["rank"] == 1
    assert result["candidates"][1]["rank"] == 2
    assert result["candidates"][2]["rank"] == 3


# ---------------------------------------------------------------------------
# Test 9: K greater than dataset size (K > N)
# ---------------------------------------------------------------------------
def test_k_greater_than_dataset_size(mock_face_repo, valid_query_vector):
    docs = [
        FaceVector(id=1, case_id=1, vector=valid_query_vector.tolist()),
        FaceVector(id=2, case_id=2, vector=(valid_query_vector + 0.1).tolist()),
    ]
    mock_face_repo.get_all_registered.return_value = docs

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=10)

    assert result["k_requested"] == 10
    assert result["k_used"] == 2
    assert len(result["candidates"]) == 2


# ---------------------------------------------------------------------------
# Test 10: Top-K ranking
# ---------------------------------------------------------------------------
def test_top_k_ranking(mock_face_repo, valid_query_vector):
    docs = [
        FaceVector(id=i, case_id=i, vector=(valid_query_vector + i * 0.05).tolist())
        for i in range(1, 10)
    ]
    mock_face_repo.get_all_registered.return_value = docs

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=3)

    assert len(result["candidates"]) == 3
    assert [c["rank"] for c in result["candidates"]] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Test 11: Distance ordering (ascending)
# ---------------------------------------------------------------------------
def test_distance_ordering_ascending(mock_face_repo, valid_query_vector):
    docs = [
        FaceVector(id=1, case_id=10, vector=(valid_query_vector + 0.5).tolist()),
        FaceVector(id=2, case_id=20, vector=valid_query_vector.tolist()),
        FaceVector(id=3, case_id=30, vector=(valid_query_vector + 0.2).tolist()),
    ]
    mock_face_repo.get_all_registered.return_value = docs

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=3)

    distances = [c["distance"] for c in result["candidates"]]
    assert distances == sorted(distances)
    assert result["candidates"][0]["case_id"] == 20  # Distance 0.0 should be rank 1


# ---------------------------------------------------------------------------
# Test 12: Threshold behavior
# ---------------------------------------------------------------------------
def test_threshold_behavior(mock_face_repo, valid_query_vector):
    # Vector 1 distance ~0.0 (below 0.50 threshold)
    # Vector 2 distance >1.0 (above 0.50 threshold)
    doc1 = FaceVector(id=1, case_id=1, vector=valid_query_vector.tolist())
    doc2 = FaceVector(id=2, case_id=2, vector=(valid_query_vector + 2.0).tolist())
    mock_face_repo.get_all_registered.return_value = [doc1, doc2]

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, top_k=2, threshold=0.50)

    assert result["status"] == "POTENTIAL_MATCH"
    assert result["candidates"][0]["is_potential_match"] is True
    assert result["candidates"][1]["is_potential_match"] is False


# ---------------------------------------------------------------------------
# Test 13: No-potential-match behavior
# ---------------------------------------------------------------------------
def test_no_potential_match_behavior(mock_face_repo, valid_query_vector):
    # All stored vectors are far away
    doc = FaceVector(id=1, case_id=99, vector=(valid_query_vector + 5.0).tolist())
    mock_face_repo.get_all_registered.return_value = [doc]

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector, threshold=0.10)

    assert result["status"] == "NO_POTENTIAL_MATCH"
    assert result["candidates"][0]["is_potential_match"] is False
    assert result["candidates"][0]["match_decision"] == "NO_POTENTIAL_MATCH"


# ---------------------------------------------------------------------------
# Test 14: Self-match behavior
# ---------------------------------------------------------------------------
def test_self_match_behavior(sample_face_repo, case_repo, valid_query_vector):
    # Create real case & vector in test DB
    case = case_repo.create(
        MissingPerson(
            name="Self Match Unit Person",
            age=30,
            gender="Male",
            last_seen_location="City X",
            contact_number="1111111111",
            description="Self match test",
            photo_path="data/faces/placeholder.png",
        )
    )
    fv = sample_face_repo.save_face_vector(
        FaceVector(case_id=case.id, vector=valid_query_vector.tolist())
    )

    try:
        engine = KNNFaceMatchingEngine(face_repo=sample_face_repo)
        res = engine.match_vector(valid_query_vector, top_k=1, threshold=0.60)

        assert res["status"] == "POTENTIAL_MATCH"
        assert res["candidates"][0]["case_id"] == case.id
        assert res["candidates"][0]["distance"] <= 1e-4
    finally:
        sample_face_repo.delete_face_vectors_by_case(case.id)
        case_repo.delete(case.id)


# ---------------------------------------------------------------------------
# Test 15: Invalid stored vector handling
# ---------------------------------------------------------------------------
def test_invalid_stored_vector_handling(mock_face_repo, valid_query_vector):
    valid_doc = FaceVector(id=1, case_id=1, vector=valid_query_vector.tolist())
    invalid_doc_nan = FaceVector(id=2, case_id=2, vector=[np.nan] * 1404)
    invalid_doc_short = FaceVector(id=3, case_id=3, vector=[1.0] * 500)
    invalid_doc_empty = FaceVector(id=4, case_id=4, vector=[])

    mock_face_repo.get_all_registered.return_value = [
        valid_doc,
        invalid_doc_nan,
        invalid_doc_short,
        invalid_doc_empty,
    ]

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    result = engine.match_vector(valid_query_vector)

    # Should safely skip the 3 invalid stored records and match only valid_doc
    assert result["num_reference_vectors"] == 1
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["case_id"] == 1


# ---------------------------------------------------------------------------
# Test 16: Multiple query faces support
# ---------------------------------------------------------------------------
def test_multiple_query_faces(mock_face_repo, valid_query_vector):
    from services.face_detection import FaceDetectionResult, DetectedFace

    mock_doc = FaceVector(id=1, case_id=5, vector=valid_query_vector.tolist())
    mock_face_repo.get_all_registered.return_value = [mock_doc]

    # Mock detection result with 2 faces
    mock_face0 = MagicMock(spec=DetectedFace)
    mock_face1 = MagicMock(spec=DetectedFace)

    det_result = FaceDetectionResult(
        success=True,
        num_faces=2,
        faces=[mock_face0, mock_face1],
    )

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)

    with patch("services.face_matching.detect_faces", return_value=det_result):
        with patch("services.face_matching.generate_face_vector_by_index", return_value=valid_query_vector) as mock_gen:
            res = engine.match_image("dummy_path.png", query_face_index=1)
            mock_gen.assert_called_once_with(det_result, face_index=1, expected_landmarks=468)
            assert res["query_face_index"] == 1
            assert res["num_query_faces_detected"] == 2


# ---------------------------------------------------------------------------
# Test 17: Deterministic result ordering
# ---------------------------------------------------------------------------
def test_deterministic_result_ordering(mock_face_repo, valid_query_vector):
    docs = [
        FaceVector(id=1, case_id=1, vector=(valid_query_vector + 0.1).tolist()),
        FaceVector(id=2, case_id=2, vector=(valid_query_vector + 0.2).tolist()),
        FaceVector(id=3, case_id=3, vector=(valid_query_vector + 0.3).tolist()),
    ]
    mock_face_repo.get_all_registered.return_value = docs

    engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
    res1 = engine.match_vector(valid_query_vector)
    res2 = engine.match_vector(valid_query_vector)

    assert res1["candidates"] == res2["candidates"]
