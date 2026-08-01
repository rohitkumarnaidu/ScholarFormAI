# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Encryption service for securely storing user API keys.
Uses Fernet symmetric encryption with key rotation support.
"""

import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionService:
    """Handles encryption/decryption of sensitive data using Fernet."""

    def __init__(self, key: str | None = None):
        self._key = key or os.environ.get("ENCRYPTION_KEY")
        if not self._key:
            logger.critical(
                "ENCRYPTION_KEY is not set. The application will refuse to start because "
                "encrypted data would be unrecoverable after restart. "
                "Set the ENCRYPTION_KEY environment variable in production."
            )
            raise RuntimeError(
                "ENCRYPTION_KEY environment variable is required. "
                "Set ENCRYPTION_KEY to a valid Fernet key before starting the application."
            )
        if isinstance(self._key, str):
            self._key = self._key.encode()
        self._fernet = Fernet(self._key)

    @property
    def fernet(self) -> Fernet:
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return base64-encoded ciphertext."""
        if not plaintext:
            raise ValueError("Cannot encrypt empty value")
        encrypted = self._fernet.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext string."""
        if not ciphertext:
            raise ValueError("Cannot decrypt empty value")
        try:
            raw = base64.b64decode(ciphertext)
            return self._fernet.decrypt(raw).decode()
        except InvalidToken:
            logger.error("Failed to decrypt value — key mismatch or corrupted data")
            raise ValueError("Decryption failed: invalid key or corrupted data")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key for rotation."""
        return Fernet.generate_key().decode()


_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
