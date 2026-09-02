"""
DashboardService aggregates statistics and recent items for the Admin and Officer Dashboards.

All data comes from MongoDB via the repository layer — no fake/hardcoded values.
No MongoDB queries are built here; counting and filtering is delegated to repositories.

Officer enforcement:
  Every officer-scoped method applies the ownership filter from authorize_view_cases,
  which returns {"created_by": officer_username}. This filter is merged into EVERY
  repository query — the database, not the UI, does the filtering so an officer can
  never accidentally receive another officer's rows.
"""
from backend.repositories.case_repository import CaseRepository
from backend.repositories.match_repository import MatchRepository
from backend.repositories.sighting_repository import SightingRepository
from backend.auth.permissions import authorize_view_cases


class DashboardService:
    def __init__(self, case_repo=None, match_repo=None, sighting_repo=None):
        self.case_repo = case_repo or CaseRepository()
        self.match_repo = match_repo or MatchRepository()
        self.sighting_repo = sighting_repo or SightingRepository()

    # ------------------------------------------------------------------
    # Individual stat helpers (each maps to a repository count call)
    # ------------------------------------------------------------------

    def get_total_cases(self, current_user: dict = None) -> int:
        query = self._role_case_filter(current_user)
        return self.case_repo.count(query)

    def get_active_cases(self, current_user: dict = None) -> int:
        query = self._role_case_filter(current_user)
        query = query or {}
        query["status"] = {"$in": ["Missing", "MISSING", "Active", "ACTIVE", "ACTIVE_INVESTIGATION", "POTENTIAL_MATCH", "UNDER_MATCH_REVIEW", "MATCH_CONFIRMED", "REOPENED"]}
        return self.case_repo.count(query)

    def get_pending_cases(self, current_user: dict = None) -> int:
        """
        Pending = Missing (still active / not resolved).
        Synonym of get_active_cases — provided to match the officer dashboard
        naming ('My Pending Cases') without coupling the UI to status semantics.
        """
        return self.get_active_cases(current_user=current_user)

    def get_resolved_cases(self, current_user: dict = None) -> int:
        query = self._role_case_filter(current_user)
        query = query or {}
        query["status"] = {"$in": ["Found", "FOUND", "Resolved", "RESOLVED", "Closed", "CLOSED", "Reunited", "REUNITED"]}
        return self.case_repo.count(query)

    def get_pending_review_cases(self) -> int:
        return self.match_repo.count({"status": "Pending Review"})

    def get_potential_matches(self) -> int:
        return self.match_repo.count()

    def get_confirmed_matches(self) -> int:
        return self.match_repo.count({"status": "Confirmed Match"})

    def get_video_sightings(self) -> int:
        return self.sighting_repo.count_video_sightings()

    def get_total_sightings(self) -> int:
        return self.sighting_repo.count()

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def get_case_status_breakdown(self, current_user: dict = None) -> dict:
        """
        Returns a dict of {status: count} for cases, respecting role filtering.
        Admin → all cases. Officer → own cases only.
        """
        query = self._role_case_filter(current_user)
        if query is None:
            # No role restriction: use the aggregation pipeline in the repo
            return self.case_repo.count_by_status()

        # Officer: we need to filter *before* grouping. Load matching docs and count.
        docs = self.case_repo.get_all(query)
        breakdown = {}
        for c in docs:
            if not c.status:
                continue
            breakdown[c.status] = breakdown.get(c.status, 0) + 1
        return breakdown

    # ------------------------------------------------------------------
    # Recent items (already sorted descending by the repositories)
    # ------------------------------------------------------------------

    def get_recent_cases(self, limit: int = 5, current_user: dict = None):
        query = self._role_case_filter(current_user)
        if query is None:
            return self.case_repo.get_recent(limit=limit)

        docs = self.case_repo.get_all(query)
        return docs[:limit]

    def get_recent_matches(self, limit: int = 5):
        return self.match_repo.get_recent(limit=limit)

    # ------------------------------------------------------------------
    # Master payloads
    # ------------------------------------------------------------------

    def get_dashboard_data(self, current_user: dict = None) -> dict:
        """
        Returns the complete ADMIN dashboard data payload.
        """
        return {
            "total_cases": self.get_total_cases(current_user=current_user),
            "active_cases": self.get_active_cases(current_user=current_user),
            "resolved_cases": self.get_resolved_cases(current_user=current_user),
            "pending_review": self.get_pending_review_cases(),
            "potential_matches": self.get_potential_matches(),
            "confirmed_matches": self.get_confirmed_matches(),
            "video_sightings": self.get_video_sightings(),
            "total_sightings": self.get_total_sightings(),
            "recent_cases": self.get_recent_cases(limit=5, current_user=current_user),
            "recent_matches": self.get_recent_matches(limit=5),
            "case_status_breakdown": self.get_case_status_breakdown(current_user=current_user),
        }

    def get_officer_dashboard_data(self, current_user: dict) -> dict:
        """
        Returns the OFFICER dashboard payload.

        IMPORTANT: `current_user` is REQUIRED — without it we cannot enforce
        the ownership filter. This method explicitly passes the user through
        to every stat so every database query includes `created_by=<username>`.
        Raises PermissionError if the user role isn't authorized to view cases.
        """
        if current_user is None:
            raise PermissionError("Officer dashboard requires an authenticated user.")

        total = self.get_total_cases(current_user=current_user)
        active = self.get_active_cases(current_user=current_user)
        pending = self.get_pending_cases(current_user=current_user)
        resolved = self.get_resolved_cases(current_user=current_user)

        return {
            "my_total_cases": total,
            "my_active_cases": active,
            "my_pending_cases": pending,
            "my_resolved_cases": resolved,
            "my_recent_cases": self.get_recent_cases(limit=5, current_user=current_user),
            "my_case_status_breakdown": self.get_case_status_breakdown(current_user=current_user),
        }

    # ------------------------------------------------------------------
    # Internal role filter builder (raises PermissionError for bad roles)
    # ------------------------------------------------------------------

    @staticmethod
    def _role_case_filter(current_user: dict = None) -> dict | None:
        """
        Returns a MongoDB filter dict restricted by role, or None if no restriction.
        Uses the authorize_view_cases helper from the permissions module.

        Admin → None (no filter = see all).
        Officer → {"created_by": <username>} — ALWAYS injected into queries.
        Public/unauthorized → PermissionError raised inside authorize_view_cases.
        """
        if current_user is None:
            return None
        return authorize_view_cases(current_user)
