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
