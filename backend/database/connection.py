import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from backend.config.settings import DATABASE_URL, DATABASE_NAME

_client = None

def get_mongo_client() -> MongoClient:
    """Retrieves or creates a singleton MongoClient instance."""
    global _client
    if _client is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not configured in settings.")
        # Set a 2-second server selection timeout so Streamlit UI doesn't hang indefinitely
        _client = MongoClient(DATABASE_URL, serverSelectionTimeoutMS=2000)
    return _client

# Alias get_client for backwards compatibility with existing repositories and tests
get_client = get_mongo_client

def get_database():
    """Retrieves the MongoDB database instance."""
    client = get_mongo_client()
    return client[DATABASE_NAME]

def check_database_connection():
    """
    Health-check function to check MongoDB connection status.
    Returns (True, success_msg) if available, else (False, error_msg).
    """
    try:
        client = get_mongo_client()
        # The admin command 'ping' is a low-overhead connection check
        client.admin.command('ping')
        return True, "MongoDB connection is healthy."
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return False, f"Could not connect to MongoDB: {str(e)}"
    except Exception as e:
        return False, f"Database error: {str(e)}"

# Alias check_connection for backwards compatibility with existing UI pages
check_connection = check_database_connection

def close_database_connection():
    """Closes the MongoDB connection and resets the client singleton."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
    return True

