"""
Validators for the Missing Person Registration workflow.

Exposes field-level validators and a single aggregate validator
(validate_registration_payload) used by the service layer and UI layer.
"""
import re
import os
from typing import Tuple, Optional, List, Dict, Any

# ------------------------------------------------------------------
# Allowed configurations (could be moved to config/settings later)
# ------------------------------------------------------------------
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
# 5 MB default max image size
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MIN_AGE = 0
MAX_AGE = 120

GENDER_OPTIONS = {"Male", "Female", "Other"}
STATUS_ACTIVE = "ACTIVE"


# ------------------------------------------------------------------
# Field-level validators
# ------------------------------------------------------------------

def validate_required(value, field_name: str, min_length: int = 2) -> Tuple[bool, str]:
    if value is None:
        return False, f"{field_name} is required."
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False, f"{field_name} is required."
        if len(stripped) < min_length:
            return False, f"{field_name} must be at least {min_length} characters long."
    return True, "OK"


def validate_age(age: int) -> Tuple[bool, str]:
    if age is None:
        return False, "Age is required."
    if not isinstance(age, int) or isinstance(age, bool):
        return False, "Age must be a whole number."
    if age < MIN_AGE or age > MAX_AGE:
        return False, f"Age must be between {MIN_AGE} and {MAX_AGE}."
    return True, "OK"


def validate_email(email: str) -> Tuple[bool, str]:
    if not email:
        return False, "Email is required."
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email.strip()):
        return False, "Please provide a valid email address (e.g., name@example.com)."
    return True, "OK"


def validate_phone(phone: str) -> Tuple[bool, str]:
    if not phone:
        return False, "Phone number is required."
    phone_regex = r'^\+?[0-9\s\-()]{8,20}$'
    if not re.match(phone_regex, phone.strip()):
        return False, "Please provide a valid phone number (10-15 digits)."
    return True, "OK"


def validate_gender(gender: str) -> Tuple[bool, str]:
    if not gender:
        return False, "Gender is required."
    if gender not in GENDER_OPTIONS:
        return False, f"Gender must be one of: {', '.join(sorted(GENDER_OPTIONS))}."
    return True, "OK"


def validate_image_filename(filename: Optional[str]) -> Tuple[bool, str]:
    """Checks image extension and path safety against the allow-list."""
    if not filename:
        return False, "A photograph upload is required."

    raw_str = str(filename)
    if ".." in raw_str or "/" in raw_str or "\\" in raw_str:
        return False, "Path traversal sequence detected in filename."

    clean_name = os.path.basename(raw_str)
    _, ext = os.path.splitext(clean_name.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return (False,
                f"Invalid image format: '{ext or 'none'}'. "
                f"Allowed formats: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}.")
    return True, "OK"


def validate_image_bytes(num_bytes: int) -> Tuple[bool, str]:
    """Validates the byte length of an uploaded photograph."""
    if num_bytes <= 0:
        return False, "The uploaded image file is empty."
    if num_bytes > MAX_IMAGE_BYTES:
        return (False,
                f"Image is too large ({num_bytes / 1024 / 1024:.2f} MB). "
                f"Maximum allowed is {MAX_IMAGE_BYTES / 1024 / 1024:.0f} MB.")
    return True, "OK"


def validate_image_upload(uploaded_file) -> Tuple[bool, str]:
    """
    Comprehensive image validation for a file-like object exposing
    `.name` (filename) and `.size` (byte count).
    """
    if not uploaded_file:
        return False, "A photograph upload is required."

    ok, msg = validate_image_filename(getattr(uploaded_file, "name", ""))
    if not ok:
        return False, msg

    # Check MIME type if available
    mime = getattr(uploaded_file, "type", None)
    if mime and mime not in ALLOWED_IMAGE_MIMES:
        return (False,
                f"Unsupported image type '{mime}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_MIMES))}.")

    size_bytes = getattr(uploaded_file, "size", None)
    if size_bytes is None:
        # Fallback: allow — we can't inspect bytes without reading
        return True, "OK"
    return validate_image_bytes(size_bytes)


# ------------------------------------------------------------------
# Aggregate registration payload validator
# ------------------------------------------------------------------

def validate_registration_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates all registration fields at once and returns a list of
    human-readable error messages (empty list = valid).

    Expected keys (all required):
        name, age, gender, description, last_seen_date, last_seen_location,
        state, city, contact_name, contact_email, contact_phone,
        has_upload (bool) or photo_file (file-like)
    """
    errors: List[str] = []

    ok, msg = validate_required(payload.get("name"), "Full Name", min_length=2)
    if not ok:
        errors.append(msg)

    age_ok, age_msg = validate_age(payload.get("age"))
    if not age_ok:
        errors.append(age_msg)

    gender_ok, gender_msg = validate_gender(payload.get("gender"))
    if not gender_ok:
        errors.append(gender_msg)

    desc_ok, desc_msg = validate_required(payload.get("description"), "Description", min_length=10)
    if not desc_ok:
        errors.append(desc_msg)

    if not payload.get("last_seen_date"):
        errors.append("Last Seen Date is required.")

    loc_ok, loc_msg = validate_required(payload.get("last_seen_location"), "Last Seen Location", min_length=3)
    if not loc_ok:
        errors.append(loc_msg)

    state_ok, state_msg = validate_required(payload.get("state"), "State", min_length=2)
    if not state_ok:
        errors.append(state_msg)

    city_ok, city_msg = validate_required(payload.get("city"), "City", min_length=2)
    if not city_ok:
        errors.append(city_msg)

    cname_ok, cname_msg = validate_required(payload.get("contact_name"), "Contact Person Name", min_length=2)
    if not cname_ok:
        errors.append(cname_msg)

    email_ok, email_msg = validate_email(payload.get("contact_email"))
    if not email_ok:
        errors.append(email_msg)

    phone_ok, phone_msg = validate_phone(payload.get("contact_phone"))
    if not phone_ok:
        errors.append(phone_msg)

    # Photograph presence / content
    photo_file = payload.get("photo_file")
    if payload.get("photo_skip_validation"):
        # Test-hook: skip image validation in unit tests that pass bytes separately
        pass
    elif photo_file is None:
        # Legacy 'has_upload' key
        if not payload.get("has_upload"):
            errors.append("A photograph is required to register a missing person bulletin.")
    else:
        img_ok, img_msg = validate_image_upload(photo_file)
        if not img_ok:
            errors.append(img_msg)

    return (len(errors) == 0), errors


# ------------------------------------------------------------------
# Legacy helper used by existing pages
# ------------------------------------------------------------------
def validate_case_inputs(name: str, age: int, reporter_contact: str) -> Tuple[bool, str]:
    """Backwards-compatible legacy wrapper — do not extend; use the new validator above."""
    if not name or len(name.strip()) < 2:
        return False, "Name must be at least 2 characters long."
    ok, msg = validate_age(age)
    if not ok:
        return False, msg
    if reporter_contact:
        ok_p, msg_p = validate_phone(reporter_contact)
        if not ok_p:
            return False, msg_p
    return True, "Success"
