import pytest
from services.face_matching import calculate_similarity, match_face_embeddings

def test_calculate_similarity_identical():
    """Identical vectors should yield a cosine similarity score of 1.0."""
    vec = [0.5, 0.5, 0.5, 0.5]
    score = calculate_similarity(vec, vec)
    assert pytest.approx(score, 0.0001) == 1.0

def test_calculate_similarity_orthogonal():
    """Orthogonal vectors should yield a cosine similarity score of 0.0."""
    vec1 = [1.0, 0.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0, 0.0]
    score = calculate_similarity(vec1, vec2)
    assert pytest.approx(score, 0.0001) == 0.0

def test_calculate_similarity_mismatched_dimensions():
    """Mismatched dimension inputs should return 0.0 similarity."""
    score = calculate_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
    assert score == 0.0

def test_match_face_embeddings():
    """Verifies that query embeddings are compared and ranked properly against records."""
    query = [1.0, 0.0, 0.0, 0.0]
    
    # List of database records: (item, embedding_list)
    records = [
        ("Case B", [0.0, 1.0, 0.0, 0.0]), # Orthogonal (score 0.0)
        ("Case A", [0.9, 0.1, 0.0, 0.0]), # Very similar (score ~0.9)
        ("Case C", [0.5, 0.5, 0.0, 0.0]), # Semi-similar (score ~0.7)
    ]
    
    matches = match_face_embeddings(query, records, threshold=0.60)
    
    assert len(matches) == 3
    # Check sorting order: Case A (highest confidence) first
    assert matches[0]["record"] == "Case A"
    assert matches[0]["confidence"] > 0.85
    assert matches[0]["match"] is True
    
    # Case C should be second (semi-similar)
    assert matches[1]["record"] == "Case C"
    assert matches[1]["confidence"] > 0.65
    assert matches[1]["match"] is True
    
    # Case B should be last (orthogonal, below threshold)
    assert matches[2]["record"] == "Case B"
    assert matches[2]["confidence"] == 0.0
    assert matches[2]["match"] is False
