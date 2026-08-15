"""
Role-based authorization system.

Provides:
- Streamlit page guards: require_auth(), require_role()
- Role checkers: is_admin(), is_officer()
- Permission functions: can_view_all_cases(), can_create_case(), can_edit_case(),
  can_delete_case(), can_trigger_matching(), can_review_match(), can_view_map(),
  can_process_video(), can_manage_users(), can_view_reports()

All permission checks read the current user from st.session_state.
Service-layer authorization uses the user dict passed explicitly (no Streamlit dependency).
"""
import streamlit as st


# ──────────────────────────────────────────────────────────────────────
# Role constants
# ──────────────────────────────────────────────────────────────────────

ROLE_ADMIN = "admin"
ROLE_OFFICER = "officer"

# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────

def _current_role() -> str:
    """Returns the role of the current session user, or empty string."""
    user = st.session_state.get("user")
    if user:
        return user.get("role", "")
    return ""


def _current_user_id():
    """Returns the ID of the current session user, or None."""
    user = st.session_state.get("user")
    if user:
        return user.get("id")
    return None


def _current_username() -> str:
    """Returns the username of the current session user, or empty string."""
    user = st.session_state.get("user")
    if user:
        return user.get("username", "")
    return ""


# ──────────────────────────────────────────────────────────────────────
# Streamlit page guards (call at the top of a page; halts rendering)
# ──────────────────────────────────────────────────────────────────────

def require_auth():
    """
    Reusable authentication guard.
    Halts page rendering if the user is not logged in.
    Returns True if authenticated.
    """
    if not st.session_state.get("authenticated", False):
        st.error("🔒 Authentication Required. Please log in to proceed.")
        st.stop()
    return True


def require_role(allowed_roles=None):
    """
    Asserts that a user is logged in and has one of the allowed roles.
    If unauthorized, displays warning/error banner and halts further rendering.
    """
    if allowed_roles is None:
        allowed_roles = [ROLE_ADMIN, ROLE_OFFICER]

    require_auth()

    user_role = _current_role()
    if user_role not in allowed_roles:
        st.error(
            f"⚠️ Access Denied. Role '{user_role.upper()}' is not authorized to access this page."
        )
        st.stop()

    return True


# ──────────────────────────────────────────────────────────────────────
# Role checkers
# ──────────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    """Returns True if the current session user is an Admin."""
    return _current_role() == ROLE_ADMIN


def is_officer() -> bool:
    """Returns True if the current session user is an Officer."""
    return _current_role() == ROLE_OFFICER


# ──────────────────────────────────────────────────────────────────────
# Permission functions (session-aware — read from st.session_state)
# ──────────────────────────────────────────────────────────────────────

def can_create_case() -> bool:
    """Both Admin and Officer can register missing-person cases."""
    return _current_role() in (ROLE_ADMIN, ROLE_OFFICER)


def can_view_all_cases() -> bool:
    """Only Admin can view ALL cases across all officers."""
    return _current_role() == ROLE_ADMIN


def can_edit_case(case_created_by: str = None) -> bool:
    """
    Admin can edit any case.
    Officer can only edit cases they created.

    Args:
        case_created_by: The username of the officer who created the case.
                         Required for Officer role checks.
    """
    role = _current_role()
    if role == ROLE_ADMIN:
        return True
    if role == ROLE_OFFICER:
        if case_created_by is None:
            return False
        return _current_username() == case_created_by
    return False


def can_delete_case() -> bool:
    """Only Admin can delete cases."""
    return _current_role() == ROLE_ADMIN


def can_trigger_matching() -> bool:
    """Only Admin can trigger face matching."""
    return _current_role() == ROLE_ADMIN


def can_process_video() -> bool:
    """Only Admin can process video sightings."""
    return _current_role() == ROLE_ADMIN


def can_review_match() -> bool:
    """Only Admin can review (confirm/reject) potential matches."""
    return _current_role() == ROLE_ADMIN


def can_view_map() -> bool:
    """Only Admin can view the India sightings map."""
    return _current_role() == ROLE_ADMIN


def can_manage_users() -> bool:
    """Only Admin can manage authorized users."""
    return _current_role() == ROLE_ADMIN


def can_view_reports() -> bool:
    """Only Admin can view reports."""
    return _current_role() == ROLE_ADMIN


# ──────────────────────────────────────────────────────────────────────
# Service-layer authorization helpers (no Streamlit dependency)
#
# These accept an explicit user dict so they can be called from service
# code and tests without needing st.session_state.
# ──────────────────────────────────────────────────────────────────────

def authorize_view_cases(user: dict) -> dict | None:
    """
    Returns a MongoDB filter dict that restricts case visibility by role.
    Admin → None (no filter = see all).
    Officer → {"created_by": <username>} (own cases only).

    Raises PermissionError if the user has no case-viewing rights.
    """
    role = user.get("role", "")
    if role == ROLE_ADMIN:
        return None  # no restriction
    if role == ROLE_OFFICER:
        username = user.get("username", "")
        if not username:
            raise PermissionError("Officer user is missing a username.")
        return {"created_by": username}
    raise PermissionError(f"Role '{role}' is not authorized to view cases.")


def authorize_edit_case(user: dict, case_created_by: str) -> bool:
    """
    Returns True if the user is allowed to edit this case.
    Raises PermissionError if not.
    """
    role = user.get("role", "")
    if role == ROLE_ADMIN:
        return True
    if role == ROLE_OFFICER:
        username = user.get("username", "")
        if username and username == case_created_by:
            return True
        raise PermissionError("Officers can only edit their own cases.")
    raise PermissionError(f"Role '{role}' is not authorized to edit cases.")


def authorize_delete_case(user: dict) -> bool:
    """Only Admin. Raises PermissionError otherwise."""
    if user.get("role") == ROLE_ADMIN:
        return True
    raise PermissionError("Only administrators can delete cases.")


def authorize_trigger_matching(user: dict) -> bool:
    """Only Admin. Raises PermissionError otherwise."""
    if user.get("role") == ROLE_ADMIN:
        return True
    raise PermissionError("Only administrators can trigger face matching.")


def authorize_process_video(user: dict) -> bool:
    """Only Admin. Raises PermissionError otherwise."""
    if user.get("role") == ROLE_ADMIN:
        return True
    raise PermissionError("Only administrators can process video sightings.")


def authorize_review_match(user: dict) -> bool:
    """Only Admin. Raises PermissionError otherwise."""
    if user.get("role") == ROLE_ADMIN:
        return True
    raise PermissionError("Only administrators can review matches.")


def authorize_manage_users(user: dict) -> bool:
    """Only Admin. Raises PermissionError otherwise."""
    if user.get("role") == ROLE_ADMIN:
        return True
    raise PermissionError("Only administrators can manage users.")
