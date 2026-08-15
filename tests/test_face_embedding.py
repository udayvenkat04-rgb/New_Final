"""
Phase 13 tests — Face Vector / Embedding Generation.

Covers the 13 required scenarios:
  1. Valid 468-landmark input → produces a vector.
  2. Correct output shape (1404,).
  3. Correct numeric dtype (float32).
  4. No NaN values.
  5. No infinite values.
  6. Deterministic output (identical input → identical vector).
  7. Invalid landmark count → LandmarkCountMismatchError.
  8. Missing X coordinate → LandmarkValidationError.
  9. Missing Y coordinate → LandmarkValidationError.
 10. Missing Z coordinate → LandmarkValidationError.
 11. Empty landmark input → LandmarkValidationError.
 12. Multiple faces producing separate vectors.
 13. Resolution / translation / scale invariance of normalisation.

Tests do NOT require MongoDB or real MediaPipe detection. We build synthetic
landmark fixtures directly so the service logic can be exercised independently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pytest

from services import face_embedding as fe
from services.face_detection import (
    DetectedFace,
    FaceDetectionResult,
    FaceLandmark,
)


# ---------------------------------------------------------------------------
# Helpers: deterministic synthetic landmark fixtures
# ---------------------------------------------------------------------------


def _make_landmarks_array(
    num_landmarks: int = fe.DEFAULT_LANDMARKS_PER_FACE,
    *,
    base_x: float = 0.3,
    base_y: float = 0.25,
    scale: float = 0.4,
    seed: int = 123,
) -> np.ndarray:
    """Return a deterministic (N, 3) float32 array shaped like real landmarks.

    The points are spread in a rectangular grid in XY with a gentle Z variation,
    all inside the canonical MediaPipe normalised [0, 1]² image box.
    """
    rng = np.random.default_rng(seed)
    cols = int(np.ceil(np.sqrt(num_landmarks)))
    rows = int(np.ceil(num_landmarks / cols))
    u = np.arange(cols, dtype=np.float32) / max(1, cols - 1)
    v = np.arange(rows, dtype=np.float32) / max(1, rows - 1)
    uu, vv = np.meshgrid(u, v)
    xs = (base_x + uu.ravel()[:num_landmarks] * scale).astype(np.float32)
    ys = (base_y + vv.ravel()[:num_landmarks] * scale).astype(np.float32)
    jitter = rng.normal(0.0, 0.002, size=num_landmarks).astype(np.float32)
    zs = (-0.05 + (uu.ravel()[:num_landmarks] - 0.5) * 0.1 + jitter).astype(np.float32)
    arr = np.stack([xs, ys, zs], axis=1)
    assert arr.shape == (num_landmarks, 3)
    return arr


def _make_face_landmark_objects(
    num_landmarks: int = fe.DEFAULT_LANDMARKS_PER_FACE,
    **kw,
) -> List[FaceLandmark]:
    arr = _make_landmarks_array(num_landmarks, **kw)
    return [
        FaceLandmark(index=i, x=float(arr[i, 0]), y=float(arr[i, 1]), z=float(arr[i, 2]))
        for i in range(num_landmarks)
    ]


def _make_detected_face(
    face_index: int = 0,
    num_landmarks: int = fe.DEFAULT_LANDMARKS_PER_FACE,
    **kw,
) -> DetectedFace:
    return DetectedFace(
        face_index=face_index,
        landmarks=_make_face_landmark_objects(num_landmarks, **kw),
        bounding_box_pixels=(10, 10, 100, 120),
        presence_score=0.9,
    )


def _make_detection_result(num_faces: int = 1) -> FaceDetectionResult:
    faces = [
        _make_detected_face(face_index=i, seed=7 + i,
                            base_x=0.2 + i * 0.25)
        for i in range(num_faces)
    ]
    return FaceDetectionResult(
        success=True,
        num_faces=num_faces,
        faces=faces,
        image_width=800,
        image_height=600,
        processed_image_rgb=np.zeros((600, 800, 3), dtype=np.uint8),
    )


# ---------------------------------------------------------------------------
# 1-6: Happy-path + shape / dtype / NaN / Inf / determinism
# ---------------------------------------------------------------------------


class TestValidVectorOutput:
    """Scenarios 1–6: valid 468-landmark input → correct vector shape."""

    def test_scenario_01_valid_468_input(self):
        arr = _make_landmarks_array(fe.DEFAULT_LANDMARKS_PER_FACE)
        vec = fe.generate_face_vector(arr)
        assert vec is not None
        assert isinstance(vec, np.ndarray)

    def test_scenario_02_shape_is_1404_1d(self):
        arr = _make_landmarks_array()
        vec = fe.generate_face_vector(arr)
        assert vec.shape == (fe.DEFAULT_VECTOR_DIM,)
        assert vec.ndim == 1
        assert vec.size == fe.DEFAULT_VECTOR_DIM  # 1404 exactly

    def test_scenario_03_dtype_is_float32(self):
        arr = _make_landmarks_array()
        vec = fe.generate_face_vector(arr)
        assert vec.dtype == fe.DEFAULT_VECTOR_DTYPE
        assert np.issubdtype(vec.dtype, np.floating)

    def test_scenario_04_no_nan_values(self):
        arr = _make_landmarks_array()
        vec = fe.generate_face_vector(arr)
        assert not np.isnan(vec).any()
        report = fe.validate_face_vector(vec)
        assert report.has_nan is False

    def test_scenario_05_no_infinite_values(self):
        arr = _make_landmarks_array()
        vec = fe.generate_face_vector(arr)
        assert np.isfinite(vec).all()
        report = fe.validate_face_vector(vec)
        assert report.has_inf is False
        assert report.all_finite is True

    def test_scenario_06_deterministic_output(self):
        arr = _make_landmarks_array(seed=999)
        vec_a = fe.generate_face_vector(arr)
        vec_b = fe.generate_face_vector(arr)
        # Byte-wise identical floats (==) rather than allclose — determinism
        # requires the exact same sequence, not just "close enough".
        np.testing.assert_array_equal(vec_a, vec_b)

    def test_validate_face_vector_reports_valid_on_good_output(self):
        vec = fe.generate_face_vector(_make_landmarks_array())
        report = fe.validate_face_vector(vec)
        assert report.is_valid is True
        assert report.shape == (fe.DEFAULT_VECTOR_DIM,)
        assert len(report.errors) == 0


# ---------------------------------------------------------------------------
# 7. Invalid landmark count
# ---------------------------------------------------------------------------


class TestLandmarkCountMismatch:
    """Scenario 7: landmark count != 468 → LandmarkCountMismatchError."""

    def test_too_few_landmarks_400(self):
        arr = _make_landmarks_array(num_landmarks=400)
        with pytest.raises(fe.LandmarkCountMismatchError) as excinfo:
            fe.generate_face_vector(arr)
        assert excinfo.value.expected == fe.DEFAULT_LANDMARKS_PER_FACE
        assert excinfo.value.actual == 400

    def test_too_many_landmarks_512(self):
        arr = _make_landmarks_array(num_landmarks=512)
        with pytest.raises(fe.LandmarkCountMismatchError):
            fe.generate_face_vector(arr)

    def test_zero_landmarks_via_expected_count(self):
        # (Scenario 11 covers truly-empty input; here we trigger count mismatch
        #  with expected_landmarks=10 and actual 468.)
        arr = _make_landmarks_array(468)
        with pytest.raises(fe.LandmarkCountMismatchError) as excinfo:
            fe.generate_face_vector(arr, expected_landmarks=10)
        assert excinfo.value.expected == 10
        assert excinfo.value.actual == 468

    def test_expected_none_accepts_arbitrary_count(self):
        # Passing expected_landmarks=None disables the strict count check.
        arr = _make_landmarks_array(num_landmarks=100)
        vec = fe.generate_face_vector(arr, expected_landmarks=None)
        assert vec.shape == (100 * 3,)


# ---------------------------------------------------------------------------
# 8-10. Missing X / Y / Z coordinates
# ---------------------------------------------------------------------------


class TestMissingCoordinates:
    """Scenarios 8-10: landmark objects missing X, Y, or Z attrs."""

    def test_scenario_08_missing_x_attribute(self):
        @dataclass
        class NoX:
            y: float
            z: float

        bad = [NoX(y=0.5, z=0.0) for _ in range(fe.DEFAULT_LANDMARKS_PER_FACE)]
        with pytest.raises(fe.LandmarkValidationError, match="X, Y, Z"):
            fe.normalize_landmarks(bad)

    def test_scenario_09_missing_y_attribute(self):
        @dataclass
        class NoY:
            x: float
            z: float

        bad = [NoY(x=0.5, z=0.0) for _ in range(fe.DEFAULT_LANDMARKS_PER_FACE)]
        with pytest.raises(fe.LandmarkValidationError, match="X, Y, Z"):
            fe.normalize_landmarks(bad)

    def test_scenario_10_missing_z_attribute(self):
        @dataclass
        class NoZ:
            x: float
            y: float

        bad = [NoZ(x=0.5, y=0.5) for _ in range(fe.DEFAULT_LANDMARKS_PER_FACE)]
        with pytest.raises(fe.LandmarkValidationError, match="X, Y, Z"):
            fe.normalize_landmarks(bad)

    def test_tuple_with_only_two_values_rejected(self):
        bad = [(0.5, 0.5) for _ in range(fe.DEFAULT_LANDMARKS_PER_FACE)]
        with pytest.raises(fe.LandmarkValidationError):
            fe.normalize_landmarks(bad)

    def test_nan_coordinates_rejected(self):
        arr = _make_landmarks_array()
        arr[5, 0] = np.nan  # corrupt one X value
        with pytest.raises(fe.LandmarkValidationError, match="non-finite"):
            fe.normalize_landmarks(arr)

    def test_inf_coordinates_rejected(self):
        arr = _make_landmarks_array()
        arr[10, 1] = np.inf  # corrupt one Y value
        with pytest.raises(fe.LandmarkValidationError, match="non-finite"):
            fe.normalize_landmarks(arr)


# ---------------------------------------------------------------------------
# 11. Empty landmark input
# ---------------------------------------------------------------------------


class TestEmptyInput:
    """Scenario 11: empty / None-like landmark sequences."""

    def test_empty_list(self):
        with pytest.raises(fe.LandmarkValidationError, match="Empty"):
            fe.normalize_landmarks([])

    def test_empty_tuple(self):
        with pytest.raises(fe.LandmarkValidationError, match="Empty"):
            fe.normalize_landmarks(())

    def test_empty_ndarray(self):
        with pytest.raises(fe.LandmarkValidationError, match="Empty"):
            fe.normalize_landmarks(np.zeros((0, 3), dtype=np.float32))

    def test_empty_detected_face(self):
        face = DetectedFace(face_index=0, landmarks=[])
        with pytest.raises(fe.LandmarkValidationError, match="Empty"):
            fe.generate_face_vector(face)


# ---------------------------------------------------------------------------
# 12. Multiple faces → separate, independent vectors
# ---------------------------------------------------------------------------


class TestMultipleFaces:
    """Scenario 12: multi-face detection → one vector per face."""

    NUM_FACES = 3

    def test_generate_vectors_for_all_faces_count(self):
        result = _make_detection_result(num_faces=self.NUM_FACES)
        vectors = fe.generate_vectors_for_all_faces(result)
        assert isinstance(vectors, list)
        assert len(vectors) == self.NUM_FACES
        for v in vectors:
            assert isinstance(v, np.ndarray)
            assert v.shape == (fe.DEFAULT_VECTOR_DIM,)
            assert v.dtype == fe.DEFAULT_VECTOR_DTYPE

    def test_each_face_vector_is_distinct(self):
        result = _make_detection_result(num_faces=self.NUM_FACES)
        vectors = fe.generate_vectors_for_all_faces(result)
        # Each synthetic face was seeded differently → vectors must differ
        for i in range(self.NUM_FACES):
            for j in range(i + 1, self.NUM_FACES):
                assert not np.array_equal(vectors[i], vectors[j]), (
                    f"Face {i} and face {j} produced the same vector — "
                    "expected independent data to differ."
                )

    def test_generate_face_vector_by_index_selects_correct_face(self):
        result = _make_detection_result(num_faces=self.NUM_FACES)
        all_vecs = fe.generate_vectors_for_all_faces(result)
        for idx in range(self.NUM_FACES):
            vec_by_idx = fe.generate_face_vector_by_index(result, idx)
            np.testing.assert_array_equal(
                vec_by_idx,
                all_vecs[idx],
                err_msg=f"face_index={idx} vector does not match batch index.",
            )

    def test_face_index_out_of_range_raises(self):
        result = _make_detection_result(num_faces=2)
        with pytest.raises(fe.FaceIndexOutOfRangeError):
            fe.generate_face_vector_by_index(result, 5)
        with pytest.raises(fe.FaceIndexOutOfRangeError):
            fe.generate_face_vector_by_index(result, -1)

    def test_no_faces_detected_raises_no_faces_error(self):
        result = FaceDetectionResult(
            success=True, num_faces=0, faces=[],
            image_width=100, image_height=100,
            processed_image_rgb=np.zeros((100, 100, 3), dtype=np.uint8),
        )
        with pytest.raises(fe.NoFacesDetectedError):
            fe.generate_vectors_for_all_faces(result)
        with pytest.raises(fe.NoFacesDetectedError):
            fe.generate_face_vector_by_index(result, 0)

    def test_failed_detection_result_rejected(self):
        result = FaceDetectionResult(
            success=False, error_message="mediapipe crashed",
        )
        with pytest.raises(fe.FaceEmbeddingError, match="failed detection"):
            fe.generate_vectors_for_all_faces(result)


# ---------------------------------------------------------------------------
# 13. Normalisation invariance
# ---------------------------------------------------------------------------


class TestNormalizationInvariance:
    """Scenario 13: equivalent geometry → equivalent normalised representation.

    The normalisation should be invariant to:
      * translation (uniform X/Y shift — e.g. crop vs different frame position)
      * uniform scale (e.g. same face at 2× image resolution — larger bounding
        box but identical relative geometry)
      * z-axis translation (uniform depth offset applied to every point should
        vanish because we subtract the mean z)
    """

    def test_translation_invariance_xy_shift(self):
        base = _make_landmarks_array(seed=5)
        # Shift every point by the same (dx, dy, 0) — face moved in the frame.
        translated = base + np.array([0.2, -0.15, 0.0], dtype=np.float32)
        v_base = fe.generate_face_vector(base)
        v_shifted = fe.generate_face_vector(translated)
        np.testing.assert_allclose(v_base, v_shifted, atol=1e-5, rtol=1e-5)

    def test_uniform_scale_invariance(self):
        base = _make_landmarks_array(seed=7)
        # Uniform scale 2× in XYZ — same face, twice as far from camera (or
        # in a 2× higher-resolution crop). Mean-center removes position; then
        # the farthest-landmark radius doubles so the final normalised set
        # is identical.
        scaled = base * 2.0
        v_base = fe.generate_face_vector(base)
        v_scaled = fe.generate_face_vector(scaled)
        np.testing.assert_allclose(v_base, v_scaled, atol=1e-5, rtol=1e-5)

    def test_uniform_z_translation_invariance(self):
        base = _make_landmarks_array(seed=11)
        z_shifted = base.copy()
        z_shifted[:, 2] += 0.5
        v_base = fe.generate_face_vector(base)
        v_z = fe.generate_face_vector(z_shifted)
        np.testing.assert_allclose(v_base, v_z, atol=1e-5, rtol=1e-5)

    def test_degenerate_face_all_landmarks_collapsed_raises(self):
        # All landmarks at exactly the same XY point → scale factor = 0
        collapsed = np.zeros((fe.DEFAULT_LANDMARKS_PER_FACE, 3), dtype=np.float32)
        collapsed[:, 0] = 0.5
        collapsed[:, 1] = 0.5
        collapsed[:, 2] = np.linspace(-0.1, 0.1, fe.DEFAULT_LANDMARKS_PER_FACE, dtype=np.float32)
        with pytest.raises(fe.DegenerateFaceError):
            fe.normalize_landmarks(collapsed)


# ---------------------------------------------------------------------------
# validate_face_vector negative-path tests
# ---------------------------------------------------------------------------


class TestValidateFaceVectorNegative:
    """Exercise every failure branch of validate_face_vector."""

    def test_wrong_shape_reported(self):
        vec = np.zeros(1400, dtype=np.float32)
        report = fe.validate_face_vector(vec)
        assert report.is_valid is False
        assert any("Shape mismatch" in e for e in report.errors)

    def test_non_numeric_dtype_reported(self):
        vec = np.array(["x"] * fe.DEFAULT_VECTOR_DIM)
        report = fe.validate_face_vector(vec)
        assert report.is_valid is False
        assert any("not numeric" in e.lower() for e in report.errors)

    def test_nan_vector_reported(self):
        vec = np.zeros(fe.DEFAULT_VECTOR_DIM, dtype=np.float32)
        vec[42] = np.nan
        report = fe.validate_face_vector(vec)
        assert report.is_valid is False
        assert report.has_nan is True
        assert any("NaN" in e for e in report.errors)

    def test_inf_vector_reported(self):
        vec = np.zeros(fe.DEFAULT_VECTOR_DIM, dtype=np.float32)
        vec[99] = -np.inf
        report = fe.validate_face_vector(vec)
        assert report.is_valid is False
        assert report.has_inf is True
        assert any("Inf" in e or "infinite" in e.lower() for e in report.errors)

    def test_non_ndarray_input(self):
        report = fe.validate_face_vector([0.0] * fe.DEFAULT_VECTOR_DIM)  # type: ignore[arg-type]
        assert report.is_valid is False
        assert any("numpy ndarray" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Flattening order: confirm landmark-major layout [X0,Y0,Z0,…,XN-1,YN-1,ZN-1]
# ---------------------------------------------------------------------------


class TestVectorLayout:
    """Confirm the flat order matches the documented landmark-major layout."""

    def test_landmark_major_flattening_order(self):
        N = 4  # tiny fixture we can inspect element-wise
        arr = np.asarray(
            [
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 6.0],
                [7.0, 8.0, 9.0],
                [10.0, 11.0, 12.0],
            ],
            dtype=np.float32,
        )
        normed = fe.normalize_landmarks(arr, expected_landmarks=N)
        vec = fe.landmarks_to_vector(normed, expected_landmarks=N)
        # After normalization we can still check the co-location property:
        # landmark i's coordinates occupy positions 3i, 3i+1, 3i+2.
        for i in range(N):
            x_i, y_i, z_i = normed[i]
            assert vec[3 * i + 0] == pytest.approx(x_i)
            assert vec[3 * i + 1] == pytest.approx(y_i)
            assert vec[3 * i + 2] == pytest.approx(z_i)


# ---------------------------------------------------------------------------
# DetectedFace (dataclass) input path for generate_face_vector
# ---------------------------------------------------------------------------


class TestDetectedFaceInput:
    """generate_face_vector accepts Phase 12 DetectedFace instances."""

    def test_detected_face_produces_1404_vector(self):
        face = _make_detected_face()
        vec = fe.generate_face_vector(face)
        assert vec.shape == (fe.DEFAULT_VECTOR_DIM,)

    def test_face_landmark_dataclass_list_input(self):
        lms = _make_face_landmark_objects()
        vec = fe.generate_face_vector(lms)
        assert vec.shape == (fe.DEFAULT_VECTOR_DIM,)

    def test_list_of_xyz_tuples_input(self):
        tuples: List[Tuple[float, float, float]] = [
            (0.1 + i * 0.001, 0.2 + i * 0.001, -0.05 + i * 0.0001)
            for i in range(fe.DEFAULT_LANDMARKS_PER_FACE)
        ]
        vec = fe.generate_face_vector(tuples)
        assert vec.shape == (fe.DEFAULT_VECTOR_DIM,)

    def test_list_of_dicts_with_xyz_keys_input(self):
        dicts = [
            {"x": 0.3 + i * 0.001, "y": 0.4, "z": 0.0}
            for i in range(fe.DEFAULT_LANDMARKS_PER_FACE)
        ]
        vec = fe.generate_face_vector(dicts)
        assert vec.shape == (fe.DEFAULT_VECTOR_DIM,)


# ---------------------------------------------------------------------------
# Meta / config helper
# ---------------------------------------------------------------------------


class TestEmbeddingConfig:
    def test_get_embedding_config_returns_expected_keys(self):
        cfg = fe.get_embedding_config()
        assert isinstance(cfg, dict)
        assert cfg["default_landmarks_per_face"] == 468
        assert cfg["default_coords_per_landmark"] == 3
        assert cfg["default_vector_dim"] == 1404
        assert cfg["refuses_to_truncate_or_pad"] is True
        assert "normalization" in cfg and isinstance(cfg["normalization"], str)
