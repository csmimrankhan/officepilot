"""Tests for the Fernet token crypto helper."""

from cryptography.fernet import Fernet

from app.services.email.crypto import (
    TokenCryptoError,
    decrypt_str,
    encrypt_str,
)


def test_round_trip_with_default_key():
    plain = "ya29.A0AfH6SMA_xyz"
    enc = encrypt_str(plain)
    assert enc != plain
    assert decrypt_str(enc) == plain


def test_encrypt_does_not_return_plaintext():
    plain = "refresh-token-1234567890"
    enc = encrypt_str(plain)
    assert plain not in enc
    assert Fernet  # library available


def test_decrypt_invalid_raises_clear_error():
    try:
        decrypt_str("not-a-valid-fernet-token")
    except TokenCryptoError as exc:
        assert "encryption key" in str(exc).lower() or "decrypt" in str(exc).lower()
    else:
        raise AssertionError("expected TokenCryptoError")


def test_decrypt_none_returns_none():
    assert decrypt_str(None) is None


def test_encrypt_none_returns_none():
    assert encrypt_str(None) is None  # type: ignore[arg-type]
