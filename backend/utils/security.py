"""
Security utilities for password hashing and verification.
Uses bcrypt exclusively for new hashes. Retains read-support for legacy SHA-256 hashes.
"""
import hashlib
import bcrypt


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt with an auto-generated salt.
    Returns the bcrypt hash string (starts with '$2b$').
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a password against its stored hash.
    Supports bcrypt (primary) and legacy SHA-256 salted hashes (read-only compat).
    """
    if not hashed_password:
        return False

    # Legacy SHA-256 salted format: sha256$<salt>$<hash>
    if hashed_password.startswith("sha256$"):
        try:
            _, salt, stored_hash = hashed_password.split('$')
            recreated = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
            return recreated == stored_hash
        except ValueError:
            return False

    # Primary: bcrypt
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False
