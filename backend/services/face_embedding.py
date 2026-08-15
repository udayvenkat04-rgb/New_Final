"""
Face Vector / Embedding Generation Service — Phase 13.

Purpose
-------
Convert the structured MediaPipe face landmarks produced by the Phase 12
``services.face_detection`` module into a *single deterministic 1,404-D*
NumPy vector per detected face.

Pipeline (single face)
----------------------
    landmarks (list of FaceLandmark, N=468)
       ↓  validate: landmark count / XYZ presence / finite values
    raw (N, 3) float32 array [x, y, z] rows
       ↓  Normalize (deterministic — documented below)
    normed (N, 3) float32 array
       ↓  Flatten in order: X1, Y1, Z1, X2, Y2, Z2, …, X468, Y468, Z468
    vector shape (1404,)  dtype float32

This module keeps a *strict* dependency direction:

    Streamlit UI → Face Detection → Face Embedding → NumPy vector

It never imports from Streamlit, MongoDB, KNN, email, video, or map modules
so it stays reusable by:
  * case registration (save missing-person vectors)
  * image matching (query vector vs known index)
  * video frame matching later on

Normalization (deterministic, documented)
-----------------------------------------
1. **Translation invariance**
     Subtract the mean landmark position from every landmark. The face is now
     centered at the origin regardless of where it appears in the frame.

       μx = mean(x_i),   μy = mean(y_i),   μz = mean(z_i)
       x'_i = x_i - μx
       y'_i = y_i - μy
       z'_i = z_i - μz

2. **Scale invariance**
     Compute R = the Euclidean distance *from the mean center* of the single
     farthest landmark in the (x, y) plane (the "facial radius" in screen
     space). Divide x' and y' by R so the face always lives inside a unit
     circle of radius ≈ 1 in the image plane, regardless of subject
     distance or image resolution.

     z (depth) is scaled by the *same* R so the relative 3-D proportions of
     the mesh are preserved — a very long nose stays a very long nose after
     scaling.

       R = max_over_i( sqrt(x'_i² + y'_i²) )
       X_i = x'_i / R
       Y_i = y'_i / R
       Z_i = z'_i / R

   - R is *never allowed to hit 0* (degenerate face) — we fail loudly.
   - After normalization, max sqrt(X_i² + Y_i²) = 1.0 exactly (for the
     farthest landmark).

3. **Ordering**
     The landmarker-index ordering is preserved exactly. Phase 12 guarantees
     FaceLandmark.index == the enumeration index, so iterating the list in
     list order yields deterministic point 0..N-1.  We never sort or
     otherwise shuffle points.

This is *identical* when applied to registration images and to
query/sighting images, so embeddings live in the same coordinate space.

Vector layout
-------------
After normalization, we flatten the (N, 3) array in row-major "XYZ per
landmark" order:

    [ X0, Y0, Z0,  X1, Y1, Z1,  … ,  X(N-1), Y(N-1), Z(N-1) ]

The target layout is **not** [all X | all Y | all Z] — we intentionally
keep each landmark's coordinates tightly co-located so Phase 14 KNN distance
computations reflect per-landmark geometry naturally.

Landmark count configuration
----------------------------
The canonical Phase 13 target is 468 landmarks → 1,404 dimensions.  To keep
the service safe against model upgrades we:

  * Default to 468 landmarks (1,404 dims).
  * Allow the caller / config to override ``expected_landmarks``.
  * NEVER silently truncate or pad — if the actual landmark count does not
    match ``expected_landmarks`` we raise ``LandmarkCountMismatchError`` with
    a message that includes both numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from backend.services.face_detection import (
    DetectedFace,
    FaceDetectionResult,
    FaceLandmark,
)

# ---------------------------------------------------------------------------
# Canonical defaults — exactly match Phase 13 target of 1,404 dims.
# ---------------------------------------------------------------------------

DEFAULT_LANDMARKS_PER_FACE: int = 468
DEFAULT_COORDS_PER_LANDMARK: int = 3  # X, Y, Z
DEFAULT_VECTOR_DIM: int = DEFAULT_LANDMARKS_PER_FACE * DEFAULT_COORDS_PER_LANDMARK  # 1404
DEFAULT_VECTOR_DTYPE = np.float32


# ---------------------------------------------------------------------------
# Custom, clearly-named application-level exceptions — so callers can react
# without parsing free-form error strings.
# ---------------------------------------------------------------------------


class FaceEmbeddingError(Exception):
    """Base for all exceptions raised by this module."""


class LandmarkValidationError(FaceEmbeddingError):
    """Raised when the landmark data is malformed (missing coords, non-finite)."""


class LandmarkCountMismatchError(LandmarkValidationError):
    """Raised when actual landmark count != the configured expected count.

    Attributes
    ----------
    expected : int
    actual : int
    """

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Landmark count mismatch: expected {expected} landmarks "
            f"(→ {expected * DEFAULT_COORDS_PER_LANDMARK}D vector), "
            f"but got {actual}. Refusing to pad or truncate silently. "
            f"Adjust DEFAULT_LANDMARKS_PER_FACE / the expected_landmarks "
            f"argument if you intentionally changed the MediaPipe model."
        )


class FaceVectorValidationError(FaceEmbeddingError):
    """Raised when post-generation vector validation fails."""


class DegenerateFaceError(FaceEmbeddingError):
    """Raised when landmarks collapse to a single point (scale factor = 0)."""


class NoFacesDetectedError(FaceEmbeddingError):
    """Raised when a FaceDetectionResult contains 0 faces but a vector was
    requested."""


class FaceIndexOutOfRangeError(FaceEmbeddingError, IndexError):
    """Raised when ``face_index`` points to a non-existent face."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VectorValidationReport:
    """Structured output of :func:`validate_face_vector`."""
    is_valid: bool
    shape: Tuple[int, ...]
    expected_shape: Tuple[int, ...]
    dtype: Any
    has_nan: bool
    has_inf: bool
    all_finite: bool
    expected_dtype_match: bool
    errors: Tuple[str, ...]

    def __str__(self) -> str:  # pragma: no cover - debug formatting
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"<VectorValidationReport {status}: shape={self.shape}, "
            f"dtype={self.dtype}, NaN={self.has_nan}, Inf={self.has_inf}, "
            f"errors={list(self.errors)}>"
        )


def _iter_xyz_from_landmarks(
    landmarks: Sequence[Any],
) -> Iterable[Tuple[float, float, float]]:
    """Yield ``(x, y, z)`` tuples from *any* landmark-shaped iterable.

    Supports:
      * a list of Phase 12 ``FaceLandmark`` dataclass instances  (preferred)
      * a list of tuples / lists ``[x, y, z]``
      * an (N, 3) numpy array
    The goal is to keep :func:`normalize_landmarks` / :func:`landmarks_to_vector`
    callable with both Phase 12 output and arbitrary test fixtures.
    """
    if isinstance(landmarks, np.ndarray):
        arr = np.asarray(landmarks)
        if arr.ndim != 2 or arr.shape[1] != DEFAULT_COORDS_PER_LANDMARK:
            raise LandmarkValidationError(
                f"Landmark numpy array must be shape (N, 3), got {arr.shape}."
            )
        for row in arr:
            yield float(row[0]), float(row[1]), float(row[2])
        return

    for idx, lm in enumerate(landmarks):
        # Phase 12 FaceLandmark dataclass (preferred)
        if isinstance(lm, FaceLandmark):
            yield float(lm.x), float(lm.y), float(lm.z)
            continue
        # Tuple / list of 3 values
        if isinstance(lm, (tuple, list)) and len(lm) == 3:
            x, y, z = lm
            yield float(x), float(y), float(z)
            continue
        # Dict with x/y/z keys
        if isinstance(lm, dict) and {"x", "y", "z"}.issubset(lm.keys()):
            yield float(lm["x"]), float(lm["y"]), float(lm["z"])
            continue
        # Attribute object (SimpleNamespace etc.)
        if hasattr(lm, "x") and hasattr(lm, "y") and hasattr(lm, "z"):
            yield float(getattr(lm, "x")), float(getattr(lm, "y")), float(getattr(lm, "z"))
            continue
        raise LandmarkValidationError(
            f"Landmark at index {idx} does not expose X, Y, Z coordinates. "
            f"Got: {type(lm).__name__}."
        )


def _validate_raw_landmarks(
    raw_rows: np.ndarray,
    expected_landmarks: Optional[int],
) -> None:
    """Validate the (N, 3) float array before normalization.

    Raises
    ------
    LandmarkValidationError
        If the array has the wrong shape, contains non-finite values, or has
        a landmark count that does not match ``expected_landmarks``.
    LandmarkCountMismatchError
        Subtype of LandmarkValidationError raised specifically on count
        mismatch.
    """
    if raw_rows.size == 0:
        raise LandmarkValidationError(
            "Empty landmark input — cannot build a face vector."
        )
    if raw_rows.ndim != 2 or raw_rows.shape[1] != DEFAULT_COORDS_PER_LANDMARK:
        raise LandmarkValidationError(
            f"Landmarks must form an (N, 3) matrix, got shape {raw_rows.shape}."
        )
    actual = int(raw_rows.shape[0])
    if expected_landmarks is not None and actual != int(expected_landmarks):
        raise LandmarkCountMismatchError(int(expected_landmarks), actual)

    if not np.all(np.isfinite(raw_rows)):
        n_bad = int(np.sum(~np.isfinite(raw_rows)))
        raise LandmarkValidationError(
            f"Landmark coordinates contain {n_bad} non-finite values "
            f"(NaN / Inf). Refusing to generate a vector."
        )


# ---------------------------------------------------------------------------
# Core pure functions (no caches, no globals, fully deterministic)
# ---------------------------------------------------------------------------


def normalize_landmarks(
    landmarks: Sequence[Any],
    *,
    expected_landmarks: Optional[int] = DEFAULT_LANDMARKS_PER_FACE,
) -> np.ndarray:
    """Normalize raw landmarks into a translation- and scale-invariant (N,3) array.

    See the module docstring for the exact normalization algorithm.

    Parameters
    ----------
    landmarks:
        Any shape supported by :func:`_iter_xyz_from_landmarks`.
    expected_landmarks:
        The mandatory landmark count, or ``None`` to accept any N (strongly
        discouraged — defaults to :data:`DEFAULT_LANDMARKS_PER_FACE` = 468
        so we get a 1,404-D vector downstream).

    Returns
    -------
    np.ndarray
        shape ``(N, 3)``, dtype ``float32``, after mean-centering +
        farthest-landmark-in-xy-plane scaling.

    Raises
    ------
    LandmarkValidationError
        Malformed / empty / non-finite landmarks.
    LandmarkCountMismatchError
        Actual N != ``expected_landmarks``.
    DegenerateFaceError
        All landmarks collapsed to the same XY point (scale factor = 0).
    """
    # Materialize the heterogeneous input into a homogeneous float32 matrix
    rows = list(_iter_xyz_from_landmarks(landmarks))
    if len(rows) == 0:
        raise LandmarkValidationError(
            "Empty landmark input — cannot normalize a face vector."
        )
    raw = np.asarray(rows, dtype=DEFAULT_VECTOR_DTYPE)  # shape (N, 3)

    _validate_raw_landmarks(raw, expected_landmarks)

    # 1) Translation invariance — mean-center
    mean = raw.mean(axis=0)  # shape (3,)
    centered = raw - mean

    # 2) Scale invariance — divide by the xy-plane radius to the farthest point
    xy_radii = np.sqrt(centered[:, 0] ** 2 + centered[:, 1] ** 2)
    scale = float(xy_radii.max()) if xy_radii.size > 0 else 0.0
    if scale <= 0.0:
        raise DegenerateFaceError(
            "All landmarks collapsed to a single point in the XY plane "
            "(scale factor = 0). Cannot build a normalized face vector."
        )
    normed = centered / scale

    # Ensure final dtype is exactly float32 so downstream math is consistent
    return np.asarray(normed, dtype=DEFAULT_VECTOR_DTYPE)


def landmarks_to_vector(
    normalized_landmarks: np.ndarray,
    *,
    expected_landmarks: Optional[int] = DEFAULT_LANDMARKS_PER_FACE,
) -> np.ndarray:
    """Flatten a normalized (N, 3) landmark matrix into a 1-D vector.

    Order is *landmark-major*: ``[X0, Y0, Z0, X1, Y1, Z1, …]``.
    """
    if not isinstance(normalized_landmarks, np.ndarray):
        raise LandmarkValidationError(
            f"landmarks_to_vector expects a numpy ndarray, got "
            f"{type(normalized_landmarks).__name__}."
        )

    if normalized_landmarks.ndim != 2 or normalized_landmarks.shape[1] != DEFAULT_COORDS_PER_LANDMARK:
        raise LandmarkValidationError(
            f"Normalized landmarks must be shape (N, 3), got "
            f"{normalized_landmarks.shape}."
        )

    actual = int(normalized_landmarks.shape[0])
    if expected_landmarks is not None and actual != int(expected_landmarks):
        raise LandmarkCountMismatchError(int(expected_landmarks), actual)

    # Preserving float32: reshape with C order so the (row-major) order becomes
    # X0, Y0, Z0, X1, Y1, Z1, … — this is deterministic.
    flat = normalized_landmarks.astype(DEFAULT_VECTOR_DTYPE, copy=False).reshape(-1, order="C")
    expected_dim = actual * DEFAULT_COORDS_PER_LANDMARK
    if flat.shape[0] != expected_dim:
        raise FaceVectorValidationError(
            f"Flattened vector has {flat.shape[0]} elements but expected "
            f"{expected_dim} (landmark-major reshape failed)."
        )
    return flat


def generate_face_vector(
    face: Union[Sequence[Any], DetectedFace, np.ndarray],
    *,
    expected_landmarks: Optional[int] = DEFAULT_LANDMARKS_PER_FACE,
    validate: bool = True,
) -> np.ndarray:
    """Full pipeline: landmarks → normalized (N,3) → 1,404-D float32 vector.

    Parameters
    ----------
    face:
        Any one of:
          * a Phase 12 ``DetectedFace`` instance (recommended — uses its
            ``landmarks`` list directly)
          * an iterable of landmark objects (``FaceLandmark`` / tuples / dicts)
          * an (N, 3) numpy array
    expected_landmarks:
        Mandatory landmark count. Default 468 → 1,404D vector.
    validate:
        When True (default), also run :func:`validate_face_vector` on the
        final vector.

    Returns
    -------
    np.ndarray, shape ``(expected_landmarks * 3,)``, dtype float32
    """
    # Unwrap DetectedFace -> landmarks list
    if isinstance(face, DetectedFace):
        landmarks = face.landmarks
    else:
        landmarks = face

    normed = normalize_landmarks(landmarks, expected_landmarks=expected_landmarks)
    vector = landmarks_to_vector(normed, expected_landmarks=expected_landmarks)

    if validate:
        report = validate_face_vector(
            vector,
            expected_dim=(
                int(expected_landmarks) * DEFAULT_COORDS_PER_LANDMARK
                if expected_landmarks is not None
                else None
            ),
        )
        if not report.is_valid:
            raise FaceVectorValidationError(
                "Generated vector failed validation: " + "; ".join(report.errors)
            )
    return vector


def validate_face_vector(
    vector: np.ndarray,
    *,
    expected_dim: Optional[int] = DEFAULT_VECTOR_DIM,
) -> VectorValidationReport:
    """Validate the final face vector numerically.

    Reports on:
      * exact shape match (``(expected_dim,)``)
      * dtype numeric + ideally float32
      * absence of NaN / Inf values (``np.isfinite``)
    """
    errors: List[str] = []
    expected_shape = (int(expected_dim),) if expected_dim is not None else tuple()

    if not isinstance(vector, np.ndarray):
        return VectorValidationReport(
            is_valid=False,
            shape=(),
            expected_shape=expected_shape,
            dtype=None,
            has_nan=True,
            has_inf=True,
            all_finite=False,
            expected_dtype_match=False,
            errors=(
                f"validate_face_vector expects a numpy ndarray, got "
                f"{type(vector).__name__}.",
            ),
        )

    shape = tuple(vector.shape)
    dtype = vector.dtype

    if expected_dim is not None and shape != expected_shape:
        errors.append(
            f"Shape mismatch: expected {expected_shape}, got {shape}."
        )
    elif vector.ndim != 1:
        errors.append(
            f"Vector must be 1-D, got ndim={vector.ndim}, shape={shape}."
        )

    # Numeric dtype — must check before np.isnan / np.isinf / np.isfinite
    # because those ufuncs raise TypeError on non-numeric dtypes (e.g. str).
    is_numeric_dtype = bool(np.issubdtype(dtype, np.number))
    if not is_numeric_dtype:
        errors.append(f"Vector dtype {dtype} is not numeric.")
    expected_dtype_match = (dtype == DEFAULT_VECTOR_DTYPE)
    if expected_dim is not None and not expected_dtype_match:
        errors.append(
            f"Vector dtype {dtype} differs from the canonical "
            f"{DEFAULT_VECTOR_DTYPE.__name__}."
        )

    if is_numeric_dtype and vector.size > 0:
        has_nan = bool(np.isnan(vector).any())
        has_inf = bool(np.isinf(vector).any())
        all_finite = bool(np.isfinite(vector).all())
    else:
        has_nan = False
        has_inf = False
        all_finite = False
    if has_nan:
        errors.append("Vector contains NaN values.")
    if has_inf:
        errors.append("Vector contains Inf values.")

    is_valid = (len(errors) == 0)
    return VectorValidationReport(
        is_valid=is_valid,
        shape=shape,
        expected_shape=expected_shape,
        dtype=dtype,
        has_nan=has_nan,
        has_inf=has_inf,
        all_finite=all_finite,
        expected_dtype_match=expected_dtype_match,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Multi-face helpers — choose which face to vectorize
# ---------------------------------------------------------------------------


def generate_vectors_for_all_faces(
    result: FaceDetectionResult,
    *,
    expected_landmarks: Optional[int] = DEFAULT_LANDMARKS_PER_FACE,
) -> List[np.ndarray]:
    """Given a Phase 12 ``FaceDetectionResult``, produce one vector per face.

    Raises
    ------
    FaceEmbeddingError (subtype)
        If detection failed, or if any face has malformed landmarks.
    NoFacesDetectedError
        If the detection contains 0 faces.
    """
    if not isinstance(result, FaceDetectionResult):
        raise FaceEmbeddingError(
            f"generate_vectors_for_all_faces expects a FaceDetectionResult, "
            f"got {type(result).__name__}."
        )
    if not result.success:
        raise FaceEmbeddingError(
            "Refusing to generate face vectors from a failed detection: "
            + (result.error_message or "unknown detection error.")
        )
    if result.num_faces == 0:
        raise NoFacesDetectedError(
            "FaceDetectionResult contains 0 faces; cannot produce vectors."
        )
    vectors: List[np.ndarray] = []
    for idx, face in enumerate(result.faces):
        try:
            vectors.append(
                generate_face_vector(face, expected_landmarks=expected_landmarks)
            )
        except FaceEmbeddingError as exc:
            raise FaceEmbeddingError(
                f"Failed to generate vector for face_index={idx}: {exc}"
            ) from exc
    return vectors


def generate_face_vector_by_index(
    result: FaceDetectionResult,
    face_index: int,
    *,
    expected_landmarks: Optional[int] = DEFAULT_LANDMARKS_PER_FACE,
) -> np.ndarray:
    """Select exactly one face from a detection result and vectorize it.

    Raises
    ------
    FaceIndexOutOfRangeError
        If ``face_index`` is out of range. The caller (UI / service) decides
        which face to pick; we never silently default to ``face_index=0``.
    """
    if not isinstance(result, FaceDetectionResult):
        raise FaceEmbeddingError(
            f"generate_face_vector_by_index expects a FaceDetectionResult, "
            f"got {type(result).__name__}."
        )
    if not result.success:
        raise FaceEmbeddingError(
            "Refusing to select a face from a failed detection."
        )
    if result.num_faces == 0:
        raise NoFacesDetectedError(
            "FaceDetectionResult contains 0 faces; cannot pick a face_index."
        )
    if not (0 <= int(face_index) < result.num_faces):
        raise FaceIndexOutOfRangeError(
            f"face_index={face_index} is out of range. Detection contains "
            f"{result.num_faces} face(s) (valid indices: "
            f"0…{result.num_faces - 1})."
        )
    face = result.faces[int(face_index)]
    return generate_face_vector(face, expected_landmarks=expected_landmarks)


# ---------------------------------------------------------------------------
# Meta helpers (for reporting / debug pages)
# ---------------------------------------------------------------------------


def get_embedding_config() -> dict:
    return {
        "default_landmarks_per_face": DEFAULT_LANDMARKS_PER_FACE,
        "default_coords_per_landmark": DEFAULT_COORDS_PER_LANDMARK,
        "default_vector_dim": DEFAULT_VECTOR_DIM,
        "default_vector_dtype": str(DEFAULT_VECTOR_DTYPE.__name__),
        "normalization": (
            "1) mean-centre all landmarks (translation invariant); "
            "2) divide x', y', z' by the maximum XY-plane distance from the "
            "mean centre (scale invariant); "
            "3) flatten in landmark-major order: X0,Y0,Z0,…,XN-1,YN-1,ZN-1."
        ),
        "refuses_to_truncate_or_pad": True,
    }


# Backward-compatibility alias for UI modules importing get_face_embedding directly
get_face_embedding = generate_face_vector
