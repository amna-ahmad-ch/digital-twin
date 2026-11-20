"""Admin session cookie. Visitors stay anonymous and are addressed only by conversation id."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import Settings

COOKIE = "avatar_admin"
MAX_AGE = 14 * 24 * 3600


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="avatar-admin")


def issue_token(settings: Settings) -> str:
    return _serializer(settings).dumps({"role": "admin"})


def token_is_valid(settings: Settings, token: str | None) -> bool:
    if not token or not settings.admin_password:
        return False
    try:
        data = _serializer(settings).loads(token, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(data, dict) and data.get("role") == "admin"
