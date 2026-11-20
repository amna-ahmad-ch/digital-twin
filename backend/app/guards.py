"""Cheap protections for the model key. No configuration."""

from __future__ import annotations

import re
from uuid import UUID

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

MESSAGE_LIMIT = 2_000
TRUNCATION_NOTE = (
    "[...message truncated as it's too long; ask the visitor to send something more concise]"
)
INSTANT_RE = re.compile(r"^q\d{1,2}$", re.IGNORECASE)
RATE = parse("20/minute")
DAILY_MODEL_CALLS = 30
DAILY_RATE = parse(f"{DAILY_MODEL_CALLS}/day")


class ChatLimiter:
    def __init__(self) -> None:
        self._limiter = MovingWindowRateLimiter(MemoryStorage())

    def allow(self, conversation_id: str) -> bool:
        return bool(self._limiter.hit(RATE, "avatar-chat", conversation_id))

    def allow_model_call(self, visitor_ip: str) -> bool:
        return bool(self._limiter.hit(DAILY_RATE, "avatar-daily", visitor_ip))


def clamp_message(text: str) -> str:
    cleaned = text.replace("\x00", "")
    if len(cleaned) <= MESSAGE_LIMIT:
        return cleaned
    return f"{cleaned[:MESSAGE_LIMIT]}\n{TRUNCATION_NOTE}"


def clamp_name(name: str | None) -> str | None:
    if name is None:
        return None
    cleaned = " ".join(name.replace("\x00", "").split())
    if not cleaned:
        return None
    return cleaned[:80]


def visitor_ip(forwarded_for: str | None, client_host: str | None) -> str:
    """The address the nearest proxy saw. A visitor-supplied prefix is ignored."""
    parts = [part.strip() for part in (forwarded_for or "").split(",") if part.strip()]
    if parts:
        return parts[-1][:80]
    if client_host:
        return client_host[:80]
    return "unknown"


def parse_conversation_id(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("conversation_id must be a UUID") from exc


def instant_number(text: str) -> int | None:
    stripped = text.strip()
    if not INSTANT_RE.match(stripped):
        return None
    return int(stripped[1:])


_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
_CONTACT = (
    "get in touch",
    "contact me",
    "contact you",
    "reach you",
    "talk to you",
    "speak to you",
    "call you",
    "meet you",
)


def visitor_needs_owner(text: str) -> bool:
    """True when a visitor is trying to reach the owner, so the admin inbox can flag the thread."""
    if _EMAIL.search(text):
        return True
    lowered = text.lower()
    return any(phrase in lowered for phrase in _CONTACT)
