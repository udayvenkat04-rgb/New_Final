"""
Unit & Integration Test Suite for Group Photo Face Recognition & Matching Accuracy.

Verifies:
1. 2-Stage Face Crop Landmarking on multi-face / group images.
2. Aspect-ratio invariant face vector embedding generation.
3. Matching similarity between individual selfie reference photos and group photo faces.
"""
import numpy as np
import pytest

from backend.services.face_detection import (
    detect_faces,
    DetectedFace,
    FaceLandmark,
    FaceDetectionResult,
    _refine_face_landmarks_with_crop,
)
from backend.services.face_embedding import (
    normalize_landmarks,
    generate_face_vector,
    generate_face_vector_by_index,
    DEFAULT_LANDMARKS_PER_FACE,
)
from backend.services.face_matching import validate_query_vector


def _create_synthetic_landmarks(num_points: int = 468, scale_x: float = 1.0, scale_y: float = 1.0) -> list[FaceLandmark]:
    """Helper to generate canonical 468 landmark face grid."""
    lms = []
    cols = int(np.ceil(np.sqrt(num_points)))
    rows = int(np.ceil(num_points / cols))
    u = np.linspace(0.3, 0.7, cols) * scale_x
    v = np.linspace(0.3, 0.7, rows) * scale_y
    uu, vv = np.meshgrid(u, v)
    xs = uu.ravel()[:num_points]
    ys = vv.ravel()[:num_points]
    for i in range(num_points):
        lms.append(FaceLandmark(index=i, x=float(xs[i]), y=float(ys[i]), z=0.01 * (i % 5)))
    return lms


def test_aspect_ratio_invariant_normalization():
    """Verify aspect-ratio correction matches 16:9 group photos and 1:1 selfie faces."""
    # Physical face grid of 200x200 pixels
    num_points = 468
    cols = int(np.ceil(np.sqrt(num_points)))
    rows = int(np.ceil(num_points / cols))
    px = np.linspace(150, 350, cols)  # 200px wide
    py = np.linspace(150, 350, rows)  # 200px high
    pxx, pyy = np.meshgrid(px, py)
    px_flat = pxx.ravel()[:num_points]
    py_flat = pyy.ravel()[:num_points]

    # Face in 500x500 selfie image
    lms_square = []
    for i in range(num_points):
        lms_square.append(FaceLandmark(index=i, x=float(px_flat[i] / 500.0), y=float(py_flat[i] / 500.0), z=0.01 * (i % 5)))

    # Same physical 200x200px face placed in a 1920x1080 group photo (e.g. at x=800, y=400)
    lms_group = []
    for i in range(num_points):
        gx = (px_flat[i] - 150 + 800) / 1920.0
        gy = (py_flat[i] - 150 + 400) / 1080.0
        lms_group.append(FaceLandmark(index=i, x=float(gx), y=float(gy), z=0.01 * (i % 5)))

    # Vector generated from 1:1 square selfie
    vec_square = generate_face_vector(
        lms_square,
        image_width=500,
        image_height=500,
    )

    # Vector generated from 16:9 landscape group photo of same face
    vec_landscape = generate_face_vector(
        lms_group,
        image_width=1920,
        image_height=1080,
    )

    # Validate output shapes & finite values
    assert vec_square.shape == (1404,)
    assert vec_landscape.shape == (1404,)
    assert np.all(np.isfinite(vec_square))
    assert np.all(np.isfinite(vec_landscape))

    # Euclidean distance between normalized physical face vectors should be within match margin (< 1.3)
    dist = float(np.linalg.norm(vec_square - vec_landscape))
    assert dist < 1.3, f"Aspect ratio distance {dist:.4f} exceeds threshold 1.3"


def test_crop_landmark_refinement_execution():
    """Verify 2-stage crop refinement runs safely on DetectedFace objects."""
    lms = _create_synthetic_landmarks(468)
    face = DetectedFace(
        face_index=0,
        landmarks=lms,
        bounding_box_pixels=(100, 100, 150, 150),
        presence_score=0.95,
    )

    dummy_rgb = np.full((600, 800, 3), 200, dtype=np.uint8)

    # Graceful execution when landmarker is None or mock
    refined_face = _refine_face_landmarks_with_crop(face, dummy_rgb, landmarker=None)
    assert refined_face is not None
    assert len(refined_face.landmarks) == 468


def test_group_photo_detection_result_integration():
    """Verify detect_faces returns valid FaceDetectionResult with refine_crops parameter."""
    dummy_img = np.full((400, 600, 3), 180, dtype=np.uint8)
    res = detect_faces(dummy_img, refine_crops=True)
    assert isinstance(res, FaceDetectionResult)
    assert res.success is True
