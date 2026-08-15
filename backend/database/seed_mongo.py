import os
import json
from datetime import datetime
from backend.database.connection import get_database, check_connection
from backend.database.collections import (
    get_users_collection,
    get_missing_persons_collection,
    get_face_vectors_collection,
    get_sightings_collection,
    get_match_results_collection,
    get_case_history_collection
)

# Go up 3 levels from backend/database/seed_mongo.py to reach project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSON_DB_DIR = os.path.join(PROJECT_ROOT, "missing_person_db")

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return date_str

def seed_mongo_database():
    connected, msg = check_connection()
    if not connected:
        print(f"ERROR: Cannot seed database. {msg}")
        return False
        
    print("Connecting to MongoDB...")
    db = get_database()
    
    # Define collection mappings
    mappings = [
        ("users.json", get_users_collection, "users"),
        ("missing_persons.json", get_missing_persons_collection, "missing_persons"),
        ("face_vectors.json", get_face_vectors_collection, "face_vectors"),
        ("sightings.json", get_sightings_collection, "sightings"),
        ("match_results.json", get_match_results_collection, "match_results"),
        ("case_history.json", get_case_history_collection, "case_history")
    ]
    
    date_fields = {
        "created_at", "updated_at", "last_seen_date", 
        "sighting_time", "matched_at", "timestamp"
    }
    
    try:
        for filename, get_coll_func, label in mappings:
            file_path = os.path.join(JSON_DB_DIR, filename)
            coll = get_coll_func()
            
            # Clear existing data
            print(f"Clearing collection '{label}'...")
            coll.delete_many({})
            
            if os.path.exists(file_path):
                print(f"Seeding collection '{label}' from {filename}...")
                with open(file_path, "r") as f:
                    items = json.load(f)
                
                if items:
                    # Convert date strings to python datetime objects
                    for item in items:
                        for field in date_fields:
                            if field in item:
                                item[field] = parse_date(item[field])
                    
                    coll.insert_many(items)
                    print(f"Successfully seeded {len(items)} documents in '{label}'.")
                else:
                    print(f"Source file {filename} is empty. Skipped seeding.")
            else:
                print(f"WARNING: Seed file {filename} not found at {file_path}. Skipped.")
                
        print("\nSUCCESS: MongoDB database successfully seeded from JSON files!")
        return True
    except Exception as e:
        print(f"\nERROR: Failed to seed MongoDB: {e}")
        return False

if __name__ == "__main__":
    seed_mongo_database()
