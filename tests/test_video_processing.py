"""
Unit & Integration Test Suite for Video Processing Service (Phase 17).

Does NOT require MongoDB.
Uses OpenCV synthetic video generation for controlled, isolated testing.
"""

import os
import tempfile
import pytest
import numpy as np
import cv2

from services.video_processing import (
    VideoMetadata,
    SampledFrame,
    VideoValidationResult,
    ExtractionResult,
    validate_video,
    get_video_metadata,
    sample_frames,
    extract_frames,
    release_video_resources,
    save_temporary_video,
)
from config import settings


# ── Helper Fixtures & Synthetic Video Generators ────────────────────

def create_synthetic_mp4_video(
    filename: str = "test_synthetic.mp4",
    width: int = 320,
    height: int = 240,
    fps: float = 30.0,
    num_frames: int = 60
) -> str:
    """
    Creates a synthetic MP4 video file on disk for unit testing.
    """
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, filename)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create a simple synthetic frame with varying color
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color_val = (i * 4) % 256
        frame[:, :] = (color_val, 255 - color_val, 128)
        # Add frame text label
        cv2.putText(
            frame,
            f"Frame {i}",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )
        out.write(frame)

    out.release()
    return video_path


@pytest.fixture
def synthetic_video():
    """Fixture providing a 60-frame 30FPS MP4 synthetic video."""
    video_path = create_synthetic_mp4_video("test_fixture_60frames.mp4", num_frames=60, fps=30.0)
    yield video_path
    if os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass


# ── Test Cases ──────────────────────────────────────────────────────

def test_valid_mp4_video(synthetic_video):
    """1. Test validation of a valid MP4 video."""
    res = validate_video(synthetic_video)
    assert res.is_valid is True
    assert res.error_message == ""
    assert res.metadata is not None
    assert res.metadata.width == 320
    assert res.metadata.height == 240
    assert res.metadata.fps == 30.0
    assert res.metadata.total_frame_count == 60


def test_invalid_video_file():
    """2. Test rejection of non-existent video file path."""
    res = validate_video("non_existent_video_path_12345.mp4")
    assert res.is_valid is False
    assert "does not exist" in res.error_message.lower()


def test_unsupported_file_type():
    """3. Test rejection of unsupported file extension."""
    temp_dir = tempfile.gettempdir()
    dummy_txt = os.path.join(temp_dir, "test_document.txt")
    with open(dummy_txt, "w") as f:
        f.write("This is not a video file.")

    try:
        res = validate_video(dummy_txt)
        assert res.is_valid is False
        assert "unsupported video format" in res.error_message.lower()
    finally:
        if os.path.exists(dummy_txt):
            os.remove(dummy_txt)


def test_corrupted_video_file():
    """4. Test rejection of a corrupted video file."""
    temp_dir = tempfile.gettempdir()
    corrupt_path = os.path.join(temp_dir, "corrupt_video.mp4")
    with open(corrupt_path, "wb") as f:
        f.write(b"CORRUPT_HEADER_GARBAGE_BYTES_1234567890")

    try:
        res = validate_video(corrupt_path)
        assert res.is_valid is False
        assert ("could not open" in res.error_message.lower() or "corrupted" in res.error_message.lower())
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


def test_video_metadata_extraction(synthetic_video):
    """5. Test get_video_metadata structured result."""
    meta = get_video_metadata(synthetic_video)
    assert isinstance(meta, VideoMetadata)
    assert meta.filename == "test_fixture_60frames.mp4"
    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 30.0
    assert meta.total_frame_count == 60
    assert meta.duration_seconds == 2.0  # 60 frames / 30 fps = 2s

    # Test to_dict helper
    meta_dict = meta.to_dict()
    assert meta_dict["filename"] == "test_fixture_60frames.mp4"
    assert meta_dict["frame_count"] == 60
    assert meta_dict["duration_seconds"] == 2.0


def test_fps_extraction(synthetic_video):
    """6. Test exact FPS extraction."""
    meta = get_video_metadata(synthetic_video)
    assert meta.fps == 30.0


def test_frame_count_extraction(synthetic_video):
    """7. Test frame count metric extraction."""
    meta = get_video_metadata(synthetic_video)
    assert meta.total_frame_count == 60


def test_duration_calculation(synthetic_video):
    """8. Test video duration calculation in seconds."""
    meta = get_video_metadata(synthetic_video)
    # 60 frames / 30 FPS = 2.0 seconds
    assert pytest.approx(meta.duration_seconds, 0.01) == 2.0


def test_frame_sampling(synthetic_video):
    """9. Test frame sampling with 1.0s interval on 30 FPS, 60-frame video."""
    # 30 FPS, interval 1.0s => step = 30 frames => sampled at frame 0, frame 30 => 2 frames
    res = sample_frames(synthetic_video, sample_interval_seconds=1.0)
    assert res.total_frames_sampled == 2
    assert len(res.frames) == 2
    assert res.frames[0].frame_index == 0
    assert res.frames[0].timestamp_seconds == 0.0
    assert res.frames[1].frame_index == 30
    assert pytest.approx(res.frames[1].timestamp_seconds, 0.01) == 1.0
    assert res.frames[0].frame.shape == (240, 320, 3)  # RGB frame shape


def test_sampling_interval(synthetic_video):
    """10. Test varying sampling interval (0.5s vs 2.0s)."""
    # 0.5s interval => step = 15 frames => frames 0, 15, 30, 45 => 4 frames
    res_05 = sample_frames(synthetic_video, sample_interval_seconds=0.5)
    assert res_05.total_frames_sampled == 4

    # 2.0s interval => step = 60 frames => frame 0 => 1 frame
    res_20 = sample_frames(synthetic_video, sample_interval_seconds=2.0)
    assert res_20.total_frames_sampled == 1


def test_maximum_frame_limit(synthetic_video):
    """11. Test safety limit (max_frames_to_process)."""
    # Force max_frames_to_process = 1 on video that would sample 2 frames
    res = sample_frames(synthetic_video, sample_interval_seconds=1.0, max_frames_to_process=1)
    assert res.total_frames_sampled == 1
    assert res.limit_reached is True
    assert "safety limit reached" in res.message.lower()


def test_empty_video_file():
    """12. Test validation and error handling for 0-byte video file."""
    temp_dir = tempfile.gettempdir()
    empty_path = os.path.join(temp_dir, "empty_video.mp4")
    with open(empty_path, "wb") as f:
        pass  # create 0 byte file

    try:
        res = validate_video(empty_path)
        assert res.is_valid is False
        assert "empty" in res.error_message.lower()
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)


def test_zero_invalid_fps(monkeypatch, synthetic_video):
    """13. Test zero/invalid FPS detection."""
    # Monkeypatch cv2.VideoCapture.get to return 0 for CAP_PROP_FPS
    orig_get = cv2.VideoCapture.get

    def mock_get(self, propId):
        if propId == cv2.CAP_PROP_FPS:
            return 0.0
        return orig_get(self, propId)

    monkeypatch.setattr(cv2.VideoCapture, "get", mock_get)

    res = validate_video(synthetic_video)
    assert res.is_valid is False
    assert "invalid or zero fps" in res.error_message.lower()


def test_opencv_resource_release(synthetic_video):
    """14. Test safe OpenCV resource release function."""
    cap = cv2.VideoCapture(synthetic_video)
    assert cap.isOpened() is True
    release_video_resources(cap)
    assert cap.isOpened() is False

    # Calling release again or on None should not crash
    release_video_resources(None)
    release_video_resources(cap)


def test_temporary_file_cleanup():
    """15. Test save_temporary_video and cleanup callback."""
    dummy_bytes = b"TEMPORARY_VIDEO_BYTES_DATA"
    temp_path, cleanup_fn = save_temporary_video(dummy_bytes, filename="sample.mp4")

    assert os.path.exists(temp_path)
    assert os.path.getsize(temp_path) == len(dummy_bytes)

    # Call cleanup callback
    cleanup_fn()
    assert not os.path.exists(temp_path)


def test_large_video_protection(synthetic_video):
    """16. Test rejection of videos exceeding MAX_VIDEO_SIZE_MB."""
    # Set max_size_mb to a tiny limit (0.0001 MB ~ 100 bytes) so our synthetic video exceeds it
    res = validate_video(synthetic_video, max_size_mb=0.0001)
    assert res.is_valid is False
    assert "exceeds maximum allowed limit" in res.error_message.lower()
