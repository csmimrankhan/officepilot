"""Symmetric encryption for OAuth tokens.

Uses Fernet (AES-128-CBC + HMAC-SHA256). The key is loaded from
``OFFICEPILOT_GMAIL_TOKEN_KEY``; for development convenience a random key
is generated and persisted under ``OFFICEPILOT_GMAIL_STATE_DIR`` on first
use. Operators are expected to set their own key in production.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from ...config import get_settings

logger = logging.getLogger(__name__)

_KEY_FILE = "token.key"


class TokenCryptoError(Exception):
    pass


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    s = get_settings()
    s.gmail_state_dir.mkdir(parents=True, exist_ok=True)
    key_path: Path = s.gmail_state_dir / _KEY_FILE
    key = s.gmail_token_key.encode("utf-8") if s.gmail_token_key else None
    if not key:
        if key_path.exists():
            key = key_path.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            try:
                # Restrict permissions where possible (best effort on Windows).
                key_path.chmod(0o600)
            except Exception:  # pragma: no cover
                pass
            logger.warning(
                "Generated a new Fernet key at %s. "
                "Set OFFICEPILOT_GMAIL_TOKEN_KEY in production to persist it.",
                key_path,
            )
    try:
        return Fernet(key)
    except Exception as exc:  # pragma: no cover
        raise TokenCryptoError(f"Invalid token encryption key: {exc}") from exc


def encrypt_str(plaintext: str) -> str:
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_str(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenCryptoError(
            "Stored token could not be decrypted. The encryption key has likely "
            "changed; please reconnect Gmail."
        ) from exc
