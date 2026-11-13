import hashlib
import hmac
import secrets
import time
from fastapi import Request

from app.config.config import settings
from app.exceptions.auth import CSRFValidationException


def generate_csrf_token(secret_key: str | None = None) -> str:
    """
    Generates a cryptographically secure, stateless HMAC-signed CSRF token.
    Format: <random_hex>.<timestamp>.<hmac_signature>
    """
    key = (secret_key or settings.JWT_SECRET_KEY).encode("utf-8")
    rand_hex = secrets.token_hex(16)
    timestamp = int(time.time())
    message = f"{rand_hex}:{timestamp}".encode("utf-8")
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"{rand_hex}.{timestamp}.{signature}"


def validate_csrf_token(
    token: str | None,
    secret_key: str | None = None,
    max_age_seconds: int = 86400,
) -> bool:
    """
    Validates the structure, timestamp freshness, and HMAC signature of a CSRF token.
    """
    if not token or not isinstance(token, str):
        return False

    parts = token.split(".")
    if len(parts) != 3:
        return False

    rand_hex, timestamp_str, signature = parts
    try:
        token_time = int(timestamp_str)
    except ValueError:
        return False

    current_time = int(time.time())
    # Reject if expired or timestamp is in the future beyond 5 minutes drift
    if current_time - token_time > max_age_seconds or token_time > current_time + 300:
        return False

    key = (secret_key or settings.JWT_SECRET_KEY).encode("utf-8")
    message = f"{rand_hex}:{token_time}".encode("utf-8")
    expected_signature = hmac.new(key, message, hashlib.sha256).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


async def verify_csrf_token(request: Request) -> None:
    """
    FastAPI dependency for state-changing endpoints (POST, PUT, PATCH, DELETE).
    Validates that the X-CSRF-Token header contains a valid, unexpired CSRF token.
    """
    if request.method.upper() in ["GET", "HEAD", "OPTIONS"]:
        return

    token = (
        request.headers.get("X-CSRF-Token")
        or request.headers.get("x-csrf-token")
        or request.headers.get("X-XSRF-TOKEN")
        or request.headers.get("x-xsrf-token")
    )
    if not token:
        raise CSRFValidationException(message="Missing CSRF token in X-CSRF-Token header")

    if not validate_csrf_token(token):
        raise CSRFValidationException(message="Invalid or expired CSRF token")
