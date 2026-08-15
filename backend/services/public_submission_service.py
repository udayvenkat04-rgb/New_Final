"""
Public Submission Service for Missing Person Identification System (Phase 22).

Handles input validation, safe photo storage, submission reference generation,
duplicate candidate flagging, PENDING_VERIFICATION creation, and sanitized public status lookups.
"""

import os
import re
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from PIL import Image
import io

from backend.models.public_submission import PublicSubmission, PublicSubmissionAudit
from backend.repositories.public_submission_repository import PublicSubmissionRepository
from backend.config.settings import BASE_DIR

logger = logging.getLogger(__name__)

# Valid email regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
# Valid phone regex (7 to 15 digits allowing spaces/dashes)
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-]{7,15}$")

# Upload Storage Directory
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads", "public_submissions")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class PublicSubmissionService:
    def __init__(self, repository: Optional[PublicSubmissionRepository] = None):
        self.repository = repository or PublicSubmissionRepository()

    def validate_submission_data(
        self,
        form_data: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Validates public missing person report input fields and image file."""
        if form_data is None or not isinstance(form_data, dict):
            return False, "INVALID_FORM_DATA"

        # 1. Full Name
        full_name = str(form_data.get("full_name", "")).strip()
        if not full_name or len(full_name) < 2:
            return False, "INVALID_FULL_NAME: Full name must be at least 2 characters long."

        # 2. Age Range (0 < age <= 120)
        try:
            age = int(form_data.get("age", 0))
            if not (0 < age <= 120):
                return False, "INVALID_AGE: Age must be between 1 and 120."
        except (ValueError, TypeError):
            return False, "INVALID_AGE: Age must be a valid number between 1 and 120."

        # 3. Gender
        gender = str(form_data.get("gender", "")).strip()
        if not gender:
            return False, "INVALID_GENDER: Gender is required."

        # 4. Location Fields
        city = str(form_data.get("last_seen_city", "")).strip()
        state = str(form_data.get("last_seen_state", "")).strip()
        if not city:
            return False, "INVALID_CITY: Last seen city is required."
        if not state:
            return False, "INVALID_STATE: Last seen state is required."

        # 5. Complainant Contact Info
        comp_name = str(form_data.get("complainant_name", "")).strip()
        if not comp_name or len(comp_name) < 2:
            return False, "INVALID_COMPLAINANT_NAME: Complainant name is required."

        email = str(form_data.get("contact_email", "")).strip()
        if not email or not EMAIL_REGEX.match(email):
            return False, "INVALID_EMAIL: Please provide a valid email address."

        phone = str(form_data.get("contact_phone", "")).strip()
        if not phone or not PHONE_REGEX.match(phone):
            return False, "INVALID_PHONE: Please provide a valid contact phone number."

        # 6. Consent Checkbox
        consent = form_data.get("consent", False)
        if not consent:
            return False, "MISSING_CONSENT: You must confirm the declaration to submit a report."

        # 7. Image File Validation (If image bytes provided)
        if image_bytes is not None and len(image_bytes) > 0:
            if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                return False, "OVERSIZED_IMAGE: Image file size must not exceed 5 MB."

            if filename:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    return False, f"INVALID_IMAGE_TYPE: Only {', '.join(ALLOWED_EXTENSIONS)} images are allowed."

            # Verify image readability using PIL
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
            except Exception as e:
                logger.warning("Unreadable image file uploaded: %s", e)
                return False, "CORRUPTED_IMAGE: Uploaded image file is unreadable or corrupted."

        return True, "VALIDATION_SUCCESS"

    def generate_submission_reference(self) -> str:
        """Generates a unique user-safe submission reference code (e.g. MP-SUB-2026-104829)."""
        year_str = datetime.utcnow().strftime("%Y")
        for _ in range(20):
            rand_suffix = str(uuid.uuid4().int)[:6].zfill(6)
            ref = f"MP-SUB-{year_str}-{rand_suffix}"
            if not self.repository.get_submission_by_reference(ref):
                return ref

        # Fallback timestamp-based unique reference
        ts_suffix = str(int(datetime.utcnow().timestamp() * 1000))[-6:]
        return f"MP-SUB-{year_str}-{ts_suffix}"

    def save_uploaded_photo(self, image_bytes: bytes, filename: Optional[str] = None) -> Optional[str]:
        """Saves photo bytes securely to uploads/public_submissions and returns relative file path."""
        if not image_bytes:
            return None

        ext = ".jpg"
        if filename:
            clean_name = os.path.basename(str(filename))
            parsed_ext = os.path.splitext(clean_name)[1].lower()
            if parsed_ext in ALLOWED_EXTENSIONS:
                ext = parsed_ext

        safe_filename = f"public_sub_{uuid.uuid4().hex}{ext}"
        filepath = os.path.normpath(os.path.join(UPLOAD_DIR, safe_filename))

        try:
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            return filepath
        except Exception as e:
            logger.error("Failed to save uploaded public submission photo: %s", e)
            return None

    def create_public_submission(
        self,
        form_data: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates form data, saves photograph, checks for duplicate candidates,
        and persists PENDING_VERIFICATION submission. Returns sanitized public response.
        """
        # Validate Input
        valid, val_msg = self.validate_submission_data(form_data, image_bytes, filename)
        if not valid:
            return False, {"error": val_msg}

        # Save Photograph
        photo_path = None
        if image_bytes and len(image_bytes) > 0:
            photo_path = self.save_uploaded_photo(image_bytes, filename)

        # Generate Reference Code
        reference = self.generate_submission_reference()

        # Parse Date/Time
        last_seen_dt = form_data.get("last_seen_date")
        if isinstance(last_seen_dt, str):
            try:
                last_seen_dt = datetime.strptime(last_seen_dt.split("T")[0], "%Y-%m-%d")
            except ValueError:
                last_seen_dt = datetime.utcnow()
        elif not isinstance(last_seen_dt, datetime):
            last_seen_dt = datetime.utcnow()

        # Check Duplicate Candidate
        is_dup = self.repository.check_possible_duplicate(
            full_name=str(form_data.get("full_name", "")),
            age=int(form_data.get("age", 0)),
            city=form_data.get("last_seen_city"),
            state=form_data.get("last_seen_state"),
        )

        submission = PublicSubmission(
            submission_reference=reference,
            full_name=str(form_data.get("full_name", "")).strip(),
            age=int(form_data.get("age", 0)),
            gender=str(form_data.get("gender", "")).strip(),
            height=form_data.get("height"),
            identifying_features=form_data.get("identifying_features"),
            description=form_data.get("description"),
            last_seen_date=last_seen_dt,
            last_seen_time=form_data.get("last_seen_time"),
            last_seen_city=form_data.get("last_seen_city"),
            last_seen_state=form_data.get("last_seen_state"),
            last_seen_location=form_data.get("last_seen_location"),
            complainant_name=str(form_data.get("complainant_name", "")).strip(),
            relationship=form_data.get("relationship"),
            contact_email=str(form_data.get("contact_email", "")).strip(),
            contact_phone=str(form_data.get("contact_phone", "")).strip(),
            photo_path=photo_path,
            status="PENDING_VERIFICATION",
            is_possible_duplicate=is_dup,
        )

        # Save to Repository
        try:
            created_sub = self.repository.create_submission(submission)

            # Record Audit Entry
            audit = PublicSubmissionAudit(
                submission_id=created_sub.id,
                submission_reference=created_sub.submission_reference,
                action="SUBMITTED",
                actor_username="public_user",
                actor_role="public",
                new_status="PENDING_VERIFICATION",
                notes="Report submitted via public portal.",
            )
            self.repository.create_audit_record(audit)

            # Sanitized Public Response (Excludes private internal IDs, face vectors, email/phone)
            public_response = {
                "status": "SUCCESS",
                "message": "Your missing-person report has been submitted successfully.",
                "submission_reference": created_sub.submission_reference,
                "submission_status": created_sub.status,
                "is_possible_duplicate": created_sub.is_possible_duplicate,
                "created_at": created_sub.created_at.strftime("%Y-%m-%d %H:%M UTC") if created_sub.created_at else "",
            }
            return True, public_response

        except Exception as e:
            logger.error("Failed to create public submission record: %s", e)
            return False, {"error": "DATABASE_ERROR: Failed to save report."}

    def get_public_submission_status(self, reference: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Retrieves sanitized public status information by submission reference.
        Never exposes complainant email, phone, victim names, private notes, or internal IDs.
        """
        if not reference or not isinstance(reference, str):
            return False, {"error": "INVALID_REFERENCE: Please provide a valid submission reference."}

        sub = self.repository.get_submission_by_reference(reference.strip())
        if not sub:
            return False, {"error": "NOT_FOUND: No submission found for reference code."}

        status_messages = {
            "PENDING_VERIFICATION": "Your report has been received and is pending administrative review.",
            "UNDER_REVIEW": "Your report is currently being reviewed by an authorized administrator.",
            "APPROVED": "Your report has been verified and approved. An official bulletin has been opened.",
            "REJECTED": "Administrative review for this report has been completed.",
        }

        created_str = sub.created_at.strftime("%d %b %Y, %H:%M UTC") if sub.created_at else ""

        # Strictly Sanitized Public Status Object
        safe_response = {
            "submission_reference": sub.submission_reference,
            "status": sub.status,
            "submitted_at": created_str,
            "status_message": status_messages.get(sub.status, "Status update available."),
        }
        return True, safe_response
