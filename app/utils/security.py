from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet


def _build_fernet_key() -> bytes:
    raw = os.getenv("SERVICENOW_ENCRYPTION_KEY", "").strip()
    if not raw:
        raise RuntimeError("SERVICENOW_ENCRYPTION_KEY is not set")

    try:
        decoded = base64.urlsafe_b64decode(raw.encode("utf-8"))
        if len(decoded) == 32:
            return raw.encode("utf-8")
    except Exception:
        pass

    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    return Fernet(_build_fernet_key())


def encrypt_text(value: str) -> str:
    token = get_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(value: str) -> str:
    plain = get_fernet().decrypt(value.encode("utf-8"))
    return plain.decode("utf-8")

