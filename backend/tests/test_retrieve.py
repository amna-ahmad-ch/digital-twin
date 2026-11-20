"""Retrieval stays on a few passages instead of the whole profile."""

from app.config import project_root
from app.knowledge import build_instructions, load_faqs, load_text
from app.retrieve import Index, chunk_profile, fuse


def test_profile_is_split_and_guidance_is_kept_separate():
    profile = load_text(project_root() / "knowledge" / "knowledge.md")
    searchable, pinned, guidance = chunk_profile(profile)
    assert len(searchable) > 5
    assert any(chunk["title"] == "About Me" for chunk in pinned)
    assert "Do not claim that the experimental Groq reranking" in guidance
    assert all("Groq reranking system is part of the deployed" not in chunk["text"] for chunk in searchable)
    joined = "\n".join(chunk["text"] for chunk in searchable)
    assert "ClickUp" in joined
    assert len(joined) < len(profile)


def test_hybrid_search_ranks_the_matching_passage_first():
    chunks = [
        {"title": "Education", "text": "Amna studied software engineering at NUST from 2002 to 2006."},
        {"title": "Books", "text": "Share a Book helps parents give away used school textbooks."},
    ]
    index = Index(chunks, vectors=[[1.0, 0.0], [0.0, 1.0]])
    found = index.search_with_vector("Where did Amna study at NUST?", [1.0, 0.0], k=1)
    assert found[0]["title"] == "Education"


def test_fusion_prefers_a_passage_found_by_both_rankers():
    education = {"title": "Education", "text": "NUST"}
    books = {"title": "Books", "text": "textbooks"}
    invoicer = {"title": "Invoicer", "text": "ClickUp"}
    fused = fuse(([education, books], [education, invoicer]), k=2)
    assert fused[0]["title"] == "Education"


def test_instructions_include_only_the_retrieved_passages():
    faqs = load_faqs(project_root() / "knowledge" / "faq.jsonl")
    profile = load_text(project_root() / "knowledge" / "knowledge.md")
    _searchable, pinned, guidance = chunk_profile(profile)
    passages = [*pinned, {"title": "Education", "text": "Studied at NUST."}]
    instructions = build_instructions("Amna Ahmad", passages, "Be brief.", faqs, guidance)
    assert "Studied at NUST." in instructions
    assert "Share a Book is a free Progressive Web App" not in instructions
    assert "Do not claim that ClickUp" in instructions
    assert len(instructions) < len(profile)
