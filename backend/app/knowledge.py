"""Load the owner's profile, voice, and numbered FAQ."""

from __future__ import annotations

import json
import re
from pathlib import Path

STOPWORDS = {
    "a", "an", "the", "to", "of", "and", "or", "i", "you", "your", "me", "my",
    "is", "it", "for", "with", "can", "how", "what", "do", "does", "did", "be",
    "this", "that", "about", "on", "in", "if", "am", "are", "was", "who",
}


def load_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_faqs(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    faqs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        row["faq"] = int(row["faq"])
        faqs.append(row)
    faqs.sort(key=lambda row: row["faq"])
    return faqs


def tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9']+", text.lower())
        if word not in STOPWORDS and len(word) > 2
    }


def exact_faq(text: str, faqs: list[dict]) -> dict | None:
    """Return a saved FAQ when the message is exactly its chip text or question."""
    phrase = " ".join(text.split()).casefold()
    if not phrase:
        return None
    for faq in faqs:
        for field in ("query", "question"):
            saved = " ".join(str(faq.get(field) or "").split()).casefold()
            if saved and saved == phrase:
                return faq
    return None


def best_faq(text: str, faqs: list[dict]) -> dict | None:
    """Pick a saved FAQ when the visitor's wording clearly overlaps one."""
    have = tokens(text)
    if not have:
        return None
    best: dict | None = None
    score = 0
    for faq in faqs:
        overlap = len(have & tokens(f"{faq['query']} {faq['question']}"))
        if overlap > score:
            best, score = faq, overlap
    if best is not None and score >= 2:
        return best
    return None


def format_instant(faq: dict) -> str:
    return f"**Q{faq['faq']}:** {faq['question']}\n\n{faq['answer']}"


def build_instructions(
    owner_name: str,
    passages: list[dict],
    style: str,
    faqs: list[dict],
    guidance: str = "",
) -> str:
    listing = "\n".join(f"- Q{faq['faq']}: {faq['query']}" for faq in faqs) or "- (none yet)"
    if passages:
        retrieved = "\n\n".join(
            f"## {passage['title']}\n\n{passage['text']}" for passage in passages
        )
    else:
        retrieved = "(No matching passages were found.)"
    notes = guidance.strip() or "Do not invent facts about the owner."
    return f"""
You are the digital twin of {owner_name}, chatting with a visitor on {owner_name}'s website.

The conversation is three-way:
- Visitor: the person on the website.
- Avatar: you. You reply only as the twin.
- Human: {owner_name}, who may join from an admin panel. You do not answer on the human's behalf, and you do not respond to a human message until the visitor writes again. When the human has already answered, don't repeat them.

The user message you receive is a transcript with every role labeled. Reply only with your next message to the visitor. Do not prefix it with "Avatar:" and do not write lines for the visitor or the human.

Tools:
- faq_tool(question_number): use this whenever a visitor's question matches one of the numbered FAQ queries below. Answer from the tool result, keeping the substance of the saved answer. Do not invent a different answer.

When you do not know the answer, or the visitor wants to reach {owner_name}, say so plainly and ask for their email. Tell them {owner_name} will see the conversation in the admin inbox and can reply in this chat. Do not claim you sent a push notification, text, or email.

FAQ queries you can route to faq_tool:
{listing}

# Retrieved passages
These excerpts were retrieved for the visitor's latest question. They are not the full profile. Answer only from these passages, from faq_tool, and from the accuracy notes. If the fact is not there, say you don't know. Do not answer unrelated personal questions by inventing a preference, hobby, or opinion.

{retrieved}

# Accuracy notes
{notes}

# Voice, formatting, and safety
{style or "Be clear, warm, and brief. Never invent facts. Never use emojis."}
""".strip()
