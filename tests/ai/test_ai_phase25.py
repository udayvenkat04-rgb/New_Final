"""
Phase 25 AI Pipeline Test Suite: Face Landmark Detection, 1,404-D Embeddings, KNN Similarity Engine.
"""

import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.face_embedding import validate_face_vector
from services.face_matching import KNNFaceMatchingEngine
from models.face_vector import FaceVector


def normalize_vector(v):
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


def test_1404_dimension_face_vector_validation():
    # Valid 1,404-D vector
    valid_vector = np.random.rand(1404).astype(np.float32)
    assert validate_face_vector(valid_vector).is_valid is True

    # Normalized vector
    norm_vec = normalize_vector(valid_vector)
    assert len(norm_vec) == 1404
    assert np.isclose(np.linalg.norm(norm_vec), 1.0)


def test_invalid_face_vectors_rejection():
    # Wrong dimensions (512-D)
    wrong_dim = np.random.rand(512).astype(np.float32)
    assert validate_face_vector(wrong_dim).is_valid is False

    # NaN vector
    nan_vector = np.full(1404, np.nan).astype(np.float32)
    assert validate_face_vector(nan_vector).is_valid is False

    # Infinite vector
    inf_vector = np.full(1404, np.inf).astype(np.float32)
    assert validate_face_vector(inf_vector).is_valid is False

    # None vector
    assert validate_face_vector(None).is_valid is False


def test_knn_matching_engine_candidate_search():
    engine = KNNFaceMatchingEngine(default_k=3, default_threshold=0.50)

    # Synthetic reference database
    ref_vector = np.random.rand(1404).astype(np.float32)
    ref_vector = normalize_vector(ref_vector)

    class MockFaceRepo:
        def get_all_registered(self):
            return [FaceVector(case_id=101, vector=ref_vector.tolist())]

    engine.face_repo = MockFaceRepo()

    # Query with exact vector -> candidate match
    res = engine.match_vector(ref_vector, top_k=5)
    assert res is not None
