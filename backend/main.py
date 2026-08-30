"""FastAPI backend for the Skylark Drones BI agent.

Run:
    uvicorn backend.main:app --reload --port 8000

Also serves the built React frontend (frontend/dist) at "/" when present, so
the whole app can be deployed as a single service; during development run the
Vite dev server separately (see frontend/README or root README) and it'll
call this API via CORS.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent.llm_adapter import LLMAdapter, get_llm_adapter
from src.agent.orchestrator import run_conversation
from src.config import get_llm_provider, get_monday_client
from src.data.repo import DataRepo

app = FastAPI(title="Skylark Drones BI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_repo: DataRepo | None = None
_llm: LLMAdapter | None = None
_llm_error: str | None = None
_sessions: dict[str, list] = {}  # session_id -> provider-native conversation history


def get_repo() -> DataRepo:
    global _repo
    if _repo is None:
        _repo = DataRepo(get_monday_client())
    return _repo


def get_llm() -> tuple[LLMAdapter | None, str | None]:
    """Lazy + cached: lets the process start even if ANTHROPIC_API_KEY isn't
    set yet, and picks it up on the next request once it is."""
    global _llm, _llm_error
    if _llm is not None:
        return _llm, None
    try:
        _llm = get_llm_adapter(get_llm_provider())
        return _llm, None
    except Exception as exc:  # noqa: BLE001
        _llm_error = str(exc)
        return None, _llm_error


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str


@app.get("/api/health")
def health():
    _, llm_error = get_llm()
    return {
        "status": "ok",
        "monday_mode": os.environ.get("MONDAY_MODE", "mock"),
        "llm_ready": llm_error is None,
        "llm_error": llm_error,
    }


@app.get("/api/data-quality")
def data_quality():
    return get_repo().quality_report


@app.post("/api/data-refresh")
def data_refresh():
    get_repo().refresh()
    return {"status": "refreshed"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "message must not be empty")

    llm, llm_error = get_llm()
    if llm is None:
        raise HTTPException(503, f"LLM not configured: {llm_error}")

    session_id = req.session_id or str(uuid.uuid4())
    history = _sessions.get(session_id, [])

    answer, updated_history = run_conversation(get_repo(), llm, history, req.message)
    _sessions[session_id] = updated_history

    return ChatResponse(session_id=session_id, answer=answer)


@app.post("/api/session/{session_id}/reset")
def reset_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"status": "reset"}


_frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
