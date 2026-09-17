import glob
import os
import json
import numpy as np

from backend.database.collections import get_missing_persons_collection, get_face_vectors_collection
from backend.services.face_storage_service import FaceStorageService
from backend.services.face_detection import detect_faces
from backend.services.face_embedding import generate_face_vector_by_index

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSON_FACE_VECTORS = os.path.join(PROJECT_ROOT, "backend", "missing_person_db", "face_vectors.json")

def process_and_register_real_vectors():
    face_repo_coll = get_face_vectors_collection()
    cases_coll = get_missing_persons_collection()
    cases = list(cases_coll.find())
    
    upload_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "backend", "data", "uploads", "*.jpg")))
    print(f"Found {len(cases)} cases and {len(upload_files)} upload image files.")
    
    face_storage = FaceStorageService()
    json_records = []
    
    for idx, case in enumerate(cases):
        case_id = case.get("id") or (idx + 1)
        name = case.get("name", f"Person {case_id}")
        
        # Pick corresponding uploaded photo if available
        photo_path = None
        if idx < len(upload_files):
            photo_path = upload_files[idx]
        elif case.get("photo_path") and os.path.exists(case.get("photo_path")):
            photo_path = case.get("photo_path")
            
        if not photo_path or not os.path.exists(photo_path):
            print(f"Skipping case_id={case_id} ({name}): image file not found.")
            continue
            
        print(f"Processing real photo for case_id={case_id} ({name}): {photo_path}")
        
        # Detect faces and generate real 1,404-D vector
        detection = detect_faces(photo_path, refine_crops=True)
        if not detection.success or detection.num_faces == 0:
            print(f"  Warning: face detection failed for {photo_path}")
            continue
            
        vec_np = generate_face_vector_by_index(detection, face_index=0, expected_landmarks=468)
        vec_list = [float(x) for x in vec_np.tolist()]
        
        # Save or update in MongoDB
        face_storage.store_face_vector(
            case_id=case_id,
            vector=vec_np,
            expected_dim=1404,
            prevent_duplicates=False
        )
        
        # Copy image file to backend/data/faces/ so load_image_safely can find it
        target_face_path = os.path.join(PROJECT_ROOT, "backend", "data", "faces", f"case_{case_id}.jpg")
        os.makedirs(os.path.dirname(target_face_path), exist_ok=True)
        with open(photo_path, "rb") as src, open(target_face_path, "wb") as dst:
            dst.write(src.read())
            
        # Update case photo_path in MongoDB
        cases_coll.update_one({"id": case_id}, {"$set": {"photo_path": target_face_path}})
        
        json_records.append({
            "id": case_id,
            "case_id": case_id,
            "sighting_id": None,
            "vector": vec_list,
            "embedding": vec_list,
            "dimensions": 1404,
            "photo_path": f"data/faces/case_{case_id}.jpg",
            "created_at": "2026-08-08T16:00:00"
        })
        
    if json_records:
        with open(JSON_FACE_VECTORS, "w") as f:
            json.dump(json_records, f, indent=2)
        print(f"Successfully updated {len(json_records)} real face vectors in MongoDB & JSON seed!")

if __name__ == "__main__":
    process_and_register_real_vectors()
