"""
CaseService manages business logic for registering cases, tracking status changes,
editing cases, searching/filtering, soft deletion, and history timelines — all with
role-based authorization enforced at the service layer.

Every protected operation verifies the caller's role before proceeding.
Officer access is filtered by `created_by` ownership — not only at the UI layer.
"""
import os
import uuid
import io
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from backend.repositories.case_repository import CaseRepository
from backend.models import MissingPerson, CaseHistory
from backend.auth.permissions import (
    authorize_view_cases,
    authorize_edit_case,
    authorize_delete_case,
)
from backend.utils.validators import validate_registration_payload, STATUS_ACTIVE


UPLOAD_ROOT = "data/uploads"
# Max retries for unique case_number on DuplicateKeyError (in case of race)
MAX_CASE_NUMBER_RETRIES = 5


def _to_relative_path(abs_path: str) -> str:
    """Normalizes an absolute filesystem path to project-relative POSIX form."""
    if abs_path is None:
        return ""
    cwd = os.path.abspath(os.getcwd())
    norm = os.path.normpath(os.path.abspath(abs_path))
    if norm.lower().startswith(cwd.lower()):
        rel = os.path.relpath(norm, cwd)
        return rel.replace("\\", "/")
    # Fallback: just return POSIX form
    return norm.replace("\\", "/")


def _save_photo_bytes(raw_bytes: bytes, original_extension: str) -> str:
    """
    Persists an uploaded photograph to disk under data/uploads/.

    NEVER uses the client-supplied filename. The stored filename is a UUID.
    Returns a PROJECT-RELATIVE path (e.g. "data/uploads/abc123.jpg") suitable
    for storage in MongoDB.
    """
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    safe_ext = ""
    if original_extension:
        # Sanitize extension (only allow alphanumerics, no path characters)
        raw_ext = original_extension.lower().replace("jpeg", "jpg")
        allowed = {".png", ".jpg", ".jpeg", ".webp"}
        if raw_ext in allowed:
            safe_ext = raw_ext
    unique_filename = f"{uuid.uuid4().hex}{safe_ext}"
    target_abs = os.path.abspath(os.path.join(UPLOAD_ROOT, unique_filename))
    with open(target_abs, "wb") as f:
        f.write(raw_bytes)
    return _to_relative_path(target_abs)


class CaseService:
    def __init__(self, case_repo: CaseRepository = None, case_repository: CaseRepository = None):
        self.case_repo = case_repo or case_repository or CaseRepository()

    # ------------------------------------------------------------------
    # New registration workflow — full field set, validates, saves photo
    # ------------------------------------------------------------------

    def register_missing_person(
        self,
        *,
        name: str,
        age: int,
        gender: str,
        description: str,
        last_seen_date: datetime,
        last_seen_location: str,
        state: str,
        city: str,
        contact_name: str,
        contact_email: str,
        contact_phone: str,
        photo_bytes: bytes,
        photo_filename: str,
        current_user: dict,
    ) -> MissingPerson:
        """
        The canonical registration flow for a Missing Person bulletin.

        Steps (in order):
          1. AUTH — verifies caller is Admin or Officer (raises PermissionError).
          2. VALIDATE — runs validate_registration_payload (all required fields).
          3. PHOTO FILE — generates safe UUID filename, writes to data/uploads/,
             returns only the relative path.
          4. CASE NUMBER — generates MP-YYYY-XXXXX via the repository; retries
             on DuplicateKeyError up to MAX_CASE_NUMBER_RETRIES times.
          5. PERSIST CASE — initial status = ACTIVE, created_by = user's user ID.
          6. HISTORY — logs a 'CASE_CREATED' entry.

        Does NOT: run face detection, KNN matching, send email, auto-process.
        """
        # 1) Auth + derive creator identity
        if current_user is None:
            raise PermissionError("Registration requires an authenticated user.")
        role = str(current_user.get("role", "")).lower()
        if role not in ("admin", "officer"):
            raise PermissionError(f"Role '{role}' is not authorized to register cases.")

        # We store created_by as the authenticated user's ID per requirement.
        creator_id = current_user.get("id") or current_user.get("_id") or current_user.get("username")
        creator_str = str(creator_id) if creator_id is not None else None
        if not creator_str:
            raise PermissionError("Authenticated user is missing an identifier; cannot register case.")
        creator_username = current_user.get("username") or creator_str

        # 2) Full payload validation
        payload = {
            "name": name,
            "age": age,
            "gender": gender,
            "description": description,
            "last_seen_date": last_seen_date,
            "last_seen_location": last_seen_location,
            "state": state,
            "city": city,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "photo_skip_validation": True,
            "has_upload": bool(photo_bytes),
        }
        valid, errors = validate_registration_payload(payload)
        if not valid:
            raise ValueError("; ".join(errors))
        if not photo_bytes:
            raise ValueError("A photograph is required to register a missing person bulletin.")

        # 3) Save photograph to disk (NEVER use original filename in storage)
        _, ext = os.path.splitext(photo_filename or "")
        photo_relative_path = _save_photo_bytes(photo_bytes, ext)

        # 4) Build case & generate unique case_number (retry on collision)
        last_attempt_error = None
        saved_case = None
        for attempt in range(MAX_CASE_NUMBER_RETRIES):
            new_case = MissingPerson(
                name=name,
                age=age,
                gender=gender,
                last_seen_location=last_seen_location,
                last_seen_date=last_seen_date,
                last_seen_state=state,
                last_seen_city=city,
                description=description,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                photo_path=photo_relative_path,
                status=STATUS_ACTIVE,
                created_by=creator_str,
                # id is assigned by case_repo.create()
            )
            new_case.case_number = self.case_repo.get_next_case_number(
                year=(last_seen_date.year if last_seen_date else None)
            )

            try:
                saved_case = self.case_repo.create(new_case)
                last_attempt_error = None
                break
            except DuplicateKeyError as dke:
                last_attempt_error = dke
                # Race: case_number collided despite our in-memory check.
                # Loop will generate the NEXT suffix for the same year and retry.
                continue

        if saved_case is None:
            # Couldn't get a unique case_number after retries
            msg = f"Failed to generate a unique case_number after {MAX_CASE_NUMBER_RETRIES} attempts."
            if last_attempt_error:
                msg += f" Last error: {last_attempt_error}"
            raise RuntimeError(msg)

        # 6) Log creation history (includes creator identifier)
        self.case_repo.log_history(CaseHistory(
            case_id=saved_case.id,
            action="CASE_CREATED",
            previous_status=None,
            new_status=STATUS_ACTIVE,
            performed_by=creator_username,
            details=(
                f"Bulletin created for '{name}'. Status set to {STATUS_ACTIVE}. "
                f"Case number: {saved_case.case_number}. "
                f"Created by user id: {creator_str} (username: {creator_username})."
            ),
        ))

        return saved_case

    # ------------------------------------------------------------------
    # Case Registration (Admin + Officer) — LEGACY helper
    # ------------------------------------------------------------------

    def register_case(self, name: str, age: int, gender: str, last_seen_location: str,
                      contact_number: str = "", description: str = "", photo_path: str = "",
                      reporter_name: str = "", reporter_contact: str = "",
                      last_seen_date: datetime = None, created_by: str = None,
                      current_user: dict = None) -> MissingPerson:
        """
        Registers a new missing person bulletin and logs history.

        Args:
            current_user: The authenticated user dict. If provided, role is checked
                          (Admin or Officer). The case's created_by is set to the
                          user's username to enable ownership tracking.
        """
        if current_user is not None:
            role = current_user.get("role", "")
            if role not in ("admin", "officer"):
                raise PermissionError(f"Role '{role}' is not authorized to register cases.")
            # Always stamp ownership from the authenticated user
            created_by = current_user.get("username") or created_by

        new_case = MissingPerson(
            name=name,
            age=age,
            gender=gender,
            last_seen_location=last_seen_location,
            contact_number=contact_number,
            description=description,
            photo_path=photo_path,
            reporter_name=reporter_name,
            reporter_contact=reporter_contact,
            last_seen_date=last_seen_date,
            created_by=created_by
        )
        saved_case = self.case_repo.create(new_case)

        # Log history (legacy strings for backward compat — legacy helper path)
        history_log = CaseHistory(
            case_id=saved_case.id,
            action="Case Created",
            previous_status=None,
            new_status=saved_case.status,
            performed_by=created_by or "system",
            details=f"Bulletin created for {name} by {created_by or 'system'}."
        )
        self.case_repo.log_history(history_log)

        return saved_case

    # ------------------------------------------------------------------
    # Case Retrieval (role-filtered)
    # ------------------------------------------------------------------

    def get_case(self, case_id: int, current_user: dict = None) -> MissingPerson:
        """
        Retrieves a single case.
        If current_user is provided, Officers can only view their own cases.
        Raises PermissionError for unauthenticated / unauthorized access.
        """
        if current_user is None:
            raise PermissionError("Viewing cases requires an authenticated user.")
        case = self.case_repo.get_by_id(case_id)
        if case is None:
            return None

        role = current_user.get("role", "")
        if role == "officer":
            username = current_user.get("username", "")
            if case.created_by != username:
                raise PermissionError("Officers can only view their own cases.")

        return case

    def get_all_cases(self, filter_query: dict = None, current_user: dict = None):
        """
        Retrieves cases filtered by role.
        Admin → all cases (optionally with filter_query).
        Officer → only own cases (created_by = username), merged with filter_query.

        Raises PermissionError for unauthenticated users or unauthorized roles.
        """
        if current_user is None:
            raise PermissionError("Listing cases requires an authenticated user.")
        role_filter = authorize_view_cases(current_user)
        if role_filter is not None:
            if filter_query is None:
                filter_query = {}
            filter_query.update(role_filter)

        return self.case_repo.get_all(filter_query)

    def search_and_filter_cases(
        self,
        search_term: str = "",
        status: str = None,
        gender: str = None,
        state: str = None,
        city: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        current_user: dict = None,
    ):
        """
        Combines text search (case_number, name, city, state) + attribute filters
        (status, gender, state, city, last_seen_date range) with role-based
        ownership enforcement.

        Admin → all matching cases.
        Officer → only own matching cases (enforced via authorize_view_cases).

        Raises PermissionError for unauthenticated / unauthorized roles.
        """
        if current_user is None:
            raise PermissionError("Searching cases requires an authenticated user.")

        # Build attribute filters
        filter_query = self.case_repo.build_filter_query(
            status=status,
            gender=gender,
            state=state,
            city=city,
            date_from=date_from,
            date_to=date_to,
        )

        # Apply role-based ownership restriction
        role_filter = authorize_view_cases(current_user)
        if role_filter is not None:
            filter_query.update(role_filter)

        # Delegate to repository search (which also excludes soft-deleted)
        return self.case_repo.search(search_term, filter_query=filter_query)

    # ------------------------------------------------------------------
    # Case Update (Admin: any case, Officer: own cases only)
    # ------------------------------------------------------------------

    def update_case_status(self, case_id: int, status: str, updated_by: str = "system",
                           current_user: dict = None) -> bool:
        """
        Updates case status and registers case history log.
        Enforces ownership check for Officers.
        """
        case = self.case_repo.get_by_id(case_id)
        if not case:
            return False

        if current_user is not None:
            authorize_edit_case(current_user, case.created_by)
            updated_by = current_user.get("username", updated_by)

        old_status = case.status
        if old_status == status:
            return True

        success = self.case_repo.update_status(case_id, status)
        if success:
            # Use legacy action string for backward compatibility — this method is
            # the legacy status-only update path. Full edit() emits CASE_STATUS_CHANGED.
            self.case_repo.log_history(CaseHistory(
                case_id=case_id,
                action="Status Changed",
                previous_status=old_status,
                new_status=status,
                performed_by=updated_by,
                details=f"Status transitioned from {old_status} to {status} by {updated_by}.",
            ))
        return bool(success)

    def edit_case(
        self,
        case_id: int,
        *,
        name: str = None,
        age: int = None,
        gender: str = None,
        description: str = None,
        last_seen_date: datetime = None,
        last_seen_location: str = None,
        state: str = None,
        city: str = None,
        contact_name: str = None,
        contact_email: str = None,
        contact_phone: str = None,
        status: str = None,
        photo_bytes: bytes = None,
        photo_filename: str = None,
        current_user: dict = None,
    ) -> MissingPerson:
        """
        Edits an existing case. Applies RBAC (Admin edits any, Officer edits own).
        Preserves `case_number`, `created_by`, `created_at`, `is_deleted`, `deleted_at`.
        Updates `updated_at` automatically.
        Logs CASE_UPDATED (and CASE_STATUS_CHANGED if status changed) to case_history.
        Returns the updated MissingPerson.
        """
        if current_user is None:
            raise PermissionError("Editing requires an authenticated user.")

        existing = self.case_repo.get_by_id(case_id)
        if not existing:
            return None

        # Authorize edit (raises PermissionError if denied)
        authorize_edit_case(current_user, existing.created_by)
        performer = current_user.get("username", "system")

        # Track changes for history details
        changes = []
        old_status = existing.status
        status_changed = False

        if name is not None and name != existing.name:
            changes.append(f"name: '{existing.name}' → '{name}'")
            existing.name = name
        if age is not None and age != existing.age:
            changes.append(f"age: {existing.age} → {age}")
            existing.age = age
        if gender is not None and gender != existing.gender:
            changes.append(f"gender: {existing.gender} → {gender}")
            existing.gender = gender
        if description is not None and description != existing.description:
            changes.append("description updated")
            existing.description = description
        if last_seen_date is not None and last_seen_date != existing.last_seen_date:
            changes.append(f"last_seen_date: {existing.last_seen_date} → {last_seen_date}")
            existing.last_seen_date = last_seen_date
        if last_seen_location is not None and last_seen_location != existing.last_seen_location:
            changes.append(f"last_seen_location updated")
            existing.last_seen_location = last_seen_location
        if state is not None and state != existing.last_seen_state:
            changes.append(f"state: {existing.last_seen_state} → {state}")
            existing.last_seen_state = state
        if city is not None and city != existing.last_seen_city:
            changes.append(f"city: {existing.last_seen_city} → {city}")
            existing.last_seen_city = city
        if contact_name is not None and contact_name != existing.contact_name:
            changes.append("contact_name updated")
            existing.contact_name = contact_name
        if contact_email is not None and contact_email != existing.contact_email:
            changes.append("contact_email updated")
            existing.contact_email = contact_email
        if contact_phone is not None and contact_phone != existing.contact_phone:
            changes.append("contact_phone updated")
            existing.contact_phone = contact_phone
        if status is not None and status != existing.status:
            changes.append(f"status: {existing.status} → {status}")
            existing.status = status
            status_changed = True
        if photo_bytes is not None:
            _, ext = os.path.splitext(photo_filename or "")
            new_photo_path = _save_photo_bytes(photo_bytes, ext)
            existing.photo_path = new_photo_path
            changes.append("photograph replaced")

        # Preserve immutable fields explicitly
        # (case_number, created_by, created_at, is_deleted, deleted_at, id)
        # They are already untouched on the existing object, but we reaffirm.
        # case_number and created_by are not in the editable list above.

        if not changes:
            # Nothing to do — still return the current state
            return existing

        updated_case = self.case_repo.update(existing)

        # Log CASE_UPDATED history
        self.case_repo.log_history(CaseHistory(
            case_id=case_id,
            action="CASE_UPDATED",
            previous_status=old_status,
            new_status=updated_case.status,
            performed_by=performer,
            details=(
                f"Fields modified by {performer}: {'; '.join(changes)}. "
                f"Case number: {updated_case.case_number} (preserved)."
            ),
        ))

        # If status was one of the changed fields, also emit a dedicated
        # CASE_STATUS_CHANGED record for audit clarity.
        if status_changed:
            self.case_repo.log_history(CaseHistory(
                case_id=case_id,
                action="CASE_STATUS_CHANGED",
                previous_status=old_status,
                new_status=updated_case.status,
                performed_by=performer,
                details=(
                    f"Status transitioned from {old_status} to {updated_case.status} "
                    f"during case edit by {performer}."
                ),
            ))

        return updated_case

    # ------------------------------------------------------------------
    # Case Deletion (Admin only — soft delete preferred)
    # ------------------------------------------------------------------

    def delete_case(self, case_id: int, current_user: dict = None) -> bool:
        """
        Soft-deletes a case. Only Admin is authorized.
        Records CASE_DELETED in case_history.
        Raises PermissionError for non-Admin roles.
        """
        if current_user is not None:
            authorize_delete_case(current_user)
            performer = current_user.get("username", "admin")
        else:
            performer = "system"

        # Fetch first to ensure case exists and capture status
        existing = self.case_repo.get_by_id(case_id, include_deleted=False)
        if not existing:
            return False

        old_status = existing.status
        case_number = existing.case_number

        success = self.case_repo.soft_delete(case_id)
        if success:
            self.case_repo.log_history(CaseHistory(
                case_id=case_id,
                action="CASE_DELETED",
                previous_status=old_status,
                new_status=None,
                performed_by=performer,
                details=(
                    f"Case {case_number} (id={case_id}) soft-deleted by {performer}. "
                    f"Previous status: {old_status}. Photograph preserved on disk for audit."
                ),
            ))
        return bool(success)

    def hard_delete_case(self, case_id: int, current_user: dict = None) -> bool:
        """
        Permanently deletes a case (physical removal). Admin only.
        Use with caution — prefer delete_case (soft delete) for auditability.
        """
        if current_user is not None:
            authorize_delete_case(current_user)
        return self.case_repo.delete(case_id)

    # ------------------------------------------------------------------
    # Case Timeline (inherits view permission)
    # ------------------------------------------------------------------

    def get_case_timeline(self, case_id: int, current_user: dict = None):
        """
        Returns the history timeline for a case.
        Officers can only view timelines for their own cases.
        """
        if current_user is not None:
            # This implicitly checks ownership for officers
            self.get_case(case_id, current_user=current_user)

        return self.case_repo.get_history_by_case(case_id)

    # ------------------------------------------------------------------
    # Convenience: reference data for filter dropdowns
    # ------------------------------------------------------------------

    def get_available_states(self) -> list:
        return self.case_repo.get_unique_states()

    def get_available_cities(self, state: str = None) -> list:
        return self.case_repo.get_unique_cities(state=state)

    def attach_face_vector(
        self, case_id: int, image_input=None, current_user: dict = None
    ):
        """
        Modular integration point for registering/updating a case's face vector.
        Uses FaceStorageService to detect face, extract 1,404-D vector, and store in MongoDB.
        Does not break existing case registration if no face is detected or if image is missing.
        """
        from backend.services.face_storage_service import FaceStorageService

        if current_user is not None:
            self.get_case(case_id, current_user=current_user)

        case = self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Case with ID {case_id} not found.")

        target_image = image_input or case.photo_path
        if not target_image:
            raise ValueError(f"No photo available for case ID {case_id}.")

        storage_service = FaceStorageService(case_repo=self.case_repo)
        return storage_service.process_and_store_image(
            case_id=case_id,
            image_input=target_image,
            prevent_duplicates=True,
        )

