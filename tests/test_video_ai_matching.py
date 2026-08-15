"""
Unit & Integration Test Suite for Video AI Matching Service (Phase 18).

Tests:
1. Video with no faces
2. Video with one face
3. Video with multiple faces
4. Multiple faces in one frame
5. Same face across many frames
6. Different cases across frames
7. Duplicate case aggregation
8. First-seen timestamp
9. Last-seen timestamp
10. Detection count
11. Best similarity
12. Representative-frame selection
13. Temporal grouping
14. No potential match
15. Invalid vector handling
16. KNN failure on one frame
17. MediaPipe failure on one frame
18. Empty video
19. Processing statistics
20. Officer authorization rejection
21. Admin authorization success
"""

import os
import tempfile
import pytest
import numpy as np
import cv2

from auth.permissions import ROLE_ADMIN, ROLE_OFFICER, authorize_process_video
from config import settings
from models.face_vector import FaceVector
from models.missing_person import MissingPerson
from repositories.case_repository import CaseRepository
from repositories.face_repository import FaceRepository
from services.face_detection import DetectedFace, FaceDetectionResult, FaceLandmark
from services.video_ai_service import (
    AggregatedVideoSighting,
    FrameFaceMatch,
    TemporalSegment,
    VideoAIScanResult,
    VideoAIService,
)


# ── Helper Fixtures & Synthetic Video Generator ──────────────────────

def create_synthetic_mp4_video(
    filename: str = "test_ai_synthetic.mp4",
    width: int = 320,
    height: int = 240,
    fps: float = 30.0,
    num_frames: int = 60
) -> str:
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, filename)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = ((i * 4) % 256, 100, 150)
        out.write(frame)

    out.release()
    return video_path


@pytest.fixture
def synthetic_video():
    video_path = create_synthetic_mp4_video("test_ai_fixture.mp4", num_frames=60, fps=30.0)
    yield video_path
    if os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass


# ── Helper Mock Classes for Isolated Testing ────────────────────────

class MockCaseRepository:
    def __init__(self):
        self.cases = {
            "1": MissingPerson(id=1, name="Alice Smith", status="Missing"),
            "2": MissingPerson(id=2, name="Bob Jones", status="Missing"),
            1: MissingPerson(id=1, name="Alice Smith", status="Missing"),
            2: MissingPerson(id=2, name="Bob Jones", status="Missing"),
        }

    def get_by_id(self, case_id):
        return self.cases.get(case_id) or self.cases.get(str(case_id))


class MockFaceRepository:
    def __init__(self, registered_vectors=None):
        self.vectors = registered_vectors or []

    def get_all_registered(self):
        return self.vectors


# ── Test Cases ──────────────────────────────────────────────────────

def test_video_no_faces(synthetic_video):
    """1. Test video with no faces detected returns NO_FACES_DETECTED."""
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([FaceVector(id=1, case_id=1, vector=[0.1]*1404)]))
    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "NO_FACES_DETECTED"
    assert res.statistics["frames_with_faces"] == 0
    assert res.statistics["total_faces_detected"] == 0


def test_video_one_face(monkeypatch, synthetic_video):
    """2. Test video with one face detected per frame matching a case."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        face = DetectedFace(landmarks=landmarks, face_index=0)
        return FaceDetectionResult(success=True, num_faces=1, faces=[face], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    ref_vector = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([ref_vector]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "SUCCESS"
    assert len(res.unique_candidates) == 1
    cand = res.unique_candidates[0]
    assert cand.case_id == "1"
    assert cand.case_name == "Alice Smith"
    assert cand.detection_count == 2


def test_video_multiple_faces(monkeypatch, synthetic_video):
    """3. Test video with faces matching different cases across frames."""
    call_count = {"count": 0}

    def mock_detect_faces(img):
        call_count["count"] += 1
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        face = DetectedFace(landmarks=landmarks, face_index=0)
        return FaceDetectionResult(success=True, num_faces=1, faces=[face], image_width=320, image_height=240)

    def mock_gen_vec(face):
        if call_count["count"] == 1:
            return np.full((1404,), 0.1, dtype=np.float32)
        return np.full((1404,), 0.5, dtype=np.float32)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", mock_gen_vec)

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    v2 = FaceVector(id=2, case_id=2, vector=[0.5]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1, v2]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "SUCCESS"
    assert len(res.unique_candidates) == 2
    case_ids = {c.case_id for c in res.unique_candidates}
    assert case_ids == {"1", "2"}


def test_multiple_faces_in_one_frame(monkeypatch, synthetic_video):
    """4. Test multiple faces detected in a single frame processed independently."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        f1 = DetectedFace(landmarks=landmarks, face_index=0)
        f2 = DetectedFace(landmarks=landmarks, face_index=1)
        return FaceDetectionResult(success=True, num_faces=2, faces=[f1, f2], image_width=320, image_height=240)

    face_vec_idx = {"idx": 0}

    def mock_gen_vec(face):
        face_vec_idx["idx"] += 1
        if face_vec_idx["idx"] % 2 == 1:
            return np.full((1404,), 0.1, dtype=np.float32)
        return np.full((1404,), 0.5, dtype=np.float32)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", mock_gen_vec)

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    v2 = FaceVector(id=2, case_id=2, vector=[0.5]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1, v2]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=2.0)
    assert res.status == "SUCCESS"
    assert res.statistics["total_faces_detected"] == 2
    assert len(res.unique_candidates) == 2


def test_same_face_across_many_frames(monkeypatch, synthetic_video):
    """5. Test same face across many frames aggregated into 1 candidate."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        face = DetectedFace(landmarks=landmarks, face_index=0)
        return FaceDetectionResult(success=True, num_faces=1, faces=[face], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=0.5)
    assert res.status == "SUCCESS"
    assert len(res.unique_candidates) == 1
    assert res.unique_candidates[0].detection_count == 4  # frames 0, 15, 30, 45


def test_different_cases_across_frames(monkeypatch, synthetic_video):
    """6. Test different registered cases detected in video."""
    call_count = {"cnt": 0}
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    def mock_gen_vec(face):
        call_count["cnt"] += 1
        if call_count["cnt"] == 1:
            return np.full((1404,), 0.1, dtype=np.float32)
        return np.full((1404,), 0.8, dtype=np.float32)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", mock_gen_vec)

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    v2 = FaceVector(id=2, case_id=2, vector=[0.8]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1, v2]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "SUCCESS"
    assert len(res.unique_candidates) == 2


def test_duplicate_case_aggregation(monkeypatch, synthetic_video):
    """7. Test duplicate case detections aggregated into single candidate."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert len(res.unique_candidates) == 1
    assert res.unique_candidates[0].case_id == "1"


def test_first_seen_timestamp(monkeypatch, synthetic_video):
    """8. Test first_seen_timestamp accuracy."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.unique_candidates[0].first_seen_timestamp == 0.0


def test_last_seen_timestamp(monkeypatch, synthetic_video):
    """9. Test last_seen_timestamp accuracy."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert pytest.approx(res.unique_candidates[0].last_seen_timestamp, 0.01) == 1.0


def test_detection_count(monkeypatch, synthetic_video):
    """10. Test total detection count for aggregated candidate."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.unique_candidates[0].detection_count == 2


def test_best_similarity(monkeypatch, synthetic_video):
    """11. Test best_similarity score calculation."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.unique_candidates[0].best_similarity == 100.0


def test_representative_frame_selection(monkeypatch, synthetic_video):
    """12. Test representative frame selection."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.unique_candidates[0].representative_frame is not None
    assert isinstance(res.unique_candidates[0].representative_frame, np.ndarray)


def test_temporal_grouping():
    """13. Test temporal grouping into segments based on gap_seconds."""
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository())
    matches = [
        FrameFaceMatch(frame_index=0, timestamp_seconds=1.0, face_index=0, case_id="1", case_name="Alice", distance=0.1, similarity_score=95.0),
        FrameFaceMatch(frame_index=30, timestamp_seconds=2.0, face_index=0, case_id="1", case_name="Alice", distance=0.1, similarity_score=95.0),
        FrameFaceMatch(frame_index=300, timestamp_seconds=20.0, face_index=0, case_id="1", case_name="Alice", distance=0.1, similarity_score=95.0),
    ]

    aggregated = service._aggregate_frame_matches(matches, gap_seconds=5.0)
    assert len(aggregated) == 1
    cand = aggregated[0]
    assert len(cand.segments) == 2
    assert cand.segments[0].start_timestamp == 1.0
    assert cand.segments[0].end_timestamp == 2.0
    assert cand.segments[1].start_timestamp == 20.0


def test_no_potential_match(monkeypatch, synthetic_video):
    """14. Test faces detected but none pass KNN threshold returns NO_POTENTIAL_MATCH."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 10.0, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[-10.0]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0, threshold=0.1)
    assert res.status == "NO_POTENTIAL_MATCH"
    assert len(res.unique_candidates) == 0


def test_invalid_vector_handling(monkeypatch, synthetic_video):
    """15. Test invalid / nan face vector handled safely."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), np.nan, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "NO_POTENTIAL_MATCH"


def test_knn_failure_on_one_frame(monkeypatch, synthetic_video):
    """16. Test single frame KNN exception does not fail video scan."""
    call_count = {"cnt": 0}
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    def mock_gen_vec(face):
        call_count["cnt"] += 1
        if call_count["cnt"] == 1:
            raise ValueError("KNN mock error on frame 1")
        return np.full((1404,), 0.1, dtype=np.float32)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", mock_gen_vec)

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "SUCCESS"
    assert len(res.unique_candidates) == 1


def test_mediapipe_failure_on_one_frame(monkeypatch, synthetic_video):
    """17. Test MediaPipe exception on one frame does not fail remaining frames."""
    call_count = {"cnt": 0}
    def mock_detect_faces(img):
        call_count["cnt"] += 1
        if call_count["cnt"] == 1:
            raise RuntimeError("MediaPipe temporary GPU error")
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    assert res.status == "SUCCESS"
    assert len(res.unique_candidates) == 1


def test_empty_video():
    """18. Test empty video file handled safely."""
    temp_dir = tempfile.gettempdir()
    empty_path = os.path.join(temp_dir, "empty_ai.mp4")
    with open(empty_path, "wb") as f:
        pass

    try:
        service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([FaceVector(id=1, case_id=1, vector=[0.1]*1404)]))
        res = service.process_video_ai(empty_path)
        assert res.status == "ERROR"
        assert "empty" in res.message.lower()
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)


def test_processing_statistics(monkeypatch, synthetic_video):
    """19. Test processing statistics content."""
    def mock_detect_faces(img):
        landmarks = [FaceLandmark(index=i, x=0.5, y=0.5, z=0.0) for i in range(468)]
        return FaceDetectionResult(success=True, num_faces=1, faces=[DetectedFace(landmarks=landmarks, face_index=0)], image_width=320, image_height=240)

    monkeypatch.setattr("services.video_ai_service.detect_faces", mock_detect_faces)
    monkeypatch.setattr("services.video_ai_service.generate_face_vector", lambda f: np.full((1404,), 0.1, dtype=np.float32))

    v1 = FaceVector(id=1, case_id=1, vector=[0.1]*1404)
    service = VideoAIService(case_repo=MockCaseRepository(), face_repo=MockFaceRepository([v1]))

    res = service.process_video_ai(synthetic_video, sample_interval_seconds=1.0)
    stats = res.statistics
    assert stats["total_video_frames"] == 60
    assert stats["sampled_frames"] == 2
    assert stats["processed_frames"] == 2
    assert stats["frames_with_faces"] == 2
    assert stats["total_faces_detected"] == 2
    assert stats["valid_vectors_generated"] == 2
    assert stats["knn_queries_performed"] == 2
    assert stats["potential_matches"] == 2
    assert stats["unique_candidate_cases"] == 1


def test_officer_authorization_rejection():
    """20. Test non-admin OFFICER role rejected by authorization guard."""
    officer_user = {"username": "officer_bob", "role": ROLE_OFFICER}
    with pytest.raises(PermissionError, match="Only administrators can process video sightings"):
        authorize_process_video(officer_user)


def test_admin_authorization_success():
    """21. Test admin role allowed by authorization guard."""
    admin_user = {"username": "admin_alice", "role": ROLE_ADMIN}
    res = authorize_process_video(admin_user)
    assert res is True
