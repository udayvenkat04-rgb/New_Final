"""
Idempotent development user seeder.

Creates one Admin and one Officer user if they don't already exist.
Credentials are read from environment variables (never hardcoded).
Passwords are never printed in logs.

Usage:
    python -m database.seed_users
"""
import os
import logging
from backend.database.connection import check_database_connection
from backend.repositories.user_repository import UserRepository
from backend.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Default development credentials — only used when env vars are absent.
# These are intentionally NOT production-safe and are documented in .env.example.
_DEV_DEFAULTS = {
    "admin": {
        "name": "Admin",
        "email": "admin@missingtracker.com",
        "password": "admin123",
        "role": "admin",
    },
    "officer": {
        "name": "Officer",
        "email": "officer@missingtracker.com",
        "password": "officer123",
        "role": "officer",
    },
}


def _get_dev_user_config(key: str) -> dict:
    """Reads dev user config from env vars with fallback to _DEV_DEFAULTS."""
    defaults = _DEV_DEFAULTS[key]
    prefix = f"DEV_{key.upper()}_"
    return {
        "name": os.getenv(f"{prefix}NAME", defaults["name"]),
        "email": os.getenv(f"{prefix}EMAIL", defaults["email"]),
        "password": os.getenv(f"{prefix}PASSWORD", defaults["password"]),
        "role": defaults["role"],
    }


def seed_dev_users() -> bool:
    """
    Seeds development Admin and Officer users into MongoDB.

    - Checks whether each user already exists (by email) before creating.
    - Never creates duplicate users.
    - Never prints passwords in logs.

    Returns True if seeding completed (even if users were skipped).
    Returns False if the database is unreachable.
    """
    connected, msg = check_database_connection()
    if not connected:
        logger.error("Cannot seed users — database unreachable: %s", msg)
        print(f"ERROR: Cannot seed users. {msg}")
        return False

    auth_service = AuthService()
    user_repo = UserRepository()

    for key in ("admin", "officer"):
        config = _get_dev_user_config(key)
        email = config["email"]

        existing = user_repo.get_by_email(email)
        if existing is not None:
            print(f"[SEED] {config['role'].upper()} user already exists (email: {email}). Skipping.")
            logger.info("Seed: %s user already exists (email: %s). Skipped.", config["role"], email)
            continue

        try:
            auth_service.create_user(
                name=config["name"],
                email=config["email"],
                password=config["password"],
                role=config["role"],
            )
            print(f"[SEED] Created {config['role'].upper()} user (email: {email}).")
            logger.info("Seed: Created %s user (email: %s).", config["role"], email)
        except ValueError as exc:
            # Shouldn't happen since we checked existence, but handle gracefully
            print(f"[SEED] Skipped {config['role'].upper()}: {exc}")
            logger.warning("Seed: Skipped %s user: %s", config["role"], exc)

    print("[SEED] User seeding complete.")
    return True


if __name__ == "__main__":
    seed_dev_users()
