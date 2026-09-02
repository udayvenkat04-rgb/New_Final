import os
import streamlit as st
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

def _raw_check_db():
    try:
        client = get_mongo_client()
        client.admin.command('ping')
        return True, "MongoDB connection is healthy."
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return False, f"Could not connect to MongoDB: {str(e)}"
    except Exception as e:
        return False, f"Database error: {str(e)}"

def check_database_connection():
    """
    Health-check function to check MongoDB connection status.
    Returns (True, success_msg) if available, else (False, error_msg).
    """
    try:
        # If in Streamlit runtime, cache health check for 15 seconds to keep navigation instant
        if hasattr(st, "cache_data"):
            return _cached_check_db()
    except Exception:
        pass
    return _raw_check_db()

@st.cache_data(ttl=15, show_spinner=False)
def _cached_check_db():
    return _raw_check_db()

# Alias check_connection for backwards compatibility with existing UI pages
check_connection = check_database_connection

def close_database_connection():
    """Closes the MongoDB connection and resets the client singleton."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
    return True

