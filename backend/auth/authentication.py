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
    Stores user info in session_state and syncs session tokens to query_params to preserve state on browser refresh.
    """
    st.session_state.authenticated = True
    st.session_state.user = {
        "id": user.get("id"),
        "username": user.get("username") or user.get("name"),
        "role": user.get("role"),
        "email": user.get("email"),
    }
    try:
        if hasattr(st, "query_params"):
            st.query_params["auth_role"] = user.get("role", "")
            st.query_params["auth_user"] = user.get("username") or user.get("name", "")
            st.query_params["auth_email"] = user.get("email", "")
            st.query_params["auth_id"] = str(user.get("id", ""))
    except Exception:
        pass


def restore_session_if_needed():
    """Restores authenticated session state from query_params on browser refresh if not initialized."""
    import os
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return

    if "authenticated" not in st.session_state:
        try:
            if hasattr(st, "query_params"):
                role = st.query_params.get("auth_role")
                username = st.query_params.get("auth_user")
                email = st.query_params.get("auth_email")
                user_id = st.query_params.get("auth_id")
                if role and username:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = {
                        "id": user_id,
                        "username": username,
                        "role": role,
                        "email": email,
                    }
        except Exception:
            pass


def logout_user():
    """
    Completely clears all authentication-related session state and query params,
    and immediately redirects the user to the login page.
    """
    for key in AUTH_SESSION_KEYS:
        if key in st.session_state:
            del st.session_state[key]

    try:
        if hasattr(st, "query_params"):
            if hasattr(st.query_params, "clear"):
                st.query_params.clear()
            else:
                for k in ["auth_role", "auth_user", "auth_email", "auth_id"]:
                    if k in st.query_params:
                        del st.query_params[k]
    except Exception:
        pass

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
    restore_session_if_needed()
    return st.session_state.get("authenticated", False) is True
