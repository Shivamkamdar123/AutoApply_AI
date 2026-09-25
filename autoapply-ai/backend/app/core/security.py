"""
Secrets Management
==================
Stores sensitive job board credentials encrypted at rest.
Never logs passwords or API keys. Uses AES-128-CBC + HMAC-SHA256 (Fernet).

Upgrade Path:
For enterprise or production deployments, swap `LocalEncryptedSecretsManager`
with HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager
by implementing the `SecretsManager` interface.
"""

import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from app.core.exceptions import SecurityError, MissingSecretKeyError


class SecretsManager:
    """Interface for secrets management."""

    def encrypt_secret(self, plaintext: str) -> str:
        raise NotImplementedError

    def decrypt_secret(self, ciphertext: str) -> str:
        raise NotImplementedError


class LocalEncryptedSecretsManager(SecretsManager):
    """
    Encrypts secrets locally using a key derived from SECRET_KEY using SHA-256.
    Ensures safe encryption without plaintext exposure in databases or logs.
    """

    def __init__(self, master_key: str):
        if not master_key or master_key.strip() == "":
            raise MissingSecretKeyError("SECRET_KEY must be provided for encrypted storage.")
        
        # Derive a 32-byte urlsafe base64 Fernet key from the master secret
        digest = hashlib.sha256(master_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt_secret(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt_secret(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise SecurityError("Failed to decrypt secret: invalid token or wrong SECRET_KEY") from exc


# -------------------------------------------------------------
# Password Hashing & Verification (bcrypt)
# -------------------------------------------------------------
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.core.exceptions import InvalidTokenError


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# -------------------------------------------------------------
# JWT Access & Refresh Token Management
# -------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed, short-lived JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed, longer-lived JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid token signature or format") from exc


# -------------------------------------------------------------
# In-Memory Rate Limiter (sliding window per key/IP)
# -------------------------------------------------------------
class InMemoryRateLimiter:
    """
    Sliding window rate limiter for brute-force prevention on authentication routes.
    Tracks timestamps per key (e.g. client IP or email).
    """

    def __init__(self, max_requests: int = 5, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        timestamps = self._history.get(key, [])
        # Filter out expired timestamps
        cutoff = now - self.window_seconds
        valid_timestamps = [ts for ts in timestamps if ts > cutoff]
        if len(valid_timestamps) >= self.max_requests:
            self._history[key] = valid_timestamps
            return False
        valid_timestamps.append(now)
        self._history[key] = valid_timestamps
        return True

    def reset(self, key: str) -> None:
        self._history.pop(key, None)


# Singleton rate limiters for auth
auth_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60.0)
upload_rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60.0)
