"""Avatar web app: visitor chat, admin inbox, and the static UI."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.agent import build_runner, transcript
from app.auth import COOKIE, MAX_AGE, issue_token, token_is_valid
from app.config import Settings, load_settings
from app.guards import (
    ChatLimiter,
    clamp_message,
    clamp_name,
    DAILY_MODEL_CALLS,
    instant_number,
    parse_conversation_id,
    visitor_ip,
    visitor_needs_owner,
)
from app.knowledge import exact_faq, format_instant, load_faqs, load_text
from app.moderation import REFUSAL, message_is_flagged
from app.store import MemoryStore, Store, SupabaseStore

log = logging.getLogger("avatar")

PUBLIC_FILES = {
    "icons.svg",
    "avatar-human.png",
    "avatar-robot.png",
    "avatar-robot-round.png",
}


class LoginIn(BaseModel):
    password: str = ""


class VisitorIn(BaseModel):
    content: str = ""
    name: str | None = None


class HumanIn(BaseModel):
    content: str = ""


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def create_app(
    settings: Settings | None = None,
    store: Store | None = None,
    runner=None,
) -> FastAPI:
    settings = settings or load_settings()
    if store is None:
        store = _make_store(settings)
    faqs = load_faqs(settings.knowledge_dir / "faq.jsonl")
    profile = load_text(settings.knowledge_dir / "knowledge.md")
    style = load_text(settings.knowledge_dir / "style.md")
    if runner is None:
        runner = build_runner(settings, faqs, profile, style)
    faqs_by_number = {faq["faq"]: faq for faq in faqs}

    app = FastAPI(title="Avatar")
    app.state.settings = settings
    app.state.store = store
    app.state.runner = runner
    app.state.faqs = faqs
    app.state.limiter = ChatLimiter()

    async def moderator(text: str) -> bool:
        return await message_is_flagged(settings.openai_api_key, text)

    app.state.moderator = moderator

    def require_admin(request: Request) -> None:
        if not token_is_valid(settings, request.cookies.get(COOKIE)):
            raise HTTPException(status_code=401, detail="Sign in required")

    @app.get("/api/config")
    def config() -> dict:
        return {
            "owner_name": settings.owner_name,
            "storage": "memory" if isinstance(store, MemoryStore) else "supabase",
            "model_ready": bool(settings.openai_api_key),
            "suggestions": [faq["query"] for faq in faqs[:3]],
            "faqs": [{"faq": faq["faq"], "query": faq["query"]} for faq in faqs],
        }

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(conversation_id: str, after: int = 0) -> dict:
        cid = _cid(conversation_id)
        rows = store.list_since(cid, after) if after else store.list_messages(cid)
        name = "Visitor"
        for row in reversed(rows):
            if row.get("conversation_name"):
                name = row["conversation_name"]
                break
        return {"conversation_id": cid, "name": name, "messages": rows}

    @app.post("/api/conversations/{conversation_id}/messages")
    async def post_message(conversation_id: str, body: VisitorIn, request: Request) -> StreamingResponse:
        cid = _cid(conversation_id)
        if not app.state.limiter.allow(cid):
            raise HTTPException(
                status_code=429,
                detail="You're sending messages too quickly. Give it a moment and try again.",
            )
        content = clamp_message(body.content or "")
        if not content.strip():
            raise HTTPException(status_code=400, detail="Message is empty")
        name = clamp_name(body.name)
        if name:
            store.rename(cid, name)

        number = instant_number(content)
        saved = faqs_by_number.get(number) if number is not None else exact_faq(content, faqs)
        calls_model = number is None and saved is None and bool(settings.openai_api_key)
        if calls_model and await app.state.moderator(content):
            visitor = store.insert(
                conversation_id=cid,
                role="visitor",
                content=content.strip(),
                conversation_name=name,
            )
            avatar = store.insert(
                conversation_id=cid,
                role="avatar",
                content=REFUSAL,
                conversation_name=name,
                needs_attention=True,
                tool_calls=[{"name": "moderation", "detail": "flagged"}],
            )

            async def refused_events() -> AsyncIterator[str]:
                yield _sse({"type": "delta", "text": REFUSAL})
                yield _sse({"type": "done", "visitor": visitor, "message": avatar})

            return _stream(refused_events())
        if calls_model:
            ip = visitor_ip(
                request.headers.get("x-forwarded-for"),
                request.client.host if request.client else None,
            )
            if not app.state.limiter.allow_model_call(ip):
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"You've reached today's limit of {DAILY_MODEL_CALLS} questions. "
                        "Please try again in 24 hours. Saved answers such as Q1 still work."
                    ),
                )
        if number is not None or saved is not None:
            faq = saved
            answer = (
                format_instant(faq)
                if faq
                else "I don't have a saved answer for that number. Ask it in a sentence, or try one of the suggestions."
            )
            detail = f"Q{faq['faq']}" if faq else f"Q{number}"
            visitor = store.insert(
                conversation_id=cid,
                role="visitor",
                content=content.strip(),
                conversation_name=name,
            )
            avatar = store.insert(
                conversation_id=cid,
                role="avatar",
                content=answer,
                conversation_name=name,
                tool_calls=[{"name": "instant", "detail": detail}],
            )

            async def instant_events() -> AsyncIterator[str]:
                yield _sse({"type": "delta", "text": answer})
                yield _sse({"type": "done", "visitor": visitor, "message": avatar})

            return _stream(instant_events())

        visitor = store.insert(
            conversation_id=cid,
            role="visitor",
            content=content,
            conversation_name=name,
        )

        async def events() -> AsyncIterator[str]:
            yield _sse({"type": "status", "state": "thinking"})
            final: dict | None = None
            try:
                prompt = transcript(store.list_messages(cid), settings.owner_name)
                async for event in runner(prompt):
                    if event.get("type") == "result":
                        final = event
                    else:
                        yield _sse(event)
            except Exception:
                log.exception("Avatar run failed")
                final = {
                    "text": f"Something went wrong on my side. I've flagged it so {settings.first_name} can see it.",
                    "tool_calls": [],
                    "needs_attention": True,
                }
            if not final or not final.get("text"):
                final = {
                    "text": f"I lost the thread of that reply. I've flagged it so {settings.first_name} can see it.",
                    "tool_calls": (final or {}).get("tool_calls") or [],
                    "needs_attention": True,
                }
            avatar = store.insert(
                conversation_id=cid,
                role="avatar",
                content=final["text"],
                conversation_name=name,
                tool_calls=final.get("tool_calls") or None,
                needs_attention=bool(final.get("needs_attention")) or visitor_needs_owner(content),
            )
            yield _sse({"type": "done", "visitor": visitor, "message": avatar})

        return _stream(events())

    @app.post("/admin/login")
    def login(body: LoginIn):
        password = body.password or ""
        if not settings.admin_password or not _passwords_match(password, settings.admin_password):
            raise HTTPException(status_code=401, detail="Incorrect password")
        response = JSONResponse({"ok": True, "owner_name": settings.owner_name})
        response.set_cookie(
            COOKIE,
            issue_token(settings),
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=MAX_AGE,
            path="/",
        )
        return response

    @app.post("/admin/logout")
    def logout():
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE, path="/")
        return response

    @app.get("/admin/api/session")
    def session(request: Request) -> dict:
        require_admin(request)
        return {"owner_name": settings.owner_name}

    @app.get("/admin/api/conversations")
    def conversations(request: Request) -> dict:
        require_admin(request)
        return {"conversations": store.inbox()}

    @app.get("/admin/api/conversations/{conversation_id}")
    def open_conversation(conversation_id: str, request: Request) -> dict:
        require_admin(request)
        return store.open_thread(_cid(conversation_id))

    @app.post("/admin/api/conversations/{conversation_id}/messages")
    def human_message(conversation_id: str, body: HumanIn, request: Request) -> dict:
        require_admin(request)
        content = clamp_message(body.content or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Message is empty")
        cid = _cid(conversation_id)
        existing = store.list_messages(cid)
        name = next((row["conversation_name"] for row in reversed(existing) if row.get("conversation_name")), None)
        row = store.insert(
            conversation_id=cid,
            role="human",
            content=content,
            conversation_name=name,
            read=True,
        )
        return {"message": row}

    @app.post("/admin/api/conversations/{conversation_id}/resolve")
    def resolve(conversation_id: str, request: Request) -> dict:
        require_admin(request)
        store.resolve(_cid(conversation_id))
        return {"ok": True}

    dist = settings.frontend_dist

    @app.get("/")
    def visitor_page():
        return _page(dist / "index.html")

    @app.get("/admin")
    @app.get("/admin/")
    def admin_page():
        return _page(dist / "admin" / "index.html")

    assets = dist / "assets"
    if assets.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{filename}")
    def public_file(filename: str):
        if filename not in PUBLIC_FILES:
            raise HTTPException(status_code=404)
        path = dist / filename
        if not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path)

    return app


def _make_store(settings: Settings) -> Store:
    use_supabase = (
        settings.store_mode != "memory"
        and settings.supabase_url.startswith("https://")
        and settings.supabase_key.startswith("sb_secret_")
    )
    if use_supabase:
        return SupabaseStore(settings.supabase_url, settings.supabase_key)
    log.info("Using the in-memory conversation store")
    return MemoryStore()


def _cid(value: str) -> str:
    try:
        return parse_conversation_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _passwords_match(given: str, expected: str) -> bool:
    import secrets

    return secrets.compare_digest(given.encode(), expected.encode())


def _stream(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _page(path: Path):
    if not path.is_file():
        return JSONResponse(
            {"detail": "Frontend is not built yet. From frontend/, run npm install and npm run build."},
            status_code=503,
        )
    return FileResponse(path)


app = create_app()
