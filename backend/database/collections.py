from backend.database.connection import get_database

_indexes_initialized = False

def initialize_indexes(db):
    """
    Sets up required and recommended database indexes for query performance 
    and unique constraints.
    """
    global _indexes_initialized
    if _indexes_initialized:
        return
    try:
        # Unique constraints
        db.users.create_index("email", unique=True)
        db.missing_persons.create_index("case_number", unique=True, sparse=True)
        
        # Recommended indexes for query optimization
        db.missing_persons.create_index("created_by")
        db.missing_persons.create_index("status")
        db.missing_persons.create_index("last_seen_city")
        db.missing_persons.create_index("last_seen_state")
        
        db.face_vectors.create_index("case_id")
        db.match_results.create_index("case_id")
        db.match_results.create_index("status")
        db.sightings.create_index("case_id")
        
        _indexes_initialized = True
        print("[MONGO] Indexes initialized successfully.")
    except Exception as e:
        # We fail gracefully and log it rather than raising during connection setup
        print(f"[MONGO] Index setup warning: {str(e)}")

def get_collection(name: str):
    """Helper to retrieve a MongoDB collection and guarantee index health."""
    db = get_database()
    initialize_indexes(db)
    return db[name]

def get_users_collection():
    return get_collection("users")

def get_missing_persons_collection():
    return get_collection("missing_persons")

def get_face_vectors_collection():
    return get_collection("face_vectors")

def get_sightings_collection():
    return get_collection("sightings")

def get_match_results_collection():
    return get_collection("match_results")

def get_case_history_collection():
    return get_collection("case_history")
