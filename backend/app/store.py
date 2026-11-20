"""Conversation storage. Supabase in production, an in-memory store for local use and tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_inbox(rows: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in sorted(rows, key=lambda item: item["id"], reverse=True):
        cid = row["conversation_id"]
        item = grouped.get(cid)
        if item is None:
            grouped[cid] = {
                "conversation_id": cid,
                "conversation_name": row.get("conversation_name") or "Visitor",
                "preview": (row.get("content") or "").replace("\n", " ")[:140],
                "updated_at": row.get("created_at"),
                "unread": 0 if row.get("read") else 1,
                "needs_attention": bool(row.get("needs_attention")),
                "count": 1,
            }
            continue
        if item["conversation_name"] == "Visitor" and row.get("conversation_name"):
            item["conversation_name"] = row["conversation_name"]
        item["count"] += 1
        if not row.get("read"):
            item["unread"] += 1
        if row.get("needs_attention"):
            item["needs_attention"] = True
    items = list(grouped.values())
    items.sort(key=lambda item: (bool(item["needs_attention"]), item["updated_at"] or ""), reverse=True)
    return items


def thread_payload(rows: list[dict], attention: bool) -> dict:
    name = "Visitor"
    for row in reversed(rows):
        if row.get("conversation_name"):
            name = row["conversation_name"]
            break
    return {
        "conversation_id": rows[0]["conversation_id"] if rows else None,
        "name": name,
        "attention": attention,
        "started_at": rows[0]["created_at"] if rows else None,
        "count": len(rows),
        "messages": rows,
    }


class Store(Protocol):
    def insert(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        conversation_name: str | None = None,
        tool_calls: list | None = None,
        needs_attention: bool = False,
        read: bool = False,
    ) -> dict: ...

    def list_messages(self, conversation_id: str) -> list[dict]: ...

    def list_since(self, conversation_id: str, after_id: int) -> list[dict]: ...

    def inbox(self) -> list[dict]: ...

    def open_thread(self, conversation_id: str) -> dict: ...

    def resolve(self, conversation_id: str) -> None: ...

    def rename(self, conversation_id: str, name: str) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self._next = 1

    def insert(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        conversation_name: str | None = None,
        tool_calls: list | None = None,
        needs_attention: bool = False,
        read: bool = False,
    ) -> dict:
        row = {
            "id": self._next,
            "conversation_id": conversation_id,
            "conversation_name": conversation_name,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "needs_attention": needs_attention,
            "read": read,
            "created_at": utcnow(),
        }
        self._next += 1
        self.rows.append(row)
        return row

    def _for(self, conversation_id: str) -> list[dict]:
        return [row for row in self.rows if row["conversation_id"] == conversation_id]

    def list_messages(self, conversation_id: str) -> list[dict]:
        return sorted(self._for(conversation_id), key=lambda row: row["id"])

    def list_since(self, conversation_id: str, after_id: int) -> list[dict]:
        return [row for row in self.list_messages(conversation_id) if row["id"] > after_id]

    def inbox(self) -> list[dict]:
        return build_inbox(self.rows)

    def open_thread(self, conversation_id: str) -> dict:
        rows = self.list_messages(conversation_id)
        attention = any(row["needs_attention"] for row in rows)
        for row in rows:
            row["read"] = True
            row["needs_attention"] = False
        return thread_payload(rows, attention)

    def resolve(self, conversation_id: str) -> None:
        for row in self._for(conversation_id):
            row["needs_attention"] = False

    def rename(self, conversation_id: str, name: str) -> None:
        for row in self._for(conversation_id):
            row["conversation_name"] = name


class SupabaseStore:
    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client

        self.client = create_client(url, key)

    def insert(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        conversation_name: str | None = None,
        tool_calls: list | None = None,
        needs_attention: bool = False,
        read: bool = False,
    ) -> dict:
        payload = {
            "conversation_id": conversation_id,
            "conversation_name": conversation_name,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "needs_attention": needs_attention,
            "read": read,
        }
        result = self.client.table("messages").insert(payload).execute()
        return result.data[0]

    def list_messages(self, conversation_id: str) -> list[dict]:
        result = (
            self.client.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("id")
            .execute()
        )
        return result.data or []

    def list_since(self, conversation_id: str, after_id: int) -> list[dict]:
        result = (
            self.client.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .gt("id", after_id)
            .order("id")
            .execute()
        )
        return result.data or []

    def inbox(self) -> list[dict]:
        result = (
            self.client.table("messages")
            .select(
                "id,conversation_id,conversation_name,role,content,needs_attention,read,created_at"
            )
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        return build_inbox(result.data or [])

    def open_thread(self, conversation_id: str) -> dict:
        existing = self.list_messages(conversation_id)
        attention = any(row.get("needs_attention") for row in existing)
        updated = (
            self.client.table("messages")
            .update({"read": True, "needs_attention": False})
            .eq("conversation_id", conversation_id)
            .execute()
        )
        rows = sorted(updated.data or existing, key=lambda row: row["id"])
        for row in rows:
            row["read"] = True
            row["needs_attention"] = False
        return thread_payload(rows, attention)

    def resolve(self, conversation_id: str) -> None:
        (
            self.client.table("messages")
            .update({"needs_attention": False})
            .eq("conversation_id", conversation_id)
            .execute()
        )

    def rename(self, conversation_id: str, name: str) -> None:
        (
            self.client.table("messages")
            .update({"conversation_name": name})
            .eq("conversation_id", conversation_id)
            .execute()
        )
