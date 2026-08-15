"""
Face Detection & Landmark Extraction Service — Phase 12.

Uses the MediaPipe Tasks **Face Landmarker** model (`face_landmarker.task`) via
the modern Tasks Python API. The dependency direction is strictly:

    Streamlit UI → Service → MediaPipe (never the reverse)

so this module remains reusable for registration-time extraction, image
matching and video processing in later phases.

Public API (keep stable for downstream phases):
    initialize_face_landmarker(...)   -> cached reusable landmarker instance
    detect_faces(image, ...)          -> FaceDetectionResult
    extract_landmarks(image, ...)     -> list of per-face landmark lists
    get_face_count(image, ...)        -> int

Everything is pure functions operating on image data. No Streamlit imports.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image as PILImage

try:
    import mediapipe as mp
    from mediapipe import Image as MPImage, ImageFormat
    from mediapipe.tasks.python.core.base_options import BaseOptions
    from mediapipe.tasks.python.vision import (
        FaceLandmarker,
        FaceLandmarkerOptions,
        RunningMode,
    )
    MEDIAPIPE_AVAILABLE = True
    MEDIAPIPE_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover - import guard
    MEDIAPIPE_AVAILABLE = False
    MEDIAPIPE_IMPORT_ERROR = str(exc)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via arguments / config.settings)
# ---------------------------------------------------------------------------

# MediaPipe Face Landmarker supplies exactly 478 landmark points per face
# (the canonical MediaPipe face mesh topology).
EXPECTED_LANDMARKS_PER_FACE = 478

# Absolute max image dimension we will process. Anything larger is
# proportionally downscaled before being fed into MediaPipe to bound memory.
_MAX_IMAGE_DIMENSION = 1920

# ---------------------------------------------------------------------------
# Data classes (structured detection results — no MP internals leak out)
# ---------------------------------------------------------------------------


@dataclass
class FaceLandmark:
    """A single landmark point with X, Y, Z coordinates.

    Coordinates are in normalized pixel space:
        x in [0, 1] across image width (0 = left, 1 = right)
        y in [0, 1] across image height (0 = top, 1 = bottom)
        z is the relative depth with magnitude smaller for landmarks further
          from the face (same convention as MediaPipe).

    Index is preserved 0..N-1 so ordering matches MediaPipe directly —
    Phase 13 will flatten these into a single vector.
    """
    index: int
    x: float
    y: float
    z: float

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class DetectedFace:
    """One detected face with its landmarks + optional bounding box."""
    face_index: int  # 0-based index in the detection batch
    landmarks: List[FaceLandmark] = field(default_factory=list)
    # Bounding box (x, y, w, h) in pixel coordinates of the input image.
    # Computed from landmark min/max — kept in pixel space for easy drawing.
    bounding_box_pixels: Optional[Tuple[int, int, int, int]] = None
    # Presence score (confidence) reported by the landmarker for this face
    presence_score: Optional[float] = None

    @property
    def landmark_count(self) -> int:
        return len(self.landmarks)

    def landmarks_as_array(self) -> np.ndarray:
        """Return (N, 3) numpy array of [x, y, z] rows — not flattened."""
        if not self.landmarks:
            return np.zeros((0, 3), dtype=np.float32)
        arr = np.asarray(
            [(lm.x, lm.y, lm.z) for lm in self.landmarks],
            dtype=np.float32,
        )
        return arr


@dataclass
class FaceDetectionResult:
    """Structured output of detect_faces().

    No MediaPipe objects leak out; everything is plain Python / numpy.
    """
    success: bool
    num_faces: int = 0
    faces: List[DetectedFace] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    error_message: Optional[str] = None
    # Original image that was actually analysed (after pre-processing), useful
    # for overlay drawing. Always RGB uint8 numpy array, or None on failure.
    processed_image_rgb: Optional[np.ndarray] = None

    # Convenience accessors --------------------------------------------------
    @property
    def is_error(self) -> bool:
        return not self.success

    def landmarks_per_face(self) -> List[int]:
        return [f.landmark_count for f in self.faces]


# ---------------------------------------------------------------------------
# Module-level singleton cache for the landmarker.
#   - We want initialise-once-and-reuse behaviour (avoids heavy model reload)
#   - Tests can force re-init via _clear_landmarker_cache()
# ---------------------------------------------------------------------------

_landmarker_cache: Optional["FaceLandmarker"] = None
_last_cache_key: Optional[Tuple[str, int, float, float, float]] = None


def _clear_landmarker_cache() -> None:
    """Test helper: releases any cached landmarker."""
    global _landmarker_cache, _last_cache_key
    if _landmarker_cache is not None:
        try:
            _landmarker_cache.close()
        except Exception:
            pass
    _landmarker_cache = None
    _last_cache_key = None


# ---------------------------------------------------------------------------
# Image input normalisation (accept str path, PIL, numpy)
# ---------------------------------------------------------------------------


_ALLOWED_INPUT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _to_rgb_array(image: Any) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Convert a flexible image input to an (H, W, 3) uint8 RGB numpy array.

    Returns:
        (rgb_array_or_None, error_message_or_None)
    """
    if image is None:
        return None, "Input image is None."

    # --- File path (str) -------------------------------------------------
    if isinstance(image, str):
        path = image.strip()
        if not path:
            return None, "Empty image path provided."
        _, ext = os.path.splitext(path.lower())
        if ext and ext not in _ALLOWED_INPUT_EXTENSIONS:
            return None, (
                f"Unsupported image extension '{ext}'. "
                f"Allowed: {sorted(_ALLOWED_INPUT_EXTENSIONS)}."
            )
        if not os.path.isfile(path):
            return None, f"Image file not found: {path}"
        try:
            pil_img = PILImage.open(path).convert("RGB")
        except Exception as exc:
            return None, f"Failed to read image from path: {exc}"
        arr = np.asarray(pil_img, dtype=np.uint8)
        if arr.size == 0:
            return None, "Image file is empty (zero pixels)."
        return arr, None

    # --- PIL Image -------------------------------------------------------
    if isinstance(image, PILImage.Image):
        try:
            arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
        except Exception as exc:
            return None, f"Failed to convert PIL image to array: {exc}"
        if arr.size == 0:
            return None, "PIL image is empty (zero pixels)."
        return arr, None

    # --- Numpy array -----------------------------------------------------
    if isinstance(image, np.ndarray):
        if image.size == 0:
            return None, "Numpy image array is empty."
        if image.ndim != 3:
            return None, (
                f"Expected 3-channel HxWxC image array, got ndim={image.ndim}."
            )
        h, w, c = image.shape
        if c not in (1, 3, 4):
            return None, (
                f"Unsupported number of channels: {c}. Expected 1, 3 or 4."
            )
        try:
            if c == 1:
                gray = image.astype(np.uint8) if image.dtype != np.uint8 else image
                arr = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            elif c == 3:
                arr = image.astype(np.uint8) if image.dtype != np.uint8 else image.copy()
                # Heuristic: if values look like BGR OpenCV order we leave them;
                # MediaPipe expects SRGB. We document input should be RGB,
                # but handle both by assuming channel order is already fine.
            else:  # c == 4 (RGBA)
                base = image.astype(np.uint8) if image.dtype != np.uint8 else image
                arr = cv2.cvtColor(base, cv2.COLOR_RGBA2RGB)
        except Exception as exc:
            return None, f"Failed to normalise numpy image array: {exc}"
        if arr.size == 0:
            return None, "Image is empty after normalisation."
        return arr, None

    # --- Anything else ---------------------------------------------------
    return None, f"Unsupported image input type: {type(image).__name__}."


def _maybe_downscale(rgb: np.ndarray, max_dim: int = _MAX_IMAGE_DIMENSION) -> np.ndarray:
    """Downscale proportionally so the max side is <= max_dim.

    Preserves aspect ratio. Returns a view/copy uint8 RGB array.
    """
    h, w = rgb.shape[:2]
    largest = max(h, w)
    if largest <= max_dim:
        return rgb
    scale = max_dim / float(largest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# Core: landmarker initialisation (cached) + detection
# ---------------------------------------------------------------------------


def initialize_face_landmarker(
    model_path: Optional[str] = None,
    num_faces: Optional[int] = None,
    min_face_detection_confidence: Optional[float] = None,
    min_face_presence_confidence: Optional[float] = None,
    min_tracking_confidence: Optional[float] = None,
    force: bool = False,
) -> Tuple[Optional["FaceLandmarker"], Optional[str]]:
    """Initialise (and cache) a MediaPipe Face Landmarker instance.

    Uses a cache key of (model_path, num_faces, det_conf, pres_conf, trk_conf)
    so repeated calls with the same arguments are a cheap no-op unless
    ``force=True`` is passed.

    Returns:
        (landmarker_instance or None, error_message or None)
    """
    global _landmarker_cache, _last_cache_key

    if not MEDIAPIPE_AVAILABLE:
        return None, (
            "MediaPipe package is not available. "
            f"Import error: {MEDIAPIPE_IMPORT_ERROR}"
        )

    # --- Resolve defaults ------------------------------------------------
    try:
        from backend.config import settings as _cfg
        default_path = _cfg.MEDIAPIPE_MODEL_PATH
        default_num = _cfg.MEDIAPIPE_NUM_FACES
        default_det = _cfg.MEDIAPIPE_MIN_DETECTION_CONF
        default_pres = _cfg.MEDIAPIPE_MIN_PRESENCE_CONF
        default_trk = _cfg.MEDIAPIPE_MIN_TRACKING_CONF
    except Exception:
        # Fallback (tests / headless environments)
        default_path = os.path.join("data", "models", "face_landmarker.task")
        default_num = 5
        default_det = 0.5
        default_pres = 0.5
        default_trk = 0.5

    resolved_path = model_path if model_path else default_path
    resolved_num = int(num_faces) if num_faces is not None else int(default_num)
    resolved_det = float(min_face_detection_confidence) if min_face_detection_confidence is not None else float(default_det)
    resolved_pres = float(min_face_presence_confidence) if min_face_presence_confidence is not None else float(default_pres)
    resolved_trk = float(min_tracking_confidence) if min_tracking_confidence is not None else float(default_trk)

    cache_key = (
        os.path.abspath(resolved_path) if os.path.isabs(resolved_path) or os.path.exists(resolved_path) else resolved_path,
        resolved_num,
        round(resolved_det, 6),
        round(resolved_pres, 6),
        round(resolved_trk, 6),
    )

    if (
        not force
        and _landmarker_cache is not None
        and _last_cache_key == cache_key
    ):
        return _landmarker_cache, None

    # --- Validate model file presence before we let MP try to open it ----
    abs_model_path = os.path.abspath(resolved_path)
    if not os.path.isfile(abs_model_path):
        # Clear any stale cached instance, this configuration is broken
        _clear_landmarker_cache()
        msg = (
            f"MediaPipe face landmarker model file not found at: "
            f"{abs_model_path}. "
            f"Download it from Google's MediaPipe Model Garden and place it "
            f"at the configured MEDIAPIPE_MODEL_PATH. See .env.example."
        )
        return None, msg

    # --- Build options + landmarker --------------------------------------
    try:
        base_options = BaseOptions(model_asset_path=abs_model_path)
        options = FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=RunningMode.IMAGE,
            num_faces=max(1, resolved_num),
            min_face_detection_confidence=max(0.0, min(1.0, resolved_det)),
            min_face_presence_confidence=max(0.0, min(1.0, resolved_pres)),
            min_tracking_confidence=max(0.0, min(1.0, resolved_trk)),
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        landmarker = FaceLandmarker.create_from_options(options)
    except Exception as exc:
        _clear_landmarker_cache()
        return None, f"Failed to initialise MediaPipe Face Landmarker: {exc}"

    _landmarker_cache = landmarker
    _last_cache_key = cache_key
    return landmarker, None


# ---------------------------------------------------------------------------
# Helpers to convert the MP FaceLandmarkerResult into our plain structures
# ---------------------------------------------------------------------------


def _extract_one_face_landmarks(
    mp_normalized_landmarks,
    face_index: int,
    image_width: int,
    image_height: int,
    presence_score: Optional[float],
) -> DetectedFace:
    """Build a DetectedFace from one normalized-landmark list."""
    landmarks: List[FaceLandmark] = []
    xs: List[float] = []
    ys: List[float] = []

    for idx, lm in enumerate(mp_normalized_landmarks):
        # MediaPipe NormalizedLandmark has .x .y .z (and sometimes .visibility)
        x = float(getattr(lm, "x", 0.0))
        y = float(getattr(lm, "y", 0.0))
        z = float(getattr(lm, "z", 0.0))
        landmarks.append(FaceLandmark(index=idx, x=x, y=y, z=z))
        xs.append(x)
        ys.append(y)

    bbox = None
    if xs and ys:
        x_min = max(0.0, min(xs))
        y_min = max(0.0, min(ys))
        x_max = min(1.0, max(xs))
        y_max = min(1.0, max(ys))
        px = int(round(x_min * image_width))
        py = int(round(y_min * image_height))
        pw = max(1, int(round((x_max - x_min) * image_width)))
        ph = max(1, int(round((y_max - y_min) * image_height)))
        bbox = (px, py, pw, ph)

    return DetectedFace(
        face_index=face_index,
        landmarks=landmarks,
        bounding_box_pixels=bbox,
        presence_score=presence_score,
    )


def _build_result_from_mp(
    mp_result,
    processed_image_rgb: np.ndarray,
) -> FaceDetectionResult:
    h, w = processed_image_rgb.shape[:2]
    faces: List[DetectedFace] = []

    if mp_result is None:
        return FaceDetectionResult(
            success=True,
            num_faces=0,
            faces=[],
            image_width=w,
            image_height=h,
            processed_image_rgb=processed_image_rgb,
        )

    mp_landmarks_list = getattr(mp_result, "face_landmarks", None) or []
    # Presence scores are an optional parallel list in newer MP builds
    presence_list = getattr(mp_result, "face_presence_scores", None) or []

    for idx, mp_landmarks in enumerate(mp_landmarks_list):
        pres: Optional[float] = None
        if idx < len(presence_list):
            try:
                pres = float(presence_list[idx])
            except Exception:
                pres = None
        faces.append(
            _extract_one_face_landmarks(
                mp_landmarks,
                face_index=idx,
                image_width=w,
                image_height=h,
                presence_score=pres,
            )
        )

    return FaceDetectionResult(
        success=True,
        num_faces=len(faces),
        faces=faces,
        image_width=w,
        image_height=h,
        processed_image_rgb=processed_image_rgb,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_faces(
    image: Union[str, np.ndarray, "PILImage.Image", None],
    *,
    model_path: Optional[str] = None,
    num_faces: Optional[int] = None,
    min_face_detection_confidence: Optional[float] = None,
    min_face_presence_confidence: Optional[float] = None,
    min_tracking_confidence: Optional[float] = None,
    max_image_dimension: int = _MAX_IMAGE_DIMENSION,
) -> FaceDetectionResult:
    """Run MediaPipe Face Landmarker on ``image``.

    Args:
        image: File path (str), PIL Image, or numpy array (HxWxC uint8).
        model_path / num_faces / min_*_confidence: forwarded to
            ``initialize_face_landmarker``; None → use Settings defaults.
        max_image_dimension: images with height/width larger than this are
            downscaled proportionally before analysis.

    Returns:
        FaceDetectionResult — always a concrete instance, never None.
        On failure the result will have ``success=False`` and a non-empty
        ``error_message``.
    """
    # 1. Normalise flexible input to RGB uint8 numpy array
    rgb_array, err = _to_rgb_array(image)
    if err is not None:
        return FaceDetectionResult(success=False, error_message=err)

    # 2. Bound memory usage for very large images
    try:
        rgb_processed = _maybe_downscale(rgb_array, max_dim=max_image_dimension)
    except Exception as exc:
        return FaceDetectionResult(
            success=False,
            error_message=f"Failed during image preprocessing: {exc}",
        )

    # 3. Get or create a cached landmarker
    landmarker, init_err = initialize_face_landmarker(
        model_path=model_path,
        num_faces=num_faces,
        min_face_detection_confidence=min_face_detection_confidence,
        min_face_presence_confidence=min_face_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )
    if init_err is not None or landmarker is None:
        h, w = rgb_processed.shape[:2]
        return FaceDetectionResult(
            success=False,
            num_faces=0,
            image_width=w,
            image_height=h,
            error_message=init_err or "Face landmarker failed to initialise.",
            processed_image_rgb=rgb_processed,
        )

    # 4. Wrap image into MediaPipe's SRGB Image + run detect
    try:
        mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb_processed)
    except Exception as exc:
        h, w = rgb_processed.shape[:2]
        return FaceDetectionResult(
            success=False,
            num_faces=0,
            image_width=w,
            image_height=h,
            error_message=f"Failed to build MediaPipe Image: {exc}",
            processed_image_rgb=rgb_processed,
        )

    try:
        mp_result = landmarker.detect(mp_image)
    except Exception as exc:
        h, w = rgb_processed.shape[:2]
        return FaceDetectionResult(
            success=False,
            num_faces=0,
            image_width=w,
            image_height=h,
            error_message=f"MediaPipe face detection error: {exc}",
            processed_image_rgb=rgb_processed,
        )

    # 5. Convert MP result to our pure-Python structures
    return _build_result_from_mp(mp_result, rgb_processed)


def extract_landmarks(
    image: Union[str, np.ndarray, "PILImage.Image", None],
    **kwargs: Any,
) -> List[List[Tuple[float, float, float]]]:
    """Lightweight convenience: returns landmarks only.

    For every detected face, returns a list of ``(x, y, z)`` tuples (length
    equals the number of landmarks on that face). If detection fails, the
    return is an empty list.
    """
    result = detect_faces(image, **kwargs)
    if not result.success:
        return []
    return [
        [lm.as_tuple() for lm in face.landmarks]
        for face in result.faces
    ]


def get_face_count(
    image: Union[str, np.ndarray, "PILImage.Image", None],
    **kwargs: Any,
) -> int:
    """Convenience: return just the number of detected faces, or 0 on error."""
    result = detect_faces(image, **kwargs)
    return result.num_faces if result.success else 0


# ---------------------------------------------------------------------------
# Version / meta helpers (useful for reports + tests)
# ---------------------------------------------------------------------------


def get_mediapipe_info() -> dict:
    """Return a small dict describing the MediaPipe runtime environment."""
    info = {
        "mediapipe_available": MEDIAPIPE_AVAILABLE,
        "mediapipe_import_error": MEDIAPIPE_IMPORT_ERROR,
        "mediapipe_version": None,
        "expected_landmarks_per_face": EXPECTED_LANDMARKS_PER_FACE,
        "max_image_dimension": _MAX_IMAGE_DIMENSION,
    }
    if MEDIAPIPE_AVAILABLE:
        try:
            info["mediapipe_version"] = mp.__version__
        except Exception:
            info["mediapipe_version"] = None
    return info
