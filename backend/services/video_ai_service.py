"""
Video AI Application Service — Phase 18

Connects:
- OpenCV Frame Sampling (Phase 17)
- MediaPipe Face Detection (Phase 12)
- 1,404-D Face Vector Generation (Phase 13)
- KNN Face Matching Engine (Phase 15)
- Cross-Frame & Temporal Aggregation Engine

Capabilities:
- Multi-face per frame processing
- Single frame failure recovery (fault-tolerant loop)
- Pre-building KNN model for fast video frame scanning
- Temporal grouping with configurable gap threshold
- Selection of best representative preview frame (highest similarity)
- Clean, structured statistics reporting
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from backend.config import settings
from backend.repositories.case_repository import CaseRepository
from backend.repositories.face_repository import FaceRepository
from backend.services.face_detection import FaceDetectionResult, detect_faces
from backend.services.face_embedding import generate_face_vector, validate_face_vector
from backend.services.face_matching import FaceMatchingService
from backend.services.video_processing import (
    ExtractionResult,
    SampledFrame,
    VideoMetadata,
    VideoValidationResult,
    sample_frames,
    validate_video,
)

logger = logging.getLogger(__name__)


# ── Structured Result Data Models ────────────────────────────────────

@dataclass
class FrameFaceMatch:
    """Represents a potential match for a single face detected in a single frame."""
    frame_index: int
    timestamp_seconds: float
    face_index: int
    case_id: str
    case_name: str
    distance: float
    similarity_score: float
    decision: str = "POTENTIAL_MATCH"
    frame_rgb: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_seconds": round(self.timestamp_seconds, 2),
            "face_index": self.face_index,
            "case_id": self.case_id,
            "case_name": self.case_name,
            "distance": round(self.distance, 4),
            "similarity_score": round(self.similarity_score, 2),
            "decision": self.decision,
        }


@dataclass
class TemporalSegment:
    """Represents a contiguous temporal segment of detections for a single case."""
    start_timestamp: float
    end_timestamp: float
    detection_count: int
    best_similarity: float
    best_distance: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_timestamp": round(self.start_timestamp, 2),
            "end_timestamp": round(self.end_timestamp, 2),
            "detection_count": self.detection_count,
            "best_similarity": round(self.best_similarity, 2),
            "best_distance": round(self.best_distance, 4),
        }


@dataclass
class AggregatedVideoSighting:
    """Represents a unique candidate case aggregated across multiple frames."""
    case_id: str
    case_name: str
    first_seen_timestamp: float
    last_seen_timestamp: float
    detection_count: int
    best_distance: float
    best_similarity: float
    representative_frame: Optional[np.ndarray] = None
    segments: List[TemporalSegment] = field(default_factory=list)
    decision: str = "POTENTIAL MATCH"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "first_seen_timestamp": round(self.first_seen_timestamp, 2),
            "last_seen_timestamp": round(self.last_seen_timestamp, 2),
            "detection_count": self.detection_count,
            "best_distance": round(self.best_distance, 4),
            "best_similarity": round(self.best_similarity, 2),
            "decision": self.decision,
            "segment_count": len(self.segments),
            "segments": [s.to_dict() for s in self.segments],
        }


@dataclass
class VideoAIScanResult:
    """Structured result object returned by the Video AI Service."""
    status: str  # "SUCCESS", "NO_FACES_DETECTED", "NO_POTENTIAL_MATCH", "NO_REFERENCE_VECTORS", "ERROR"
    unique_candidates: List[AggregatedVideoSighting] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


# ── Core Video AI Application Service ───────────────────────────────

from backend.auth.permissions import authorize_process_video


class VideoAIService:
    """
    Orchestrates video frame sampling, MediaPipe face detection,
    vector generation, KNN matching, and temporal aggregation.
    """

    def __init__(
        self,
        case_repo: Optional[CaseRepository] = None,
        face_repo: Optional[FaceRepository] = None,
        matching_service: Optional[FaceMatchingService] = None,
    ):
        self.case_repo = case_repo or CaseRepository()
        self.face_repo = face_repo or FaceRepository()
        self.matching_service = matching_service or FaceMatchingService(face_repo=self.face_repo)

    def process_video_ai(
        self,
        video_path: str,
        sample_interval_seconds: float = getattr(settings, "VIDEO_SAMPLE_INTERVAL_SECONDS", 1.0),
        max_frames_to_process: int = getattr(settings, "MAX_VIDEO_FRAMES_TO_PROCESS", 500),
        threshold: float = getattr(settings, "FACE_MATCH_THRESHOLD", 0.60),
        gap_seconds: float = getattr(settings, "VIDEO_SIGHTING_GAP_SECONDS", 5.0),
        progress_callback: Optional[Callable[[float, str], None]] = None,
        user: Optional[Dict[str, Any]] = None,
    ) -> VideoAIScanResult:
        """
        Executes complete Video AI analysis pipeline:
        Video -> Sampling -> MediaPipe -> 1,404D Vector -> KNN -> Cross-Frame Aggregation.
        """
        if user:
            authorize_process_video(user)

        start_time = time.time()

        # 1. Validate Video Input
        val_res: VideoValidationResult = validate_video(video_path)
        if not val_res.is_valid or val_res.metadata is None:
            return VideoAIScanResult(
                status="ERROR",
                message=f"Video validation failed: {val_res.error_message}",
                statistics={"processing_duration_seconds": round(time.time() - start_time, 2)}
            )

        meta: VideoMetadata = val_res.metadata

        # 2. Extract Sampled Frames
        if progress_callback:
            progress_callback(0.05, "Sampling video frames...")

        extraction_res: ExtractionResult = sample_frames(
            video_path,
            sample_interval_seconds=sample_interval_seconds,
            max_frames_to_process=max_frames_to_process
        )

        sampled_frames = extraction_res.frames
        total_sampled = len(sampled_frames)

        if total_sampled == 0:
            return VideoAIScanResult(
                status="ERROR",
                message="No frames could be sampled from the video.",
                statistics={
                    "total_video_frames": meta.total_frame_count,
                    "sampled_frames": 0,
                    "processing_duration_seconds": round(time.time() - start_time, 2)
                }
            )

        # 3. Check for Database Reference Vectors
        # We perform a quick test query or check count to avoid scanning frames if DB is empty
        ref_count = len(self.face_repo.get_all_registered())
        if ref_count == 0:
            return VideoAIScanResult(
                status="NO_REFERENCE_VECTORS",
                message="No reference face vectors stored in database for matching.",
                statistics={
                    "total_video_frames": meta.total_frame_count,
                    "sampled_frames": total_sampled,
                    "processed_frames": 0,
                    "frames_with_faces": 0,
                    "total_faces_detected": 0,
                    "valid_vectors_generated": 0,
                    "knn_queries_performed": 0,
                    "potential_matches": 0,
                    "unique_candidate_cases": 0,
                    "processing_duration_seconds": round(time.time() - start_time, 2)
                }
            )

        # 4. Initialize Processing Counters
        processed_frames = 0
        frames_with_faces = 0
        total_faces_detected = 0
        valid_vectors_generated = 0
        knn_queries_performed = 0
        potential_matches_count = 0

        frame_matches: List[FrameFaceMatch] = []

        # Cache case names to avoid repeated DB hits
        case_name_cache: Dict[str, str] = {}

        # 5. Process Frames Incrementally
        for idx, sampled in enumerate(sampled_frames):
            processed_frames += 1

            if progress_callback:
                pct = 0.10 + (0.80 * (idx + 1) / total_sampled)
                progress_callback(
                    pct,
                    f"Analyzing AI pipeline: Frame {idx + 1}/{total_sampled} | "
                    f"Faces: {total_faces_detected} | Matches: {potential_matches_count}..."
                )

            try:
                # MediaPipe Face Detection on RGB frame
                try:
                    detection: FaceDetectionResult = detect_faces(sampled.frame, fallback_on_unclear=False)
                except TypeError as e:
                    if "unexpected keyword argument 'fallback_on_unclear'" in str(e):
                        detection = detect_faces(sampled.frame)
                    else:
                        raise

                if not detection.success or detection.num_faces == 0:
                    continue

                frames_with_faces += 1
                total_faces_detected += detection.num_faces

                # Process each detected face independently
                for face_idx, detected_face in enumerate(detection.faces):
                    try:
                        # Generate 1,404-D Vector (Phase 13)
                        query_vec = generate_face_vector(detected_face)
                        valid_vectors_generated += 1

                        # KNN Query (Phase 15)
                        match_res = self.matching_service.match_vector(
                            query_vec,
                            top_k=1,
                            threshold=threshold
                        )
                        knn_queries_performed += 1

                        if match_res and match_res.get("status") in ("POTENTIAL_MATCH", "MATCH_FOUND"):
                            best_cand = match_res.get("best_candidate")
                            if best_cand and (best_cand.get("is_potential_match") or best_cand.get("decision") in ("POTENTIAL_MATCH", "POTENTIAL MATCH")):
                                case_id = str(best_cand["case_id"])

                                # Resolve Case Name
                                if case_id not in case_name_cache:
                                    c_obj = self.case_repo.get_by_id(case_id)
                                    case_name_cache[case_id] = c_obj.name if c_obj else f"Case {case_id}"

                                case_name = case_name_cache[case_id]
                                potential_matches_count += 1

                                frame_matches.append(
                                    FrameFaceMatch(
                                        frame_index=sampled.frame_index,
                                        timestamp_seconds=sampled.timestamp_seconds,
                                        face_index=face_idx,
                                        case_id=case_id,
                                        case_name=case_name,
                                        distance=float(best_cand["distance"]),
                                        similarity_score=float(best_cand["similarity_score"]),
                                        decision="POTENTIAL_MATCH",
                                        frame_rgb=sampled.frame
                                    )
                                )
                    except Exception as face_exc:
                        logger.warning(
                            "Error processing face %d in frame %d: %s",
                            face_idx, sampled.frame_index, face_exc
                        )
                        continue

            except Exception as frame_exc:
                logger.warning("Error running AI detection on frame %d: %s", sampled.frame_index, frame_exc)
                continue

        # 6. Post-Processing & Case Aggregation
        elapsed = time.time() - start_time

        stats = {
            "total_video_frames": meta.total_frame_count,
            "sampled_frames": total_sampled,
            "processed_frames": processed_frames,
            "frames_with_faces": frames_with_faces,
            "total_faces_detected": total_faces_detected,
            "valid_vectors_generated": valid_vectors_generated,
            "knn_queries_performed": knn_queries_performed,
            "potential_matches": potential_matches_count,
            "unique_candidate_cases": 0,
            "processing_duration_seconds": round(elapsed, 2)
        }

        if total_faces_detected == 0:
            return VideoAIScanResult(
                status="NO_FACES_DETECTED",
                unique_candidates=[],
                statistics=stats,
                message="No human faces detected in any of the sampled video frames."
            )

        if not frame_matches:
            return VideoAIScanResult(
                status="NO_POTENTIAL_MATCH",
                unique_candidates=[],
                statistics=stats,
                message="Faces were detected, but none matched any registered missing person within the configured threshold."
            )

        # Aggregate frame matches by case_id
        aggregated_candidates = self._aggregate_frame_matches(frame_matches, gap_seconds=gap_seconds)
        stats["unique_candidate_cases"] = len(aggregated_candidates)

        if progress_callback:
            progress_callback(1.0, f"Completed AI Video Scan! Found {len(aggregated_candidates)} candidate case(s).")

        return VideoAIScanResult(
            status="SUCCESS",
            unique_candidates=aggregated_candidates,
            statistics=stats,
            message=f"Successfully analyzed video. Found {len(aggregated_candidates)} unique candidate missing person case(s)."
        )

    def _aggregate_frame_matches(
        self,
        matches: List[FrameFaceMatch],
        gap_seconds: float = 5.0
    ) -> List[AggregatedVideoSighting]:
        """
        Aggregates individual frame-level face matches by case_id.
        Computes first_seen, last_seen, detection_count, best_distance, best_similarity,
        selects best representative frame, and partitions into temporal segments.
        """
        # Group matches by case_id
        by_case: Dict[str, List[FrameFaceMatch]] = {}
        for m in matches:
            by_case.setdefault(m.case_id, []).append(m)

        aggregated: List[AggregatedVideoSighting] = []

        for case_id, case_matches in by_case.items():
            # Sort chronologically by timestamp
            sorted_matches = sorted(case_matches, key=lambda x: x.timestamp_seconds)

            first_seen = sorted_matches[0].timestamp_seconds
            last_seen = sorted_matches[-1].timestamp_seconds
            count = len(sorted_matches)
            case_name = sorted_matches[0].case_name

            # Find best match (smallest Euclidean distance / highest similarity)
            best_match = min(sorted_matches, key=lambda x: x.distance)
            best_dist = best_match.distance
            best_sim = best_match.similarity_score
            rep_frame = best_match.frame_rgb

            # Build Temporal Segments
            segments: List[TemporalSegment] = []
            curr_seg_start = sorted_matches[0].timestamp_seconds
            curr_seg_last = sorted_matches[0].timestamp_seconds
            curr_seg_count = 1
            curr_seg_best_dist = sorted_matches[0].distance
            curr_seg_best_sim = sorted_matches[0].similarity_score

            for m in sorted_matches[1:]:
                if (m.timestamp_seconds - curr_seg_last) <= gap_seconds:
                    # Continue current temporal segment
                    curr_seg_last = m.timestamp_seconds
                    curr_seg_count += 1
                    if m.distance < curr_seg_best_dist:
                        curr_seg_best_dist = m.distance
                        curr_seg_best_sim = m.similarity_score
                else:
                    # Close current segment and start new one
                    segments.append(
                        TemporalSegment(
                            start_timestamp=curr_seg_start,
                            end_timestamp=curr_seg_last,
                            detection_count=curr_seg_count,
                            best_similarity=curr_seg_best_sim,
                            best_distance=curr_seg_best_dist
                        )
                    )
                    curr_seg_start = m.timestamp_seconds
                    curr_seg_last = m.timestamp_seconds
                    curr_seg_count = 1
                    curr_seg_best_dist = m.distance
                    curr_seg_best_sim = m.similarity_score

            # Close final segment
            segments.append(
                TemporalSegment(
                    start_timestamp=curr_seg_start,
                    end_timestamp=curr_seg_last,
                    detection_count=curr_seg_count,
                    best_similarity=curr_seg_best_sim,
                    best_distance=curr_seg_best_dist
                )
            )

            aggregated.append(
                AggregatedVideoSighting(
                    case_id=case_id,
                    case_name=case_name,
                    first_seen_timestamp=first_seen,
                    last_seen_timestamp=last_seen,
                    detection_count=count,
                    best_distance=best_dist,
                    best_similarity=best_sim,
                    representative_frame=rep_frame,
                    segments=segments,
                    decision="POTENTIAL MATCH"
                )
            )

        # Sort aggregated candidates by best_similarity descending (highest first)
        aggregated.sort(key=lambda x: x.best_similarity, reverse=True)
        return aggregated
