"""User authentication and session management."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field


SECRET_KEY = os.environ.get("SECRET_KEY", "")
TOKEN_TTL_SECONDS = 3600


@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool = True
    roles: list[str] = field(default_factory=list)


@dataclass
class Session:
    token: str
    user_id: int
    expires_at: float
    scopes: list[str] = field(default_factory=list)


_session_store: dict[str, Session] = {}


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its stored hash."""
    try:
        salt_hex, dk_hex = password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


def generate_token(user: User, scopes: list[str] | None = None) -> str:
    """Generate a signed session token for the given user."""
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is not set.")
    payload = f"{user.id}:{time.time()}:{','.join(scopes or [])}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def authenticate_user(username: str, password: str, user_db: dict[str, User]) -> Session | None:
    """
    Authenticate a user by username and password.
    Returns a Session on success, None on failure.
    """
    user = user_db.get(username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    token = generate_token(user)
    session = Session(
        token=token,
        user_id=user.id,
        expires_at=time.time() + TOKEN_TTL_SECONDS,
    )
    _session_store[token] = session
    return session


def validate_token(token: str) -> Session | None:
    """
    Validate a session token.
    Returns the Session if valid and not expired, None otherwise.
    """
    session = _session_store.get(token)
    if not session:
        return None
    if time.time() > session.expires_at:
        del _session_store[token]
        return None
    return session


def revoke_token(token: str) -> None:
    """Invalidate a session token."""
    _session_store.pop(token, None)


def require_role(session: Session, role: str, user_db: dict[int, User]) -> bool:
    """Check whether the session's user has the required role."""
    user = user_db.get(session.user_id)
    if not user:
        return False
    return role in user.roles
