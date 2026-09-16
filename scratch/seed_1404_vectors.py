import json
import os
import numpy as np

from backend.services.face_embedding import DEFAULT_LANDMARKS_PER_FACE, DEFAULT_VECTOR_DIM, normalize_landmarks, landmarks_to_vector
from backend.services.face_detection import FaceLandmark

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_VECTORS_JSON = os.path.join(PROJECT_ROOT, "missing_person_db", "face_vectors.json")

def generate_valid_1404_vector(seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    lms = []
    cols = int(np.ceil(np.sqrt(DEFAULT_LANDMARKS_PER_FACE)))
    rows = int(np.ceil(DEFAULT_LANDMARKS_PER_FACE / cols))
    u = np.linspace(0.3, 0.7, cols)
    v = np.linspace(0.3, 0.7, rows)
    uu, vv = np.meshgrid(u, v)
    xs = (uu.ravel()[:DEFAULT_LANDMARKS_PER_FACE] + rng.normal(0, 0.01, DEFAULT_LANDMARKS_PER_FACE)).astype(np.float32)
    ys = (vv.ravel()[:DEFAULT_LANDMARKS_PER_FACE] + rng.normal(0, 0.01, DEFAULT_LANDMARKS_PER_FACE)).astype(np.float32)
    zs = (rng.normal(0, 0.005, DEFAULT_LANDMARKS_PER_FACE)).astype(np.float32)
    
    for i in range(DEFAULT_LANDMARKS_PER_FACE):
        lms.append(FaceLandmark(index=i, x=float(xs[i]), y=float(ys[i]), z=float(zs[i])))
        
    normed = normalize_landmarks(lms, expected_landmarks=468)
    flat = landmarks_to_vector(normed, expected_landmarks=468)
    return [float(x) for x in flat.tolist()]

def update_seed_vectors():
    records = []
    names = ["aarav", "diya", "rohan", "ananya", "vivaan", "sanya"]
    
    for i in range(1, 7):
        vec = generate_valid_1404_vector(seed=100 + i)
        records.append({
            "id": i,
            "case_id": i,
            "sighting_id": None,
            "vector": vec,
            "embedding": vec,
            "dimensions": 1404,
            "photo_path": f"data/faces/{names[i-1]}.jpg",
            "created_at": "2026-08-08T16:00:00"
        })
        
    with open(FACE_VECTORS_JSON, "w") as f:
        json.dump(records, f, indent=2)
        
    print(f"Successfully wrote {len(records)} 1,404-D face vectors to {FACE_VECTORS_JSON}")

if __name__ == "__main__":
    update_seed_vectors()
