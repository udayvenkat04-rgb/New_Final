# Services Package
from .face_detection import detect_faces
from .face_embedding import (
    generate_face_vector,
    generate_face_vector_by_index,
    generate_vectors_for_all_faces,
    normalize_landmarks,
    landmarks_to_vector,
    validate_face_vector,
    get_embedding_config,
)
from .face_embedding import generate_face_vector as get_face_embedding
from .face_matching import match_face_embeddings, calculate_similarity, knn_match
from .map_service import render_sightings_map
from .email_service import send_matching_alert
from .video_processing import process_video_feed
from .auth_service import AuthService
from .case_service import CaseService
from .match_review import MatchReviewService
from .dashboard_service import DashboardService
from .email_service import EmailService
from .notification_service import NotificationService
from .map_service import MapService
from .public_submission_service import PublicSubmissionService
from .public_submission_review_service import PublicSubmissionReviewService
from .case_lifecycle_service import CaseLifecycleService

__all__ = [
    "detect_faces",
    "generate_face_vector",
    "match_face_embeddings",
    "AuthService",
    "CaseService",
    "MatchReviewService",
    "DashboardService",
    "EmailService",
    "NotificationService",
    "MapService",
    "PublicSubmissionService",
    "PublicSubmissionReviewService",
    "CaseLifecycleService",
]
