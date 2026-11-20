"""Avatar replies: OpenAI Agents SDK, with an offline FAQ fallback."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.config import Settings
from app.knowledge import best_faq, build_instructions, format_instant
from app.retrieve import retrieve_context


def transcript(rows: list[dict], owner_name: str) -> str:
    lines = [
        "Full conversation so far. Reply only as the Avatar, to the visitor's latest message.",
        "",
    ]
    for row in rows:
        role = row["role"]
        content = row["content"]
        if role == "visitor":
            who = row.get("conversation_name") or "Visitor"
            lines.append(f"Visitor ({who}): {content}")
        elif role == "human":
            lines.append(f"Human ({owner_name}): {content}")
        else:
            lines.append(f"Avatar: {content}")
        lines.append("")
    return "\n".join(lines).strip()


def _last_visitor_line(transcript_text: str) -> str:
    last = ""
    for line in transcript_text.splitlines():
        if line.startswith("Visitor ("):
            last = line.split(":", 1)[-1].strip()
    return last


async def offline_stream(transcript_text: str, settings: Settings, faqs: list[dict]) -> AsyncIterator[dict]:
    """Used when no OpenAI key is configured, so the twin still answers saved questions."""
    match = best_faq(_last_visitor_line(transcript_text), faqs)
    if match:
        text = format_instant(match)
        yield {"type": "tool", "name": "faq_tool", "state": "calling"}
        yield {"type": "tool", "name": "faq_tool", "state": "done", "detail": str(match["faq"])}
        yield {"type": "delta", "text": text}
        yield {
            "type": "result",
            "text": text,
            "tool_calls": [{"name": "faq_tool", "detail": str(match["faq"])}],
            "needs_attention": False,
        }
        return
    text = (
        f"I don't have that in what {settings.owner_name} has saved yet. "
        f"Leave your email and what you'd like to talk about, and "
        f"{settings.first_name} will see it in the admin inbox and can reply in this chat."
    )
    yield {"type": "delta", "text": text}
    yield {
        "type": "result",
        "text": text,
        "tool_calls": [],
        "needs_attention": True,
    }


def _text_delta(event) -> str | None:
    if getattr(event, "type", None) != "raw_response_event":
        return None
    data = getattr(event, "data", None)
    if data is None:
        return None
    if "TextDelta" not in type(data).__name__:
        return None
    delta = getattr(data, "delta", None)
    return delta if isinstance(delta, str) and delta else None


def _tool_name(item, fallback: str) -> str:
    if item is None:
        return fallback
    name = getattr(item, "tool_name", None)
    if isinstance(name, str) and name:
        return name
    raw = getattr(item, "raw_item", None)
    raw_name = getattr(raw, "name", None)
    if isinstance(raw_name, str) and raw_name:
        return raw_name
    return fallback


def build_runner(settings: Settings, faqs: list[dict], profile: str, style: str):
    async def stream(transcript_text: str) -> AsyncIterator[dict]:
        if not settings.openai_api_key:
            async for event in offline_stream(transcript_text, settings, faqs):
                yield event
            return
        question = _last_visitor_line(transcript_text)
        passages, guidance = await retrieve_context(settings, profile, faqs, question)
        instructions = build_instructions(settings.owner_name, passages, style, faqs, guidance)
        async for event in _run_live(transcript_text, settings, faqs, instructions):
            yield event

    return stream


async def _run_live(
    transcript_text: str,
    settings: Settings,
    faqs: list[dict],
    instructions: str,
) -> AsyncIterator[dict]:
    from agents import Agent, Runner, function_tool, set_default_openai_key

    set_default_openai_key(settings.openai_api_key, use_for_tracing=False)
    state: dict = {"attention": False, "tools": [], "last_tool": "tool"}
    by_number = {int(faq["faq"]): faq for faq in faqs}

    @function_tool
    def faq_tool(question_number: int) -> str:
        """Retrieve the full original question and answer for a numbered FAQ."""
        faq = by_number.get(int(question_number))
        if not faq:
            return "That question number was not found in the FAQ."
        return f"Question {faq['faq']}: {faq['question']}\n\nAnswer:\n{faq['answer']}"

    agent = Agent(
        name="Avatar",
        instructions=instructions,
        model=settings.model,
        tools=[faq_tool],
    )
    result = Runner.run_streamed(agent, transcript_text)
    parts: list[str] = []
    async for event in result.stream_events():
        delta = _text_delta(event)
        if delta:
            parts.append(delta)
            yield {"type": "delta", "text": delta}
            continue
        if getattr(event, "type", None) != "run_item_stream_event":
            continue
        name = getattr(event, "name", "")
        item = getattr(event, "item", None)
        if name == "tool_called":
            tool = _tool_name(item, state["last_tool"])
            state["last_tool"] = tool
            yield {"type": "tool", "name": tool, "state": "calling"}
        elif name == "tool_output":
            tool = _tool_name(item, state["last_tool"])
            state["tools"].append({"name": tool, "detail": "done"})
            yield {"type": "tool", "name": tool, "state": "done", "detail": "done"}

    text = "".join(parts).strip()
    if not text:
        final = getattr(result, "final_output", None)
        if isinstance(final, str):
            text = final.strip()
    if not text:
        text = (
            f"I'm not sure about that. I've flagged it so {settings.first_name} can take a look."
        )
        state["attention"] = True
    yield {
        "type": "result",
        "text": text,
        "tool_calls": state["tools"],
        "needs_attention": state["attention"],
    }
