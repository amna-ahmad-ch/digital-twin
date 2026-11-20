"""Runtime configuration. Secrets come from the environment or the root .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def project_root() -> Path:
    override = os.environ.get("AVATAR_ROOT")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "knowledge").is_dir() and (candidate / "backend").is_dir():
            return candidate
    return here.parents[2]


@dataclass(frozen=True)
class Settings:
    root: Path
    openai_api_key: str
    model: str
    owner_name: str
    admin_password: str
    supabase_url: str
    supabase_key: str
    session_secret: str
    cookie_secure: bool
    store_mode: str

    @property
    def knowledge_dir(self) -> Path:
        return self.root / "knowledge"

    @property
    def frontend_dist(self) -> Path:
        return self.root / "frontend" / "dist"

    @property
    def first_name(self) -> str:
        parts = self.owner_name.split()
        return parts[0] if parts else self.owner_name


def _openai_model(value: str | None) -> str:
    """OpenAI model ids have no provider prefix. Accept a leftover openai/ name."""
    model = (value or "").strip() or "gpt-5.4-nano"
    if model.startswith("openai/"):
        return model.split("/", 1)[1]
    return model


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    root = project_root()
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    session_secret = os.environ.get("SESSION_SECRET", "").strip() or f"avatar::{admin_password}"
    owner = os.environ.get("OWNER_NAME", "").strip() or "Amna Ahmad"
    return Settings(
        root=root,
        openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        model=_openai_model(os.environ.get("MODEL", "")),
        owner_name=owner,
        admin_password=admin_password,
        supabase_url=os.environ.get("SUPABASE_URL", "").strip().rstrip("/"),
        supabase_key=os.environ.get("SUPABASE_KEY", "").strip(),
        session_secret=session_secret,
        cookie_secure=_flag(os.environ.get("COOKIE_SECURE")),
        store_mode=os.environ.get("AVATAR_STORE", "").strip().lower(),
    )
