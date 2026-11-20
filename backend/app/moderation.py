"""Free OpenAI moderation check. A flagged message never reaches the chat model."""

from __future__ import annotations

import logging

log = logging.getLogger("avatar")

MODERATION_MODEL = "omni-moderation-latest"
REFUSAL = "I can't help with that."


async def message_is_flagged(api_key: str, text: str) -> bool:
    """True when OpenAI moderation flags the text. Errors allow the message through."""
    if not api_key or not text.strip():
        return False
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.moderations.create(model=MODERATION_MODEL, input=text)
        return bool(response.results[0].flagged)
    except Exception:
        log.exception("Moderation check failed")
        return False
