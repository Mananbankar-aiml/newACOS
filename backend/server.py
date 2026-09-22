"""Local-dev entrypoint: supervisor runs `uvicorn server:app` from backend/; the API lives in frontend/server/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "frontend" / "server"))

from app import app  # noqa: E402,F401
