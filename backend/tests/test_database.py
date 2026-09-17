import pytest
from database.connection import get_client, get_database, check_connection, check_database_connection
from database.collections import (
    get_users_collection,
    get_missing_persons_collection,
    get_face_vectors_collection,
    get_sightings_collection,
    get_match_results_collection,
    get_case_history_collection
)

def test_mongodb_connection():
    """Verifies that we can connect to the MongoDB instance and ping it successfully."""
    connected, msg = check_database_connection()
    assert connected is True, f"MongoDB connection check failed: {msg}. Please ensure MongoDB is running."
    
    # Also verify legacy alias
    alias_connected, alias_msg = check_connection()
    assert alias_connected is True

def test_database_access():
    """Verifies that we can access the target MongoDB database and get its name."""
    db = get_database()
    assert db is not None
    assert db.name == "missing_person_db"

def test_collection_access():
    """Verifies that collection getters return collection references and index setup works."""
    users = get_users_collection()
    missing_persons = get_missing_persons_collection()
    face_vectors = get_face_vectors_collection()
    sightings = get_sightings_collection()
    match_results = get_match_results_collection()
    case_history = get_case_history_collection()
    
    # Assert collection names are correct
    assert users.name == "users"
    assert missing_persons.name == "missing_persons"
    assert face_vectors.name == "face_vectors"
    assert sightings.name == "sightings"
    assert match_results.name == "match_results"
    assert case_history.name == "case_history"
    
    # Assert we can query them without errors (even if empty)
    assert isinstance(users.count_documents({}), int)
    assert isinstance(missing_persons.count_documents({}), int)

def test_crud_operations():
    """Verifies basic write, read, and delete operations on a collection."""
    coll = get_users_collection()
    
    # Clean any leftover test documents
    coll.delete_many({"id": 9999})
    
    # Insert test document
    test_user = {
        "id": 9999,
        "username": "test_mongo_user",
        "email": "test_mongo@example.com",
        "role": "officer"
    }
    
    insert_result = coll.insert_one(test_user)
    assert insert_result.acknowledged is True
    
    # Read
    fetched = coll.find_one({"id": 9999})
    assert fetched is not None
    assert fetched["username"] == "test_mongo_user"
    assert fetched["email"] == "test_mongo@example.com"
    
    # Delete
    delete_result = coll.delete_one({"id": 9999})
    assert delete_result.deleted_count == 1
