"""
Visualization helpers for the MediaPipe Face Detection service (Phase 12).

Draws clean face bounding boxes + face-mesh landmark overlays on top of the
analysed image. Returns a PIL Image ready for display in Streamlit or saving
to disk.

Pure utilities — no Streamlit imports. Keep this layer separate so the core
service does not depend on it.
"""
from __future__ import annotations

import math
from typing import Optional

import cv2
import numpy as np
from PIL import Image as PILImage

from backend.services.face_detection import (
    DetectedFace,
    FaceDetectionResult,
)

# Default colours per face index (cycles after 8)
_FACE_PALETTE = [
    (16, 185, 129),   # emerald-500
    (59, 130, 246),   # blue-500
    (245, 158, 11),   # amber-500
    (239, 68, 68),    # red-500
    (168, 85, 247),   # purple-500
    (236, 72, 153),   # pink-500
    (34, 197, 94),    # green-500
    (14, 165, 233),   # sky-500
]


def _colour_for_face(face_index: int) -> tuple:
    return _FACE_PALETTE[int(face_index) % len(_FACE_PALETTE)]


def _landmark_to_pixel(lm_x: float, lm_y: float, width: int, height: int):
    x = int(round(max(0.0, min(1.0, lm_x)) * (width - 1)))
    y = int(round(max(0.0, min(1.0, lm_y)) * (height - 1)))
    return x, y


def draw_face_detection_overlay(
    result: FaceDetectionResult,
    *,
    source_image: Optional[np.ndarray] = None,
    draw_bounding_box: bool = True,
    draw_landmarks: bool = True,
    landmark_radius: int = 1,
    draw_face_index_label: bool = True,
) -> Optional[PILImage.Image]:
    """Render a FaceDetectionResult overlay on top of the analysed image.

    Args:
        result: The structured detection result produced by ``detect_faces``.
        source_image: Optional override for the base image to draw on. If
            ``None``, ``result.processed_image_rgb`` is used.
        draw_bounding_box: Whether to draw a rectangle around each face.
        draw_landmarks: Whether to draw small circles at each landmark point.
        landmark_radius: Pixel radius of each landmark dot.
        draw_face_index_label: Whether to draw a small label "Face N" above
            each bounding box.

    Returns:
        PIL RGB Image with overlay drawn, or ``None`` if no image was
        available (e.g. detection failed with no processed_image_rgb).
    """
    # Determine the base image
    base = None
    if source_image is not None and isinstance(source_image, np.ndarray):
        if source_image.ndim == 3 and source_image.shape[2] in (1, 3, 4):
            if source_image.shape[2] == 1:
                base = cv2.cvtColor(source_image, cv2.COLOR_GRAY2RGB)
            elif source_image.shape[2] == 4:
                base = cv2.cvtColor(source_image, cv2.COLOR_RGBA2RGB)
            else:
                base = source_image.copy()
    if base is None:
        if result.processed_image_rgb is None:
            return None
        base = result.processed_image_rgb.copy()

    if base.dtype != np.uint8:
        base = np.clip(base, 0, 255).astype(np.uint8)

    h, w = base.shape[:2]

    # Respect image dimensions from the result, fall back to actual image
    out_w = result.image_width or w
    out_h = result.image_height or h
    if (out_w, out_h) != (w, h):
        base = cv2.resize(base, (out_w, out_h), interpolation=cv2.INTER_AREA)

    # Convert to BGR for OpenCV drawing, then back at the end
    canvas = cv2.cvtColor(base, cv2.COLOR_RGB2BGR)

    for face in result.faces:
        colour_bgr = tuple(int(c) for c in reversed(_colour_for_face(face.face_index)))

        # 1) Bounding box
        if draw_bounding_box and face.bounding_box_pixels is not None:
            x, y, bw, bh = face.bounding_box_pixels
            x = max(0, min(x, out_w - 1))
            y = max(0, min(y, out_h - 1))
            bw = max(1, min(bw, out_w - x))
            bh = max(1, min(bh, out_h - y))
            # Outer box (thick + colourful) + thin inner highlight
            cv2.rectangle(canvas, (x, y), (x + bw, y + bh), colour_bgr, 2, lineType=cv2.LINE_AA)
            # Label box
            if draw_face_index_label:
                label = f"Face {face.face_index}"
                if face.presence_score is not None:
                    label += f" ({face.presence_score:.2f})"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                lx = x
                ly = max(0, y - th - 8)
                cv2.rectangle(
                    canvas,
                    (lx, ly),
                    (lx + tw + 8, ly + th + 6),
                    colour_bgr,
                    thickness=-1,
                )
                cv2.putText(
                    canvas,
                    label,
                    (lx + 4, ly + th + 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

        # 2) Landmark dots
        if draw_landmarks:
            for lm in face.landmarks:
                px, py = _landmark_to_pixel(lm.x, lm.y, out_w, out_h)
                cv2.circle(
                    canvas,
                    (px, py),
                    max(1, int(landmark_radius)),
                    colour_bgr,
                    thickness=-1,
                    lineType=cv2.LINE_AA,
                )

    final_bgr = canvas
    final_rgb = cv2.cvtColor(final_bgr, cv2.COLOR_BGR2RGB)
    return PILImage.fromarray(final_rgb)


def summarise_detection(result: FaceDetectionResult) -> str:
    """Return a short, human-readable summary of a detection result."""
    if not result.success:
        return f"Detection FAILED: {result.error_message or 'unknown error'}"
    if result.num_faces == 0:
        return "Detection OK: no faces found in image "
    counts = result.landmarks_per_face()
    parts = [f"Face {i}: {c} landmarks" for i, c in enumerate(counts)]
    dims = f"{result.image_width}×{result.image_height}"
    return (
        f"Detection OK: {result.num_faces} face(s) in {dims}. "
        + "; ".join(parts)
        + "."
    )
