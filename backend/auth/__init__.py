# Authentication & Authorization Module
from .authentication import authenticate_user, login_user, logout_user, get_current_user, is_authenticated
from .permissions import (
    # Constants
    ROLE_ADMIN, ROLE_OFFICER,
    # Page guards
    require_auth, require_role,
    # Role checkers
    is_admin, is_officer,
    # Session-aware permission checks
    can_create_case, can_view_all_cases, can_edit_case, can_delete_case,
    can_trigger_matching, can_process_video, can_review_match,
    can_view_map, can_manage_users, can_view_reports,
    # Service-layer authorization helpers
    authorize_view_cases, authorize_edit_case, authorize_delete_case,
    authorize_trigger_matching, authorize_process_video,
    authorize_review_match, authorize_manage_users,
)
