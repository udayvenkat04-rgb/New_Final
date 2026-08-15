"""
Phase 25 Performance Benchmarking Test Suite.
"""

import sys
import os
import time
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.face_matching import KNNFaceMatchingEngine
from models.face_vector import FaceVector


def normalize_vector(v):
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


def test_knn_search_performance_scaling():
    engine = KNNFaceMatchingEngine(default_k=5, default_threshold=0.60)

    # Generate 500 synthetic normalized 1,404-D face vectors
    ref_vectors = []
    for i in range(500):
        vec = normalize_vector(np.random.rand(1404).astype(np.float32))
        ref_vectors.append(FaceVector(case_id=i + 1, vector=vec.tolist()))

    class MockFaceRepo:
        def get_all_registered(self): return ref_vectors

    engine.face_repo = MockFaceRepo()

    query_vec = normalize_vector(np.random.rand(1404).astype(np.float32))

    start_t = time.perf_counter()
    res = engine.match_vector(query_vec, top_k=5)
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    # Must execute KNN vector search across 500 embeddings in < 250 ms
    assert elapsed_ms < 250.0
