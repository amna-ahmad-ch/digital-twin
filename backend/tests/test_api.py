"""API behaviour: auth, guards, instant answers, and the human not waking the avatar."""

import uuid

from fastapi.testclient import TestClient

from app.config import Settings, project_root
from app.guards import MESSAGE_LIMIT, clamp_message, instant_number
from app.knowledge import best_faq, load_faqs
from app.main import create_app
from app.store import MemoryStore, build_inbox


def settings(openai_api_key: str = "") -> Settings:
    return Settings(
        root=project_root(),
        openai_api_key=openai_api_key,
        model="gpt-5.4-nano",
        owner_name="Amna Ahmad",
        admin_password="secret",
        supabase_url="",
        supabase_key="",
        session_secret="test-secret",
        cookie_secure=False,
        store_mode="memory",
    )


def app_with(runner=None, openai_api_key: str = ""):
    store = MemoryStore()
    application = create_app(settings(openai_api_key), store=store, runner=runner)

    async def allow_message(_text: str) -> bool:
        return False

    application.state.moderator = allow_message
    return TestClient(application), store, application


async def silent_runner(_transcript: str):
    yield {"type": "delta", "text": "Live reply"}
    yield {"type": "result", "text": "Live reply", "tool_calls": [], "needs_attention": False}


def test_clamp_and_instant_detection():
    assert clamp_message("hello") == "hello"
    long = "x" * (MESSAGE_LIMIT + 50)
    clamped = clamp_message(long)
    assert clamped.startswith("x" * MESSAGE_LIMIT)
    assert "truncated" in clamped
    assert instant_number("Q2") == 2
    assert instant_number("q12") == 12
    assert instant_number("Q2 please") is None
    assert instant_number("question") is None


def test_inbox_puts_attention_first():
    rows = [
        {"id": 1, "conversation_id": "a", "conversation_name": "Ana", "content": "older", "read": True, "needs_attention": False, "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": 2, "conversation_id": "b", "conversation_name": "Bo", "content": "needs you", "read": False, "needs_attention": True, "created_at": "2026-01-01T00:00:01+00:00"},
        {"id": 3, "conversation_id": "a", "conversation_name": "Ana", "content": "newest", "read": False, "needs_attention": False, "created_at": "2026-01-02T00:00:00+00:00"},
    ]
    inbox = build_inbox(rows)
    assert inbox[0]["conversation_id"] == "b"
    assert inbox[1]["preview"] == "newest"
    assert inbox[1]["unread"] == 1


def test_config_uses_owner_name():
    client, _store, _app = app_with(silent_runner)
    body = client.get("/api/config").json()
    assert body["owner_name"] == "Amna Ahmad"
    assert body["suggestions"]


def test_admin_routes_require_login_and_human_does_not_call_the_model():
    calls = {"n": 0}

    async def runner(transcript: str):
        calls["n"] += 1
        yield {"type": "result", "text": transcript, "tool_calls": [], "needs_attention": False}

    client, store, _app = app_with(runner)
    assert client.get("/admin/api/conversations").status_code == 401
    assert client.post("/admin/login", json={"password": "nope"}).status_code == 401
    logged_in = client.post("/admin/login", json={"password": "secret"})
    assert logged_in.status_code == 200
    assert client.get("/admin/api/session").json()["owner_name"] == "Amna Ahmad"

    cid = str(uuid.uuid4())
    client.post(f"/api/conversations/{cid}/messages", json={"content": "Hello there", "name": "Jordan M."})
    assert calls["n"] == 1
    human = client.post(f"/admin/api/conversations/{cid}/messages", json={"content": "It's me."})
    assert human.status_code == 200
    assert human.json()["message"]["role"] == "human"
    assert calls["n"] == 1
    roles = [row["role"] for row in store.list_messages(cid)]
    assert roles == ["visitor", "avatar", "human"]


def test_instant_answer_skips_the_model_and_restates_the_question():
    calls = {"n": 0}

    async def runner(_transcript: str):
        calls["n"] += 1
        if False:
            yield {}

    client, store, _app = app_with(runner)
    cid = str(uuid.uuid4())
    response = client.post(f"/api/conversations/{cid}/messages", json={"content": "Q1", "name": "Sam"})
    assert response.status_code == 200
    assert calls["n"] == 0
    avatar = store.list_messages(cid)[1]
    assert avatar["content"].startswith("**Q1:**")
    assert "NUST" in avatar["content"]
    assert avatar["tool_calls"][0]["name"] == "instant"


def test_suggestion_chip_text_skips_the_model():
    calls = {"n": 0}

    async def runner(_transcript: str):
        calls["n"] += 1
        if False:
            yield {}

    client, store, _app = app_with(runner, openai_api_key="sk-test")
    cid = str(uuid.uuid4())
    response = client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "Who is Amna Ahmad?", "name": "Sam"},
    )
    assert response.status_code == 200
    assert calls["n"] == 0
    avatar = store.list_messages(cid)[1]
    assert avatar["content"].startswith("**Q1:**")
    assert "NUST" in avatar["content"]
    assert avatar["tool_calls"][0] == {"name": "instant", "detail": "Q1"}


def test_long_message_is_truncated_before_it_is_stored():
    client, store, _app = app_with(silent_runner)
    cid = str(uuid.uuid4())
    response = client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "y" * (MESSAGE_LIMIT + 10), "name": "Sam"},
    )
    assert response.status_code == 200
    stored = store.list_messages(cid)[0]["content"]
    assert stored.startswith("y" * MESSAGE_LIMIT)
    assert "truncated" in stored


def test_rate_limit_rejects_before_the_model():
    calls = {"n": 0}

    async def runner(_transcript: str):
        calls["n"] += 1
        yield {"type": "result", "text": "no", "tool_calls": [], "needs_attention": False}

    client, _store, _app = app_with(runner)
    cid = str(uuid.uuid4())
    for _ in range(20):
        assert client.post(f"/api/conversations/{cid}/messages", json={"content": "Q1"}).status_code == 200
    blocked = client.post(f"/api/conversations/{cid}/messages", json={"content": "Q1"})
    assert blocked.status_code == 429
    assert "too quickly" in blocked.json()["detail"]
    assert calls["n"] == 0


def test_daily_model_cap_follows_the_ip_across_new_chats():
    from app.guards import DAILY_MODEL_CALLS

    calls = {"n": 0}

    async def runner(_transcript: str):
        calls["n"] += 1
        yield {"type": "result", "text": "live", "tool_calls": [], "needs_attention": False}

    client, _store, _app = app_with(runner, openai_api_key="sk-test")
    home = {"x-forwarded-for": "203.0.113.8"}
    for _ in range(DAILY_MODEL_CALLS):
        cid = str(uuid.uuid4())
        assert client.post(
            f"/api/conversations/{cid}/messages",
            json={"content": "What is your background?"},
            headers=home,
        ).status_code == 200
    blocked = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages",
        json={"content": "One more question"},
        headers=home,
    )
    assert blocked.status_code == 429
    assert "24 hours" in blocked.json()["detail"]
    assert calls["n"] == DAILY_MODEL_CALLS
    instant = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages",
        json={"content": "Q1"},
        headers=home,
    )
    assert instant.status_code == 200
    assert calls["n"] == DAILY_MODEL_CALLS
    other = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages",
        json={"content": "Hello from somewhere else"},
        headers={"x-forwarded-for": "198.51.100.4, 203.0.113.9"},
    )
    assert other.status_code == 200
    assert calls["n"] == DAILY_MODEL_CALLS + 1


def test_flagged_message_is_refused_before_the_model():
    calls = {"n": 0}

    async def runner(_transcript: str):
        calls["n"] += 1
        yield {"type": "result", "text": "should not run", "tool_calls": [], "needs_attention": False}

    client, store, application = app_with(runner, openai_api_key="sk-test")

    async def flag(_text: str) -> bool:
        return True

    application.state.moderator = flag
    cid = str(uuid.uuid4())
    response = client.post(f"/api/conversations/{cid}/messages", json={"content": "something harmful"})
    assert response.status_code == 200
    assert calls["n"] == 0
    rows = store.list_messages(cid)
    assert rows[1]["content"] == "I can't help with that."
    assert rows[1]["needs_attention"] is True
    allowed = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages",
        json={"content": "Q1"},
    )
    assert allowed.status_code == 200
    assert "I can't help with that." not in allowed.text
    assert calls["n"] == 0


def test_opening_a_thread_marks_it_read_and_reports_attention():
    client, store, _app = app_with(silent_runner)
    client.post("/admin/login", json={"password": "secret"})
    cid = str(uuid.uuid4())
    store.insert(conversation_id=cid, role="visitor", content="Can we talk?", conversation_name="Rae", needs_attention=True)
    inbox = client.get("/admin/api/conversations").json()["conversations"]
    assert inbox[0]["needs_attention"] is True
    assert inbox[0]["unread"] == 1
    opened = client.get(f"/admin/api/conversations/{cid}").json()
    assert opened["attention"] is True
    assert opened["name"] == "Rae"
    assert store.list_messages(cid)[0]["read"] is True
    assert store.list_messages(cid)[0]["needs_attention"] is False
    again = client.get(f"/admin/api/conversations/{cid}").json()
    assert again["attention"] is False


def test_bad_conversation_id_is_rejected():
    client, _store, _app = app_with(silent_runner)
    assert client.get("/api/conversations/not-a-uuid").status_code == 400


def test_faq_matcher_finds_a_saved_question():
    faqs = load_faqs(project_root() / "knowledge" / "faq.jsonl")
    match = best_faq("Tell me about your FoodSafety RAG project", faqs)
    assert match is not None
    assert match["faq"] == 7
