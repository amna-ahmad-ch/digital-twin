"""Hybrid retrieval over the profile, in the style of the FoodSafety live demo.

Passages are split from knowledge.md and the FAQ. A question is ranked with
BM25 and OpenAI text-embedding-3-small, fused with reciprocal rank fusion,
and the top few passages are returned. The full profile is not sent.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import Settings

log = logging.getLogger("avatar")

EMBED_MODEL = "text-embedding-3-small"
TOP_K = 5
FUSION_CANDIDATES = 20
RRF_K = 60
CHUNK_LIMIT = 1400
PINNED = {"About Me", "Guidance for the Digital Twin"}

_index_key = ""
_index: "Index | None" = None


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def passage_text(chunk: dict) -> str:
    return f"{chunk['title']}\n\n{chunk['text']}".strip()


def _split_long(title: str, text: str) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_LIMIT:
        return [{"title": title, "text": text}]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    groups: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if buffer and len(buffer) + len(paragraph) + 2 > CHUNK_LIMIT:
            groups.append(buffer)
            buffer = paragraph
        else:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
    if buffer:
        groups.append(buffer)
    if len(groups) == 1:
        return [{"title": title, "text": groups[0]}]
    return [
        {"title": f"{title} ({index}/{len(groups)})", "text": group}
        for index, group in enumerate(groups, start=1)
    ]


def chunk_profile(profile: str) -> tuple[list[dict], list[dict], str]:
    """Split the profile into searchable passages and always-included notes."""
    searchable: list[dict] = []
    pinned: list[dict] = []
    guidance: list[str] = []
    current_title = ""
    current_pin = False
    current_lines: list[str] = []
    h2 = ""

    def flush() -> None:
        text = "\n".join(current_lines).strip()
        if not text or not current_title:
            return
        if current_title == "Guidance for the Digital Twin":
            guidance.append(text)
            return
        pieces = _split_long(current_title, text)
        if current_pin:
            pinned.extend(pieces)
        else:
            searchable.extend(pieces)

    for line in profile.splitlines():
        if line.startswith("### "):
            flush()
            heading = line[4:].strip()
            current_title = f"{h2} — {heading}" if h2 else heading
            current_pin = heading in PINNED
            current_lines = []
        elif line.startswith("## "):
            flush()
            h2 = line[3:].strip()
            current_title = h2
            current_pin = h2 in PINNED
            current_lines = []
        elif line.startswith("# "):
            flush()
            current_title = ""
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return searchable, pinned, "\n\n".join(guidance).strip()


def chunk_faqs(faqs: list[dict]) -> list[dict]:
    chunks = []
    for faq in faqs:
        question = str(faq.get("question") or "").strip()
        answer = str(faq.get("answer") or "").strip()
        if not question or not answer:
            continue
        chunks.append({"title": f"FAQ: {question}", "text": answer})
    return chunks


def fuse(rankings: tuple[list[dict], ...], k: int) -> list[dict]:
    """Reciprocal rank fusion. Rank 1 scores 1/61, rank 2 scores 1/62."""
    scores: dict[str, float] = {}
    chosen: dict[str, dict] = {}
    for hits in rankings:
        for rank, chunk in enumerate(hits, start=1):
            key = passage_text(chunk)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
            chosen.setdefault(key, chunk)
    ordered = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [chosen[key] for key in ordered[:k]]


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class Index:
    def __init__(self, chunks: list[dict], vectors: list[list[float]] | None = None) -> None:
        self.chunks = chunks
        self.vectors = vectors or []
        documents = [tokenize(passage_text(chunk)) or ["empty"] for chunk in chunks]
        self.bm25 = BM25Okapi(documents) if documents else None

    def search_with_vector(self, question: str, query_vector: list[float] | None, k: int = TOP_K) -> list[dict]:
        if not self.chunks:
            return []
        pool = min(FUSION_CANDIDATES, len(self.chunks))
        keyword_scores = self.bm25.get_scores(tokenize(question)) if self.bm25 else []
        keyword_order = sorted(range(len(self.chunks)), key=lambda i: float(keyword_scores[i]), reverse=True)
        keyword_hits = [self.chunks[i] for i in keyword_order[:pool]]
        if not query_vector or len(self.vectors) != len(self.chunks):
            return keyword_hits[:k]
        vector_order = sorted(
            range(len(self.chunks)),
            key=lambda i: cosine(query_vector, self.vectors[i]),
            reverse=True,
        )
        vector_hits = [self.chunks[i] for i in vector_order[:pool]]
        return fuse((keyword_hits, vector_hits), k)


def _cache_path(settings: Settings) -> Path:
    """Committed with the project so a Render spin-down does not rebuild it."""
    return settings.knowledge_dir / "retrieval-vectors.json"


def _chunk_key(chunk: dict) -> str:
    return hashlib.sha256(passage_text(chunk).encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> dict[str, list[float]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if payload.get("model") != EMBED_MODEL:
        return {}
    items = payload.get("items")
    return items if isinstance(items, dict) else {}


def _save_cache(path: Path, items: dict[str, list[float]]) -> None:
    path.write_text(
        json.dumps({"model": EMBED_MODEL, "items": items}, separators=(",", ":")),
        encoding="utf-8",
    )


async def _embed(api_key: str, texts: list[str]) -> list[list[float]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    vectors: list[list[float] | None] = [None] * len(texts)
    for start in range(0, len(texts), 16):
        batch = texts[start : start + 16]
        response = await client.embeddings.create(model=EMBED_MODEL, input=batch)
        for item in response.data:
            vectors[start + item.index] = [round(float(value), 6) for value in item.embedding]
    if any(vector is None for vector in vectors):
        raise RuntimeError("Embedding response did not cover every passage")
    return vectors  # type: ignore[return-value]


async def retrieve_context(
    settings: Settings,
    profile: str,
    faqs: list[dict],
    question: str,
) -> tuple[list[dict], str]:
    """Return pinned notes plus the passages retrieved for this question."""
    global _index, _index_key
    searchable, pinned, guidance = chunk_profile(profile)
    chunks = searchable + chunk_faqs(faqs)
    key = hashlib.sha256("\n".join(passage_text(chunk) for chunk in chunks).encode("utf-8")).hexdigest()
    if _index is None or _index_key != key:
        _index = await _build_index(settings, chunks)
        _index_key = key
    query_vector = None
    try:
        embedded = await _embed(settings.openai_api_key, [question])
        query_vector = embedded[0]
    except Exception:
        log.exception("Question embedding failed; using keyword search only")
    found = _index.search_with_vector(question, query_vector) if _index else []
    return [*pinned, *found], guidance


async def _build_index(settings: Settings, chunks: list[dict]) -> Index:
    path = _cache_path(settings)
    cached = _load_cache(path)
    missing = [chunk for chunk in chunks if _chunk_key(chunk) not in cached]
    if missing and settings.openai_api_key:
        try:
            vectors = await _embed(settings.openai_api_key, [passage_text(chunk) for chunk in missing])
            for chunk, vector in zip(missing, vectors):
                cached[_chunk_key(chunk)] = vector
            _save_cache(path, cached)
            log.info("Embedded %s new profile passages", len(missing))
        except Exception:
            log.exception("Passage embedding failed; keyword search will be used")
    vectors = [cached.get(_chunk_key(chunk), []) for chunk in chunks]
    if any(not vector for vector in vectors):
        return Index(chunks, vectors=None)
    return Index(chunks, vectors=vectors)
