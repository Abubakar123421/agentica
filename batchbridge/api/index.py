"""Vercel Python Function entrypoint for the existing FastAPI application."""

import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_root))

from app.main import app  # noqa: E402,F401

