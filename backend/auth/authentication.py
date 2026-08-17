"""
Streamlit authentication helpers.
Bridges AuthService ↔ Streamlit session_state.
"""
import logging
import streamlit as st
from backend.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Keys managed by the auth system — used for complete session cleanup on logout.
AUTH_SESSION_KEYS = ("authenticated", "user")


def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticates a user by email and password via AuthService.

    Returns:
        dict  — user data on success
        None  — invalid email or wrong password

    Raises:
        ValueError    — account is inactive
        ConnectionError — database unreachable
    """
    auth_service = AuthService()
    user = auth_service.authenticate(email, password)
    return user.to_dict() if user else None


def login_user(user: dict):
    """
    Establishes an authenticated session.
    Stores only the minimum required user information in session_state.
    """
    st.session_state.authenticated = True
    st.session_state.user = {
        "id": user.get("id"),
        "username": user.get("username") or user.get("name"),
        "role": user.get("role"),
        "email": user.get("email"),
    }


def logout_user():
    """
    Completely clears all authentication-related session state
    and immediately redirects the user to the login page.
    """
    for key in AUTH_SESSION_KEYS:
        if key in st.session_state:
            del st.session_state[key]

    try:
        st.switch_page("pages/login.py")
    except Exception:
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()



def get_current_user() -> dict | None:
    """Returns the currently logged-in user dict, or None if not authenticated."""
    if is_authenticated():
        return st.session_state.get("user")
    return None


def is_authenticated() -> bool:
    """Returns True if the current session has an authenticated user."""
    return st.session_state.get("authenticated", False) is True
