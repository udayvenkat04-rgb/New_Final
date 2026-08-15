"""
Video Processing Service — Phase 17

Handles all OpenCV video-processing logic for the Missing Person Identification System.

Capabilities:
- Video validation (existence, extension, file size, decodability, FPS, resolution)
- Structured metadata extraction (width, height, FPS, frame count, duration, codec)
- Configurable frame sampling (interval in seconds, max frame safety limit)
- RGB frame extraction
- Safe OpenCV resource management (guaranteed VideoCapture release)
- Temporary file management and cleanup
"""

from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import cv2
import numpy as np

from backend.config import settings


# ── Structured Data Models ──────────────────────────────────────────

@dataclass
class VideoMetadata:
    """Structured container for extracted video metadata."""
    filename: str
    width: int
    height: int
    fps: float
    total_frame_count: int
    duration_seconds: float
    codec: str = "UNKNOWN"
    estimated_frame_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 2),
            "frame_count": self.total_frame_count,
            "duration_seconds": round(self.duration_seconds, 2),
            "codec": self.codec,
            "estimated_frame_count": self.estimated_frame_count,
        }


@dataclass
class SampledFrame:
    """Structured container for a single sampled frame."""
    frame_index: int
    timestamp_seconds: float
    frame: np.ndarray  # RGB image numpy array (H, W, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_seconds": round(self.timestamp_seconds, 2),
            "frame_shape": self.frame.shape if self.frame is not None else None,
        }


@dataclass
class VideoValidationResult:
    """Result object for video validation checks."""
    is_valid: bool
    error_message: str = ""
    metadata: Optional[VideoMetadata] = None


@dataclass
class ExtractionResult:
    """Result object for frame sampling / extraction ops."""
    frames: List[SampledFrame] = field(default_factory=list)
    total_frames_sampled: int = 0
    total_video_frames: int = 0
    duration_seconds: float = 0.0
    limit_reached: bool = False
    message: str = ""


# ── Helper Utilities ────────────────────────────────────────────────

def release_video_resources(cap: Optional[cv2.VideoCapture]) -> None:
    """
    Safely releases an OpenCV VideoCapture resource if opened.
    Does not raise exceptions.
    """
    if cap is not None:
        try:
            if cap.isOpened():
                cap.release()
        except Exception:
            pass


def _decode_fourcc(fourcc_int: float | int) -> str:
    """Converts OpenCV FOURCC code integer to 4-character string."""
    try:
        val = int(fourcc_int)
        if val <= 0:
            return "UNKNOWN"
        chars = [chr((val >> (8 * i)) & 0xFF) for i in range(4)]
        codec_str = "".join(chars).strip()
        return codec_str if codec_str else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def save_temporary_video(file_source: Any, filename: Optional[str] = None) -> Tuple[str, Callable[[], None]]:
    """
    Saves an uploaded file (bytes, Streamlit UploadedFile, or file-like)
    to a temporary path in `data/videos/` (or system temp directory).

    Returns:
        (temp_file_path, cleanup_callback)
    """
    videos_dir = getattr(settings, "VIDEOS_DIR", str(Path(tempfile.gettempdir()) / "mp_videos"))
    os.makedirs(videos_dir, exist_ok=True)

    raw_name = filename or getattr(file_source, "name", "uploaded_video.mp4")
    original_name = os.path.basename(str(raw_name))
    ext = os.path.splitext(original_name)[1].lower() or ".mp4"

    allowed_exts = getattr(settings, "ALLOWED_VIDEO_EXTENSIONS", {".mp4", ".avi", ".mov", ".mkv"})
    if ext not in allowed_exts:
        raise ValueError(f"Unsupported video format: '{ext}'. Allowed formats: {', '.join(sorted(allowed_exts))}.")

    unique_filename = f"temp_video_{uuid.uuid4().hex[:10]}{ext}"
    temp_path = os.path.normpath(os.path.join(videos_dir, unique_filename))

    if isinstance(file_source, (bytes, bytearray)):
        with open(temp_path, "wb") as f:
            f.write(file_source)
    elif hasattr(file_source, "read"):
        # Handle file-like or UploadedFile
        file_source.seek(0)
        with open(temp_path, "wb") as f:
            f.write(file_source.read())
        # Reset pointer if supported
        if hasattr(file_source, "seek"):
            try:
                file_source.seek(0)
            except Exception:
                pass
    elif isinstance(file_source, (str, Path)) and os.path.exists(file_source):
        # File path passed directly — no need to copy
        return str(file_source), lambda: None
    else:
        raise ValueError("Invalid file_source: must be bytes, UploadedFile, or valid existing file path.")

    def cleanup():
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return temp_path, cleanup


# ── Core Service Functions ──────────────────────────────────────────

def validate_video(
    video_path: str,
    max_size_mb: float = getattr(settings, "MAX_VIDEO_SIZE_MB", 100)
) -> VideoValidationResult:
    """
    Validates a video file:
    - Checks file existence & non-empty
    - Checks extension against allowed formats (.mp4, .avi, .mov, .mkv)
    - Checks file size against max_size_mb limit
    - Checks OpenCV can open the video
    - Checks resolution > 0, FPS > 0, decodable test frame
    """
    if not video_path or not isinstance(video_path, (str, Path)):
        return VideoValidationResult(is_valid=False, error_message="Video file path is required.")

    video_path_str = str(video_path)
    if not os.path.exists(video_path_str):
        return VideoValidationResult(is_valid=False, error_message="Video file does not exist on disk.")

    file_size_bytes = os.path.getsize(video_path_str)
    if file_size_bytes == 0:
        return VideoValidationResult(is_valid=False, error_message="Video file is empty (0 bytes).")

    max_bytes = max_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        file_size_mb = file_size_bytes / (1024 * 1024)
        return VideoValidationResult(
            is_valid=False,
            error_message=f"Video size ({file_size_mb:.2f} MB) exceeds maximum allowed limit of {max_size_mb} MB."
        )

    ext = os.path.splitext(video_path_str)[1].lower()
    allowed_exts = getattr(settings, "ALLOWED_VIDEO_EXTENSIONS", {".mp4", ".avi", ".mov", ".mkv"})
    if ext not in allowed_exts:
        return VideoValidationResult(
            is_valid=False,
            error_message=f"Unsupported video format: '{ext or 'none'}'. Allowed formats: {', '.join(sorted(allowed_exts))}."
        )

    cap: Optional[cv2.VideoCapture] = None
    try:
        cap = cv2.VideoCapture(video_path_str)
        if not cap.isOpened():
            return VideoValidationResult(
                is_valid=False,
                error_message="OpenCV could not open or decode the video file. File may be corrupted or use an unsupported codec."
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0:
            return VideoValidationResult(
                is_valid=False,
                error_message=f"Invalid video dimensions ({width}x{height})."
            )

        if fps <= 0 or np.isnan(fps) or np.isinf(fps):
            return VideoValidationResult(
                is_valid=False,
                error_message="Invalid or zero FPS detected in video metadata."
            )

        # Test frame read to confirm decodability
        ret, frame = cap.read()
        if not ret or frame is None or frame.size == 0:
            return VideoValidationResult(
                is_valid=False,
                error_message="Video file has no decodable frames or is corrupted."
            )

        # Compute metadata
        duration = frame_count / fps if (fps > 0 and frame_count > 0) else 0.0
        codec = _decode_fourcc(cap.get(cv2.CAP_PROP_FOURCC))
        meta = VideoMetadata(
            filename=os.path.basename(video_path_str),
            width=width,
            height=height,
            fps=fps,
            total_frame_count=frame_count,
            duration_seconds=duration,
            codec=codec,
            estimated_frame_count=frame_count,
        )

        return VideoValidationResult(is_valid=True, error_message="", metadata=meta)

    except Exception as exc:
        return VideoValidationResult(
            is_valid=False,
            error_message=f"An unexpected error occurred while validating video: {str(exc)}"
        )
    finally:
        release_video_resources(cap)


def get_video_metadata(video_path: str) -> VideoMetadata:
    """
    Extracts structured VideoMetadata from a video file using OpenCV.
    Raises ValueError if video cannot be opened.
    """
    val_res = validate_video(video_path)
    if not val_res.is_valid or val_res.metadata is None:
        raise ValueError(val_res.error_message or "Failed to read video metadata.")
    return val_res.metadata


def sample_frames(
    video_path: str,
    sample_interval_seconds: float = getattr(settings, "VIDEO_SAMPLE_INTERVAL_SECONDS", 1.0),
    max_frames_to_process: int = getattr(settings, "MAX_VIDEO_FRAMES_TO_PROCESS", 500),
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> ExtractionResult:
    """
    Samples frames from a video file incrementally according to sample_interval_seconds.

    Sampling Strategy:
    - Interval step in frames = max(1, int(round(fps * sample_interval_seconds)))
    - Converts sampled BGR frames to RGB numpy arrays.
    - Respects max_frames_to_process safety limit.

    Guarantees OpenCV VideoCapture resource release via finally block.
    """
    val_res = validate_video(video_path)
    if not val_res.is_valid or val_res.metadata is None:
        return ExtractionResult(
            frames=[],
            total_frames_sampled=0,
            total_video_frames=0,
            duration_seconds=0.0,
            limit_reached=False,
            message=f"Video validation failed: {val_res.error_message}"
        )

    meta = val_res.metadata
    fps = meta.fps
    total_video_frames = meta.total_frame_count

    # Calculate frame step
    step = max(1, int(round(fps * sample_interval_seconds)))

    cap: Optional[cv2.VideoCapture] = None
    sampled_frames: List[SampledFrame] = []
    limit_reached = False

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return ExtractionResult(
                message="Failed to open video for frame sampling."
            )

        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_idx % step == 0:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = frame_idx / fps if fps > 0 else 0.0

                sampled_frames.append(
                    SampledFrame(
                        frame_index=frame_idx,
                        timestamp_seconds=timestamp,
                        frame=rgb_frame
                    )
                )

                if progress_callback:
                    pct = min(1.0, (frame_idx + 1) / max(1, total_video_frames))
                    progress_callback(
                        pct,
                        f"Extracted {len(sampled_frames)} frames (Frame {frame_idx}/{total_video_frames})..."
                    )

                if len(sampled_frames) >= max_frames_to_process:
                    limit_reached = True
                    break

            frame_idx += 1

        if progress_callback:
            progress_callback(1.0, f"Completed! Sampled {len(sampled_frames)} frames.")

        msg = (
            f"Successfully sampled {len(sampled_frames)} frames from video."
            if not limit_reached
            else f"Safety limit reached: stopped sampling at maximum configured limit of {max_frames_to_process} frames."
        )

        return ExtractionResult(
            frames=sampled_frames,
            total_frames_sampled=len(sampled_frames),
            total_video_frames=total_video_frames,
            duration_seconds=meta.duration_seconds,
            limit_reached=limit_reached,
            message=msg
        )

    except Exception as exc:
        return ExtractionResult(
            frames=sampled_frames,
            total_frames_sampled=len(sampled_frames),
            total_video_frames=total_video_frames,
            duration_seconds=meta.duration_seconds,
            limit_reached=limit_reached,
            message=f"Error during frame extraction: {str(exc)}"
        )
    finally:
        release_video_resources(cap)


def extract_frames(
    video_path: str,
    frame_indices: List[int]
) -> List[SampledFrame]:
    """
    Extracts specific frames from a video file by their frame indices.
    Returns list of SampledFrame (RGB).
    """
    val_res = validate_video(video_path)
    if not val_res.is_valid or val_res.metadata is None:
        return []

    target_set = set(frame_indices)
    if not target_set:
        return []

    fps = val_res.metadata.fps
    cap: Optional[cv2.VideoCapture] = None
    extracted: List[SampledFrame] = []

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        frame_idx = 0
        max_idx = max(target_set)

        while frame_idx <= max_idx:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_idx in target_set:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = frame_idx / fps if fps > 0 else 0.0
                extracted.append(
                    SampledFrame(
                        frame_index=frame_idx,
                        timestamp_seconds=timestamp,
                        frame=rgb_frame
                    )
                )

            frame_idx += 1

        return extracted
    finally:
        release_video_resources(cap)


# ── Legacy Compatibility Function ───────────────────────────────────

def process_video_feed(
    video_path: str,
    db=None,
    camera_name: str = "Surveillance Cam 01",
    camera_lat: float = 28.6139,
    camera_lon: float = 77.2090,
    frame_interval: int = 15,
    progress_callback=None
) -> list:
    """
    Backwards-compatible wrapper for simulated video scan processing in UI routes.
    Runs VideoAIService to scan video frames against registered active missing profiles.
    Returns a list of match dicts containing case details, timestamp, confidence, and crop path.
    """
    if not os.path.exists(video_path):
        return []

    try:
        from backend.services.video_ai_service import VideoAIService
        service = VideoAIService()
        user = {"role": "admin", "username": "system"}
        sample_sec = max(0.5, frame_interval / 30.0)
        scan_res = service.process_video_ai(
            video_path=video_path,
            sample_interval_seconds=sample_sec,
            progress_callback=progress_callback,
            user=user
        )
        matches = []
        for cand in scan_res.unique_candidates:
            matches.append({
                "case_id": cand.case_id,
                "case_name": cand.case_name,
                "timestamp_sec": cand.first_seen_timestamp,
                "confidence": cand.best_similarity / 100.0 if cand.best_similarity > 1.0 else cand.best_similarity,
                "crop_path": ""
            })
        return matches
    except Exception as exc:
        return []
