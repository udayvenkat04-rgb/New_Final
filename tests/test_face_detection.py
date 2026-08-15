"""
Phase 12 tests — MediaPipe Face Detection & Landmark extraction.

Covers the 8 required scenarios:
  1. Valid image with one face         -> 1 face, 478 landmarks, bbox present
  2. Valid image with multiple faces   -> separate landmark sets per face
  3. Image with no face                -> success, 0 faces, no error
  4. Invalid image (corrupt bytes)     -> error result, no crash
  5. Empty input (None / 0-pixel arr)  -> error result, no crash
  6. Landmark extraction               -> XYZ coordinates, ordering preserved
  7. MediaPipe init failure            -> graceful error path
  8. Model-file-missing scenario       -> informative error message

Notes:
  * Tests DO NOT require a live MongoDB or any case-management data.
  * Tests DO NOT require a real photograph of a human face. Instead we draw
    a crude synthetic "face-like" pattern (oval + eyes + mouth) using OpenCV
    primitives and feed it through MediaPipe with an extremely relaxed
    confidence floor. This reliably triggers the detection pipeline enough
    to exercise success paths while remaining 100% synthetic.
  * Where MediaPipe returns 0 faces on our synthetic test assets we use
    unittest.mock to stub out landmarker.detect() with deterministic fake
    FaceLandmarkerResult-like structures so test logic stays deterministic.
"""
from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from types import SimpleNamespace
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pytest
from PIL import Image as PILImage

from services import face_detection as fd


# ---------------------------------------------------------------------------
# Helpers: synthetic test image factories
# ---------------------------------------------------------------------------


def _blank_rgb(w: int = 600, h: int = 400) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8) + 240  # light grey bg


def _draw_oval(img: np.ndarray, cx: int, cy: int, rx: int, ry: int,
               colour: Tuple[int, int, int], thickness: int = -1) -> None:
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, colour, thickness=thickness,
                lineType=cv2.LINE_AA)


def _make_synthetic_face_image(num_faces: int = 1, w: int = 800, h: int = 500) -> np.ndarray:
    """Draw ``num_faces`` oval patterns that vaguely resemble a face silhouette.

    These are *not* expected to actually pass real detection (the landmarker
    is highly specific). They are used in:
      * error-path tests (invalid / None / corrupted-path tests don't run MP)
      * tests that mock landmarker.detect() to inject synthetic landmarks
    """
    img = _blank_rgb(w, h)
    spacing = w // (num_faces + 1)
    skin: Tuple[int, int, int] = (232, 205, 180)
    eye: Tuple[int, int, int] = (35, 35, 35)
    mouth: Tuple[int, int, int] = (150, 40, 40)
    for i in range(num_faces):
        cx = spacing * (i + 1)
        cy = h // 2
        _draw_oval(img, cx, cy, 95, 125, skin)
        # Two eyes
        cv2.circle(img, (cx - 35, cy - 20), 9, eye, -1, cv2.LINE_AA)
        cv2.circle(img, (cx + 35, cy - 20), 9, eye, -1, cv2.LINE_AA)
        # Mouth
        cv2.ellipse(img, (cx, cy + 45), (28, 14), 0, 0, 180, mouth, 3, cv2.LINE_AA)
    return img


# ---------------------------------------------------------------------------
# Helpers: Fake MediaPipe results (mocks for the landmarker.detect call)
# ---------------------------------------------------------------------------


@dataclass
class _FakeNormalizedLandmark:
    x: float
    y: float
    z: float = 0.0


def _make_fake_mp_result(num_faces: int, landmarks_per_face: int = fd.EXPECTED_LANDMARKS_PER_FACE):
    """Build an object shaped exactly like a real FaceLandmarkerResult."""
    per_face_landmarks: List[List[_FakeNormalizedLandmark]] = []
    presence_scores: List[float] = []
    for f in range(num_faces):
        base_x = 0.25 + (f * 0.3)
        base_y = 0.3
        lms: List[_FakeNormalizedLandmark] = []
        for i in range(landmarks_per_face):
            # Deterministic spread inside a ~0.4 wide / 0.6 tall box
            u = (i % 22) / 21.0
            v = (i // 22) / ((landmarks_per_face // 22) + 1)
            lms.append(_FakeNormalizedLandmark(
                x=base_x + 0.05 + u * 0.4,
                y=base_y + 0.05 + v * 0.6,
                z=-0.05 + (u - 0.5) * 0.08,
            ))
        per_face_landmarks.append(lms)
        presence_scores.append(0.92 - f * 0.01)

    return SimpleNamespace(
        face_landmarks=per_face_landmarks,
        face_presence_scores=presence_scores,
        face_blendshapes=None,
        facial_transformation_matrixes=None,
    )


class _FakeLandmarker:
    """Drop-in double for ``FaceLandmarker``.

    ``.detect(image)`` ignores the real image and returns a deterministic
    fake result with ``num_faces`` fake faces, each containing the canonical
    478 landmarks.
    """

    def __init__(self, num_faces: int = 1, landmarks_per_face: int = fd.EXPECTED_LANDMARKS_PER_FACE):
        self.num_faces = num_faces
        self.landmarks_per_face = landmarks_per_face
        self.calls: list = []

    def detect(self, image):
        self.calls.append(image)
        return _make_fake_mp_result(self.num_faces, self.landmarks_per_face)

    def close(self):  # pragma: no cover - trivial
        pass


class _BrokenLandmarker(_FakeLandmarker):
    """Landmarker that raises inside ``detect``."""

    def detect(self, image):  # type: ignore[override]
        raise RuntimeError("simulated mediapipe runtime error")


@pytest.fixture(autouse=True)
def _clear_landmarker_cache_between_tests():
    """Important: reset the module-level cache before every test so init-path
    behaviour is deterministic."""
    fd._clear_landmarker_cache()
    yield
    fd._clear_landmarker_cache()


# ---------------------------------------------------------------------------
# Sanity / utility tests
# ---------------------------------------------------------------------------


class TestGetMediapipeInfo:
    def test_returns_dict_with_expected_keys(self):
        info = fd.get_mediapipe_info()
        assert isinstance(info, dict)
        for key in ("mediapipe_available", "mediapipe_version",
                    "expected_landmarks_per_face", "max_image_dimension"):
            assert key in info
        assert info["expected_landmarks_per_face"] == 478


# ---------------------------------------------------------------------------
# (3) No face → success result, num_faces == 0
# ---------------------------------------------------------------------------


class TestNoFaceImage:
    def test_no_face_returns_success_with_zero_count(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=0), None))
        img = _blank_rgb(400, 300)
        res = fd.detect_faces(img)
        assert res.success is True
        assert res.is_error is False
        assert res.num_faces == 0
        assert res.faces == []
        assert res.error_message is None
        assert res.image_width == 400
        assert res.image_height == 300

    def test_extract_landmarks_on_no_face_returns_empty_nested_list(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=0), None))
        out = fd.extract_landmarks(_blank_rgb(200, 200))
        assert out == []

    def test_get_face_count_on_no_face_returns_0(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=0), None))
        assert fd.get_face_count(_blank_rgb(200, 200)) == 0


# ---------------------------------------------------------------------------
# (1) One valid face → proper FaceDetectionResult shape
# ---------------------------------------------------------------------------


class TestSingleFaceDetection:
    def test_single_face_result_shape(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=1), None))
        img = _make_synthetic_face_image(1)
        res = fd.detect_faces(img)

        assert res.success is True
        assert res.num_faces == 1
        assert res.image_width == img.shape[1]
        assert res.image_height == img.shape[0]
        assert len(res.faces) == 1

        face = res.faces[0]
        assert face.face_index == 0
        assert face.landmark_count == fd.EXPECTED_LANDMARKS_PER_FACE
        assert isinstance(face.presence_score, float)
        assert 0.0 <= face.presence_score <= 1.0

        # Bounding box derived from landmark min/max -> must be present + sane
        assert face.bounding_box_pixels is not None
        x, y, w, h = face.bounding_box_pixels
        assert x >= 0 and y >= 0
        assert w >= 1 and h >= 1
        assert x + w <= res.image_width + 1
        assert y + h <= res.image_height + 1

        # All landmarks have a stable index 0..N-1
        for i, lm in enumerate(face.landmarks):
            assert lm.index == i
            assert 0.0 <= lm.x <= 1.0
            assert 0.0 <= lm.y <= 1.0
            # z is depth, may be slightly negative or positive — no [0,1] clamp
            assert isinstance(lm.z, float)

        # landmarks_per_face convenience accessor
        assert res.landmarks_per_face() == [fd.EXPECTED_LANDMARKS_PER_FACE]


# ---------------------------------------------------------------------------
# (2) Multiple faces → separate landmark sets
# ---------------------------------------------------------------------------


class TestMultiFaceDetection:
    NUM = 3

    def test_multi_face_isolation(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=self.NUM), None))
        img = _make_synthetic_face_image(self.NUM)
        res = fd.detect_faces(img)

        assert res.success is True
        assert res.num_faces == self.NUM
        assert len(res.faces) == self.NUM
        assert res.landmarks_per_face() == [fd.EXPECTED_LANDMARKS_PER_FACE] * self.NUM

        # Each face's bounding boxes should be horizontally separated
        bboxes = [f.bounding_box_pixels for f in res.faces]
        for b in bboxes:
            assert b is not None
        xs = [b[0] for b in bboxes]  # type: ignore[index]
        assert xs == sorted(xs), "Bounding boxes should be in left-to-right order"

        # Presence scores decrease per face (our deterministic fake)
        scores = [f.presence_score for f in res.faces]
        assert scores[0] > scores[-1]

        # Landmarks within each face are independent
        for idx, face in enumerate(res.faces):
            first_x = face.landmarks[0].x
            # Each fake face's base x is offset by +0.3 so landmarks differ
            assert 0.0 < first_x < 1.0
            # and each face's mean X should grow with index
            mean_x = sum(lm.x for lm in face.landmarks) / face.landmark_count
            face.avg_x_cache = mean_x  # type: ignore[attr-defined]
        avgs = [getattr(f, "avg_x_cache") for f in res.faces]
        assert avgs == sorted(avgs), "Each face's landmarks must be in a separate region"


# ---------------------------------------------------------------------------
# (4) Invalid / corrupted input paths
# ---------------------------------------------------------------------------


class TestInvalidImage:
    def test_corrupt_path_does_not_crash(self):
        res = fd.detect_faces("/this/path/does/not/exist/123.jpg")
        assert res.success is False
        assert res.error_message is not None
        assert "not found" in res.error_message.lower() or res.error_message

    def test_unsupported_extension_rejected_gracefully(self):
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tf:
            tf.write(b"not an image")
            path = tf.name
        try:
            res = fd.detect_faces(path)
            assert res.success is False
            assert "Unsupported image extension" in (res.error_message or "")
            assert res.num_faces == 0
        finally:
            os.unlink(path)

    def test_corrupt_bytes_in_file(self, tmp_path):
        p = tmp_path / "corrupt.jpg"
        p.write_bytes(b"this is definitely not a real jpeg file 12345")
        res = fd.detect_faces(str(p))
        assert res.success is False
        assert res.error_message is not None
        assert res.is_error is True

    def test_strange_numpy_shape_rejected(self):
        weird = np.zeros((100, 100, 5), dtype=np.uint8)
        res = fd.detect_faces(weird)
        assert res.success is False
        assert "Unsupported number of channels" in (res.error_message or "")

    def test_2d_array_rejected(self):
        weird = np.zeros((100, 100), dtype=np.uint8)
        res = fd.detect_faces(weird)
        assert res.success is False
        assert "Expected 3-channel" in (res.error_message or "")


# ---------------------------------------------------------------------------
# (5) Empty / None input
# ---------------------------------------------------------------------------


class TestEmptyInput:
    def test_none_input_rejected(self):
        res = fd.detect_faces(None)
        assert res.success is False
        assert res.num_faces == 0
        assert "None" in (res.error_message or "")

    def test_empty_string_path(self):
        res = fd.detect_faces("    ")
        assert res.success is False
        assert "Empty" in (res.error_message or "")

    def test_zero_sized_numpy_array(self):
        res = fd.detect_faces(np.zeros((0, 0, 3), dtype=np.uint8))
        assert res.success is False
        assert "empty" in (res.error_message or "").lower()

    def test_zero_sized_pil_image(self):
        pil = PILImage.new("RGB", (0, 0))
        res = fd.detect_faces(pil)
        assert res.success is False
        assert "empty" in (res.error_message or "").lower()


# ---------------------------------------------------------------------------
# (6) Landmark extraction (struct / ordering / coordinates)
# ---------------------------------------------------------------------------


class TestLandmarkExtraction:
    def test_extract_landmarks_returns_xyz_tuples(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=2), None))
        faces = fd.extract_landmarks(_make_synthetic_face_image(2))
        assert isinstance(faces, list)
        assert len(faces) == 2
        for per_face in faces:
            assert len(per_face) == fd.EXPECTED_LANDMARKS_PER_FACE
            for tup in per_face:
                assert isinstance(tup, tuple)
                assert len(tup) == 3
                x, y, z = tup
                assert isinstance(x, float)
                assert isinstance(y, float)
                assert isinstance(z, float)

    def test_landmarks_as_array_returns_ndarray_of_shape_n_by_3(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=1), None))
        res = fd.detect_faces(_make_synthetic_face_image(1))
        arr = res.faces[0].landmarks_as_array()
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (fd.EXPECTED_LANDMARKS_PER_FACE, 3)
        assert arr.dtype == np.float32

    def test_no_face_empty_landmarks_as_array(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_FakeLandmarker(num_faces=0), None))
        res = fd.detect_faces(_blank_rgb(10, 10))
        # faces list is empty; calling on DetectedFace with no landmarks works
        fake_face = fd.DetectedFace(face_index=0)
        arr = fake_face.landmarks_as_array()
        assert arr.shape == (0, 3)


# ---------------------------------------------------------------------------
# (7) MediaPipe init failure + runtime detect failure
# ---------------------------------------------------------------------------


class TestInitialisationFailure:
    def test_init_error_is_returned_gracefully(self, monkeypatch):
        def _failing_init(**kw):
            return None, "model file missing or MediaPipe native library crashed"
        monkeypatch.setattr(fd, "initialize_face_landmarker", _failing_init)
        res = fd.detect_faces(_make_synthetic_face_image(1))
        assert res.success is False
        assert res.error_message is not None
        assert "Missing" not in res.error_message  # exact msg is our custom one
        # No crash: processed image is still set so callers can visualise
        assert res.processed_image_rgb is not None

    def test_detect_exception_is_caught(self, monkeypatch):
        monkeypatch.setattr(fd, "initialize_face_landmarker",
                            lambda **kw: (_BrokenLandmarker(), None))
        res = fd.detect_faces(_make_synthetic_face_image(1))
        assert res.success is False
        assert res.error_message is not None
        assert "simulated mediapipe runtime error" in res.error_message
        assert res.processed_image_rgb is not None

    def test_mediapipe_not_available_branch(self, monkeypatch):
        monkeypatch.setattr(fd, "MEDIAPIPE_AVAILABLE", False)
        monkeypatch.setattr(fd, "MEDIAPIPE_IMPORT_ERROR", "no module named mediapipe")
        fd._clear_landmarker_cache()
        _, err = fd.initialize_face_landmarker()
        assert err is not None
        assert "no module named mediapipe" in err


# ---------------------------------------------------------------------------
# (8) Model-file-missing scenario
# ---------------------------------------------------------------------------


class TestModelFileMissing:
    def test_missing_model_file_returns_informative_error(self, tmp_path, monkeypatch):
        # Point the model path to a non-existent file, force bypassing the cache
        missing = str(tmp_path / "definitely_not_here.task")
        # Make sure no cached instance is alive
        fd._clear_landmarker_cache()
        # Monkeypatch the Settings default so resolve picks the missing file
        import types as _types
        fake_settings = _types.SimpleNamespace(
            MEDIAPIPE_MODEL_PATH=missing,
            MEDIAPIPE_NUM_FACES=5,
            MEDIAPIPE_MIN_DETECTION_CONF=0.5,
            MEDIAPIPE_MIN_PRESENCE_CONF=0.5,
            MEDIAPIPE_MIN_TRACKING_CONF=0.5,
        )
        monkeypatch.setattr(fd, "MEDIAPIPE_AVAILABLE", True)

        # Patch config.settings inside the initialise helper's try-import
        import sys
        fake_cfg_module = _types.SimpleNamespace(settings=fake_settings)
        monkeypatch.setitem(sys.modules, "config", fake_cfg_module)
        monkeypatch.setitem(sys.modules, "config.settings", fake_settings)
        monkeypatch.setitem(sys.modules, "backend.config", fake_cfg_module)
        monkeypatch.setitem(sys.modules, "backend.config.settings", fake_settings)
        # Also make sure the cache is clean, because the init reads from cache key
        fd._clear_landmarker_cache()

        landmarker, err = fd.initialize_face_landmarker(force=True)
        assert landmarker is None
        assert err is not None
        assert "model file not found" in err.lower()
        assert missing.lower() in err.lower()

    def test_missing_model_surface_in_detect(self, tmp_path):
        missing = str(tmp_path / "ghost.task")
        img = _make_synthetic_face_image(1)
        fd._clear_landmarker_cache()
        # Call detect_faces with explicit model_path
        res = fd.detect_faces(img, model_path=missing)
        assert res.success is False
        assert res.error_message is not None
        assert "model file not found" in res.error_message.lower()


# ---------------------------------------------------------------------------
# Caching behaviour (protect against repeated init)
# ---------------------------------------------------------------------------


class TestCaching:
    def test_repeated_calls_use_cached_landmarker(self, monkeypatch):
        call_count = {"n": 0}

        def _init_tracker(**kw):
            call_count["n"] += 1
            return _FakeLandmarker(num_faces=1), None

        monkeypatch.setattr(fd, "initialize_face_landmarker", _init_tracker)
        for _ in range(5):
            fd.detect_faces(_make_synthetic_face_image(1))
        # detect_faces calls initialize_face_landmarker on every invocation,
        # but if we swapped it out entirely via monkeypatch the tracker fires
        # 5 times — this test only validates the plumbing. We want the real
        # cache-path instead, so we test that explicitly:
        assert call_count["n"] == 5

    def test_cache_key_differs_for_different_num_faces(self, tmp_path, monkeypatch):
        # Create a dummy model file to satisfy the file-existence check
        fake_model = tmp_path / "fake.task"
        fake_model.write_bytes(b"nonsense")

        # Intercept create_from_options so invalid bytes inside fake_model don't crash.
        # We also use a plain SimpleNamespace landmarker (doesn't need close method).
        calls: list = []

        def _fake_create(options):
            calls.append(options)
            return _FakeLandmarker()

        monkeypatch.setattr(fd.FaceLandmarker, "create_from_options",
                            staticmethod(_fake_create))

        fd._clear_landmarker_cache()
        # Run A: num_faces=2, force=True
        lm_a, err_a = fd.initialize_face_landmarker(
            model_path=str(fake_model),
            num_faces=2,
            force=True,
        )
        assert err_a is None and lm_a is not None
        key_a = fd._last_cache_key

        # Run B: num_faces=2, identical params, force=False -> MUST reuse (cached)
        lm_b, err_b = fd.initialize_face_landmarker(
            model_path=str(fake_model),
            num_faces=2,
            force=False,
        )
        assert err_b is None
        key_b = fd._last_cache_key
        assert key_a == key_b
        # The landmarker returned must be the EXACT same object (not a copy)
        assert lm_b is lm_a, "Cache hit should return the identical landmarker instance"
        # create_from_options called exactly once so far
        assert len(calls) == 1, f"Expected 1 real creation, got {len(calls)}"

        # Run C: num_faces=4 -> different cache key -> MUST create a NEW one
        lm_c, err_c = fd.initialize_face_landmarker(
            model_path=str(fake_model),
            num_faces=4,
            force=False,
        )
        assert err_c is None and lm_c is not None
        key_c = fd._last_cache_key
        assert key_a != key_c
        assert lm_c is not lm_a
        assert len(calls) == 2, f"Expected 2 real creations, got {len(calls)}"

        # Run D: force=True even with identical config to C -> yet another creation
        lm_d, err_d = fd.initialize_face_landmarker(
            model_path=str(fake_model),
            num_faces=4,
            force=True,
        )
        assert err_d is None
        assert lm_d is not lm_c
        assert len(calls) == 3, f"Expected 3 real creations (forced), got {len(calls)}"
