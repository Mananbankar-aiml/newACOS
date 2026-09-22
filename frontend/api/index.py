"""
Vercel Python Serverless entrypoint for ACOS.

Vercel's Python runtime auto-detects an ASGI `app` in files under /api/ and serves it.
This file exposes the FastAPI app from ../server/app.py.

All /api/* requests hitting this Vercel project are routed here by vercel.json rewrites.
The FastAPI app's own routes are already prefixed with /api, so URLs match 1:1.
"""
import os
import sys
from pathlib import Path

# Vercel sets VERCEL=1 in its runtime — used inside app.py to skip the in-process scheduler loop
os.environ.setdefault("VERCEL", "1")

# Make ../server importable (the canonical FastAPI code lives one level up)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from app import app  # noqa: E402

# Vercel Python runtime picks up `app` as an ASGI handler
handler = app
