"""Field-level encryption (Fernet/AES-128-CBC+HMAC) and deterministic tokenisation. Keys come ONLY from the environment."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class KeyMissingError(RuntimeError):
    pass


def master_secret(env: dict[str, str] | None = None) -> bytes:
    env = env if env is not None else dict(os.environ)
    s = env.get("EMBLEM_MASTER_SECRET")
    if not s:
        if env.get("EMBLEM_ENV", "dev") == "prod":
            raise KeyMissingError(
                "EMBLEM_MASTER_SECRET is required in prod (load from Key Vault / secret manager)"
            )
        s = "dev-only-ephemeral-" + hashlib.sha256(os.urandom(16)).hexdigest()  # per-process, never stored
    return s.encode()


def _derive(secret: bytes, purpose: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=purpose).derive(secret)


class FieldCipher:
    def __init__(self, secret: bytes) -> None:
        self._fernet = Fernet(base64.urlsafe_b64encode(_derive(secret, b"field-encryption")))
        self._tok = _derive(secret, b"tokenisation")

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("cannot decrypt: wrong key or tampered ciphertext") from exc

    def token(self, value: str) -> str:
        """Deterministic pseudonym: joinable across datasets without revealing the value."""
        return "tk_" + hmac.new(self._tok, value.lower().encode(), hashlib.sha256).hexdigest()[:16]
