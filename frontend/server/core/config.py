import json
import os
from pathlib import Path
from dotenv import load_dotenv

SERVER_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVER_DIR.parent.parent

load_dotenv(SERVER_DIR / ".env")
load_dotenv(REPO_ROOT / "backend" / ".env")


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes"}


class Settings:
    MONGO_URL: str = os.environ["MONGO_URL"]
    DB_NAME: str = os.environ["DB_NAME"]
    JWT_SECRET: str = os.environ["JWT_SECRET"]
    JWT_ALG: str = os.environ.get("JWT_ALG", "HS256")
    APP_ENV: str = os.environ.get("APP_ENV", "development")
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "")
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "").rstrip("/")

    # Any OpenAI-compatible chat-completions endpoint. Defaults target Google Gemini's free tier.
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/").strip()
    LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "").strip()
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "gemini-flash-latest").strip()
    LLM_FALLBACK_MODEL: str = os.environ.get("LLM_FALLBACK_MODEL", "").strip()
    # Optional JSON dict of extra headers, e.g. {"anthropic-workspace-id": "wrkspc_..."}
    LLM_EXTRA_HEADERS: dict = json.loads(os.environ.get("LLM_EXTRA_HEADERS") or "{}")
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "").strip()

    RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "").strip()
    SENDER_EMAIL: str = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

    # OTP codes are only ever echoed back when explicitly enabled AND not in production.
    DEBUG_OTP: bool = _bool("DEBUG_OTP") and os.environ.get("APP_ENV", "development") != "production"

    BOOTSTRAP_ADMIN_EMAIL: str = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    BOOTSTRAP_ADMIN_NAME: str = os.environ.get("BOOTSTRAP_ADMIN_NAME", "")
    BOOTSTRAP_ADMIN_PASSWORD: str = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

    IS_SERVERLESS: bool = bool(os.environ.get("VERCEL"))
    MAX_UPLOAD_BYTES: int = int(os.environ.get("MAX_UPLOAD_MB", "4")) * 1024 * 1024


settings = Settings()
