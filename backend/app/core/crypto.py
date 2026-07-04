"""Symmetric encryption for secrets stored at rest (Integration API keys).

The Fernet key is derived from SECRET_KEY so no extra configuration is needed;
rotating SECRET_KEY invalidates stored integration secrets (documented in README).
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_value(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str | None:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def mask_secret(plaintext: str) -> str:
    """Return a display-safe masked version, e.g. 'sk-a****xyz1'."""
    if len(plaintext) <= 6:
        return "*" * len(plaintext)
    return f"{plaintext[:4]}****{plaintext[-4:]}"
