"""
AuthService manages user authentication and registration.
All database access goes through UserRepository — no direct collection queries.
"""
import logging
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from backend.models.user import User
from backend.repositories.user_repository import UserRepository
from backend.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """Handles authentication, user creation, and credential verification."""

    def __init__(self, user_repo: UserRepository = None):
        self.user_repo = user_repo or UserRepository()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, email: str, password: str) -> User:
        """
        Authenticates a user by email and password.

        Returns:
            User object on success.

        Raises:
            ValueError: If the account exists but is inactive.
            ConnectionError: If MongoDB is unreachable.

        Returns None for invalid email or wrong password.
        """
        clean_email = email.strip() if email else ""
        clean_pass = password.strip() if password else ""
        try:
            user = self.user_repo.get_by_email(clean_email) or self.user_repo.get_by_username(clean_email)
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            logger.error("MongoDB connection failure during authentication: %s", exc)
            raise ConnectionError(
                "Unable to connect to the database. Please try again later."
            ) from exc

        if user is None:
            return None

        if not verify_password(clean_pass, user.password_hash):
            return None

        if not user.is_active:
            raise ValueError("Account is inactive. Please contact an administrator.")

        return user

    # ------------------------------------------------------------------
    # User Creation
    # ------------------------------------------------------------------

    def create_user(self, name: str, email: str, password: str, role: str) -> User:
        """
        Creates a new user with a hashed password.

        Raises:
            ValueError: If the email is already registered.
            ConnectionError: If MongoDB is unreachable.
        """
        try:
            existing = self.user_repo.get_by_email(email)
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            logger.error("MongoDB connection failure during user creation: %s", exc)
            raise ConnectionError(
                "Unable to connect to the database. Please try again later."
            ) from exc

        if existing is not None:
            raise ValueError(f"A user with email '{email}' already exists.")

        hashed_pw = hash_password(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=hashed_pw,
            role=role,
        )
        return self.user_repo.create(new_user)

    # Backward-compatible alias
    register_user = create_user
