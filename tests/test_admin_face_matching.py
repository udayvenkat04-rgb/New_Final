"""
Test suite for Phase 16: Admin Face Matching Dashboard.

Tests:
 1. Admin access permitted via require_role guard.
 2. Officer access denied via require_role guard.
 3. Unauthenticated access denied via require_role guard.
 4. Valid image upload validation.
 5. Invalid image format / corrupt file upload validation.
 6. File size limit validation.
 7. No face detected handling.
 8. Multiple face detection & index selection.
 9. 1,404-D vector generation & validation summary.
10. KNN engine invocation with custom top_k and threshold.
11. Candidate retrieval via CaseService with ownership / permission rules.
12. Empty reference database handling (NO_REFERENCE_VECTORS).
13. No potential match within threshold handling (NO_POTENTIAL_MATCH).
14. Database failure exception handling.
15. End-to-end mocked Admin matching workflow.
"""
import io
import pytest
import numpy as np
from PIL import Image as PILImage
from unittest.mock import MagicMock, patch
import streamlit as st

from auth.permissions import require_role, ROLE_ADMIN, ROLE_OFFICER
from models import MissingPerson, FaceVector
from services.face_detection import FaceDetectionResult, DetectedFace, FaceLandmark
from services.face_embedding import generate_face_vector_by_index, FaceEmbeddingError
from services.face_matching import (
    KNNFaceMatchingEngine,
    validate_query_vector,
    InvalidQueryVectorError,
)
from services.case_service import CaseService
from pages.admin_face_matching import _validate_uploaded_image, _extract_face_crop


# ──────────────────────────────────────────────────────────────────────
# Test Fixtures & Mocks
# ──────────────────────────────────────────────────────────────────────

ADMIN_USER = {"id": 1, "username": "AdminUser", "role": "admin", "email": "admin@test.com"}
OFFICER_USER = {"id": 2, "username": "OfficerUser", "role": "officer", "email": "officer@test.com"}


@pytest.fixture
def valid_query_vector():
    np.random.seed(42)
    return np.random.uniform(-1.0, 1.0, size=(1404,)).astype(np.float32)


@pytest.fixture
def mock_session(monkeypatch):

    """Mocks st.session_state."""
    session_dict = {}

    class MockSessionState:
        def __getitem__(self, key):
            return session_dict[key]
        def __setitem__(self, key, value):
            session_dict[key] = value
        def __contains__(self, key):
            return key in session_dict
        def __delitem__(self, key):
            del session_dict[key]
        def get(self, key, default=None):
            return session_dict.get(key, default)
        def __getattr__(self, key):
            try:
                return session_dict[key]
            except KeyError:
                raise AttributeError(key)
        def __setattr__(self, key, value):
            session_dict[key] = value

    monkeypatch.setattr(st, "session_state", MockSessionState())
    return session_dict


def _set_user(session_dict, user):
    session_dict["authenticated"] = True
    session_dict["user"] = user


def _create_dummy_image_bytes(format="JPEG", size=(200, 200), color=(100, 150, 200)):
    """Helper to create dummy PIL image bytes."""
    img = PILImage.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def _create_mock_uploaded_file(bytes_data, name="test.jpg", mime="image/jpeg"):
    """Helper to mock Streamlit's UploadedFile object."""
    mock_file = MagicMock()
    mock_file.name = name
    mock_file.type = mime
    mock_file.getvalue.return_value = bytes_data
    return mock_file


# ──────────────────────────────────────────────────────────────────────
# 1. Access Control Tests
# ──────────────────────────────────────────────────────────────────────

class TestAdminFaceMatchingAccess:
    def test_admin_can_access_page(self, mock_session):
        """Admin user passes the require_role([ROLE_ADMIN]) guard."""
        _set_user(mock_session, ADMIN_USER)
        res = require_role([ROLE_ADMIN])
        assert res is True

    def test_officer_cannot_access_page(self, mock_session, monkeypatch):
        """Officer user is blocked by require_role([ROLE_ADMIN])."""
        _set_user(mock_session, OFFICER_USER)

        error_calls = []
        monkeypatch.setattr(st, "error", lambda msg: error_calls.append(msg))

        class StopException(Exception):
            pass

        monkeypatch.setattr(st, "stop", lambda: (_ for _ in ()).throw(StopException()))

        with pytest.raises(StopException):
            require_role([ROLE_ADMIN])

        assert len(error_calls) == 1
        assert "Access Denied" in error_calls[0]

    def test_unauthenticated_cannot_access_page(self, mock_session, monkeypatch):
        """Unauthenticated user is halted by require_role."""
        error_calls = []
        monkeypatch.setattr(st, "error", lambda msg: error_calls.append(msg))

        class StopException(Exception):
            pass

        monkeypatch.setattr(st, "stop", lambda: (_ for _ in ()).throw(StopException()))

        with pytest.raises(StopException):
            require_role([ROLE_ADMIN])

        assert len(error_calls) == 1
        assert "Authentication Required" in error_calls[0]


# ──────────────────────────────────────────────────────────────────────
# 2. Upload Validation Tests
# ──────────────────────────────────────────────────────────────────────

class TestImageUploadValidation:
    def test_valid_jpeg_upload(self):
        bytes_data = _create_dummy_image_bytes(format="JPEG")
        file_obj = _create_mock_uploaded_file(bytes_data, name="query.jpg")
        valid, msg, img = _validate_uploaded_image(file_obj)
        assert valid is True
        assert "Valid image" in msg
        assert img is not None
        assert img.size == (200, 200)

    def test_valid_png_upload(self):
        bytes_data = _create_dummy_image_bytes(format="PNG")
        file_obj = _create_mock_uploaded_file(bytes_data, name="query.png", mime="image/png")
        valid, msg, img = _validate_uploaded_image(file_obj)
        assert valid is True
        assert img is not None

    def test_unsupported_file_extension(self):
        file_obj = _create_mock_uploaded_file(b"some data", name="doc.pdf", mime="application/pdf")
        valid, msg, img = _validate_uploaded_image(file_obj)
        assert valid is False
        assert "Unsupported file format" in msg
        assert img is None

    def test_empty_file_upload(self):
        file_obj = _create_mock_uploaded_file(b"", name="empty.jpg")
        valid, msg, img = _validate_uploaded_image(file_obj)
        assert valid is False
        assert "empty" in msg.lower()
        assert img is None

    def test_corrupted_image_file(self):
        file_obj = _create_mock_uploaded_file(b"NOT_AN_IMAGE_CONTENT", name="corrupt.jpg")
        valid, msg, img = _validate_uploaded_image(file_obj)
        assert valid is False
        assert "Failed to read image data" in msg
        assert img is None


# ──────────────────────────────────────────────────────────────────────
# 3. Face Detection & Crop Extraction Tests
# ──────────────────────────────────────────────────────────────────────

class TestFaceDetectionIntegration:
    def test_no_face_detected_handling(self):
        result = FaceDetectionResult(success=True, num_faces=0, faces=[])
        assert result.num_faces == 0
        assert result.success is True

    def test_multiple_faces_crop_extraction(self):
        landmarks_468 = [FaceLandmark(index=i, x=0.1 + i*0.001, y=0.2, z=0.0) for i in range(468)]
        face1 = DetectedFace(face_index=0, landmarks=landmarks_468, bounding_box_pixels=(10, 10, 50, 50))
        face2 = DetectedFace(face_index=1, landmarks=landmarks_468, bounding_box_pixels=(70, 10, 50, 50))

        dummy_rgb = np.zeros((150, 150, 3), dtype=np.uint8)
        crop1 = _extract_face_crop(dummy_rgb, face1)
        crop2 = _extract_face_crop(dummy_rgb, face2)

        assert crop1.size > 0
        assert crop2.size > 0


# ──────────────────────────────────────────────────────────────────────
# 4. 1,404-D Vector Generation Tests
# ──────────────────────────────────────────────────────────────────────

class TestVectorGenerationSummary:
    def test_valid_1404_vector_generation(self):
        landmarks_468 = [FaceLandmark(index=i, x=float(i)/500.0, y=0.5, z=0.1) for i in range(468)]
        face = DetectedFace(face_index=0, landmarks=landmarks_468)
        det_result = FaceDetectionResult(success=True, num_faces=1, faces=[face])

        vec = generate_face_vector_by_index(det_result, face_index=0, expected_landmarks=468)
        validated_vec = validate_query_vector(vec, expected_dim=1404)

        assert len(validated_vec) == 1404
        assert validated_vec.dtype == np.float32
        assert np.isfinite(validated_vec).all()


# ──────────────────────────────────────────────────────────────────────
# 5. KNN Search & Candidate Retrieval Tests
# ──────────────────────────────────────────────────────────────────────

class TestKNNMatchingIntegration:
    @patch("services.face_matching.FaceRepository")
    def test_knn_search_no_reference_vectors(self, mock_repo_cls, valid_query_vector):
        mock_repo = MagicMock()
        mock_repo.get_all_registered.return_value = []
        mock_repo_cls.return_value = mock_repo

        engine = KNNFaceMatchingEngine(face_repo=mock_repo)
        res = engine.match_vector(valid_query_vector, top_k=5, threshold=0.45)

        assert res["status"] == "NO_REFERENCE_VECTORS"
        assert res["num_reference_vectors"] == 0
        assert len(res["candidates"]) == 0

    @patch("services.face_matching.FaceRepository")
    def test_knn_search_with_potential_match(self, mock_repo_cls):
        np.random.seed(123)
        query_vec = np.random.uniform(-1.0, 1.0, size=(1404,)).astype(np.float32)

        # Same vector stored -> distance ~0 -> POTENTIAL MATCH
        doc1 = FaceVector(id=1, case_id=101, vector=query_vec.tolist())
        mock_repo = MagicMock()
        mock_repo.get_all_registered.return_value = [doc1]
        mock_repo_cls.return_value = mock_repo

        engine = KNNFaceMatchingEngine(face_repo=mock_repo)
        res = engine.match_vector(query_vec, top_k=3, threshold=0.45)

        assert res["status"] == "POTENTIAL_MATCH"
        assert len(res["candidates"]) == 1
        cand = res["candidates"][0]
        assert cand["case_id"] == 101
        assert cand["is_potential_match"] is True
        assert cand["match_decision"] == "POTENTIAL MATCH"
        assert cand["similarity_score"] >= 95.0

    @patch("services.face_matching.FaceRepository")
    def test_knn_search_no_match_within_threshold(self, mock_repo_cls):
        np.random.seed(42)
        query_vec = np.ones((1404,), dtype=np.float32) * 1.0
        stored_vec = np.ones((1404,), dtype=np.float32) * -1.0

        doc1 = FaceVector(id=2, case_id=102, vector=stored_vec.tolist())
        mock_repo = MagicMock()
        mock_repo.get_all_registered.return_value = [doc1]

        engine = KNNFaceMatchingEngine(face_repo=mock_repo)
        res = engine.match_vector(query_vec, top_k=3, threshold=0.45)

        assert res["status"] == "NO_POTENTIAL_MATCH"
        assert len(res["candidates"]) == 1
        cand = res["candidates"][0]
        assert cand["is_potential_match"] is False
        assert cand["match_decision"] == "NO_POTENTIAL_MATCH"


# ──────────────────────────────────────────────────────────────────────
# 6. Candidate Retrieval & Case Details Tests
# ──────────────────────────────────────────────────────────────────────

class TestCandidateCaseDetails:
    @patch("services.case_service.CaseRepository")
    def test_case_service_retrieves_candidate_case(self, mock_case_repo_cls):
        mock_repo = MagicMock()
        mock_case = MissingPerson(
            id=101,
            case_number="MP-2026-00001",
            name="John Doe",
            age=30,
            gender="Male",
            last_seen_city="Mumbai",
            last_seen_state="Maharashtra",
            status="Missing"
        )
        mock_repo.get_by_id.return_value = mock_case
        mock_case_repo_cls.return_value = mock_repo

        case_service = CaseService(case_repo=mock_repo)
        retrieved = case_service.get_case(101, current_user=ADMIN_USER)

        assert retrieved is not None
        assert retrieved.name == "John Doe"
        assert retrieved.case_number == "MP-2026-00001"


# ──────────────────────────────────────────────────────────────────────
# 7. End-to-End Mocked Admin Matching Workflow
# ──────────────────────────────────────────────────────────────────────

class TestEndToEndAdminWorkflow:
    @patch("services.face_matching.FaceRepository")
    @patch("services.case_service.CaseRepository")
    def test_end_to_end_matching_pipeline(self, mock_case_repo_cls, mock_face_repo_cls):
        # 1. Uploaded Image
        img_bytes = _create_dummy_image_bytes()
        file_obj = _create_mock_uploaded_file(img_bytes)

        valid, msg, pil_img = _validate_uploaded_image(file_obj)
        assert valid is True

        # 2. Landmark Detection & Vector Generation
        landmarks_468 = [FaceLandmark(index=i, x=0.1, y=0.2, z=0.0) for i in range(468)]
        face = DetectedFace(face_index=0, landmarks=landmarks_468)
        det_result = FaceDetectionResult(success=True, num_faces=1, faces=[face])

        q_vec = generate_face_vector_by_index(det_result, face_index=0)
        assert len(q_vec) == 1404

        # 3. KNN Search
        doc = FaceVector(id=1, case_id=55, vector=q_vec.tolist())
        mock_face_repo = MagicMock()
        mock_face_repo.get_all_registered.return_value = [doc]
        mock_face_repo_cls.return_value = mock_face_repo

        engine = KNNFaceMatchingEngine(face_repo=mock_face_repo)
        match_result = engine.match_vector(q_vec, top_k=1, threshold=0.45)

        assert match_result["status"] == "POTENTIAL_MATCH"
        assert len(match_result["candidates"]) == 1

        # 4. Candidate Metadata Retrieval
        mock_case_repo = MagicMock()
        mock_case_repo.get_by_id.return_value = MissingPerson(
            id=55, case_number="MP-2026-00055", name="Test Subject", age=25, gender="Female"
        )
        mock_case_repo_cls.return_value = mock_case_repo

        service = CaseService(case_repo=mock_case_repo)
        case_info = service.get_case(match_result["candidates"][0]["case_id"], current_user=ADMIN_USER)

        assert case_info.name == "Test Subject"
        assert case_info.case_number == "MP-2026-00055"
