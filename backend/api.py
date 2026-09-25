from __future__ import annotations

import uuid
import logging
import os
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.types import Scope
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
logger = logging.getLogger(__name__)


class FrontendFiles(StaticFiles):
    """Keep this locally served app's HTML, styles, and scripts in sync."""

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> FileResponse:
        # Always send current bytes, including to clients with old validators.
        # A 304 could otherwise preserve assets cached before this policy.
        return FileResponse(
            full_path,
            stat_result=stat_result,
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

try:
    from agents.concierge_agent import ConciergeAgent
except ImportError:  # pragma: no cover - dependencies may be unavailable
    logger.exception("Concierge dependencies could not be imported")
    ConciergeAgent = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="User question for the healthcare concierge")


class ChatResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    answer: str = Field(min_length=1)
    agents_used: list[str]
    request_id: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)


def _chat_response(payload: Any, started: float) -> ChatResponse:
    if not isinstance(payload, dict):
        raise ValueError("Invalid concierge response")
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Empty concierge answer")
    return ChatResponse(
        answer=answer,
        agents_used=payload.get("agents_used", []),
        request_id=payload.get("request_id", str(uuid.uuid4())),
        latency_ms=payload.get("latency_ms", int((perf_counter() - started) * 1000)),
    )


def create_api_app(concierge: Any | None = None) -> FastAPI:
    """Create the small backend API that exposes the concierge agent."""
    app = FastAPI(title="Health Concierge API", version="1.0.0")
    concierge_agent = concierge
    initialization_lock = Lock()
    query_lock = Lock()

    def get_concierge():
        nonlocal concierge_agent
        with initialization_lock:
            if concierge_agent is None:
                if ConciergeAgent is None:
                    raise RuntimeError("Concierge dependencies are unavailable")
                concierge_agent = ConciergeAgent()
        return concierge_agent

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        try:
            payload = get_concierge().get_health()
        except Exception as exc:
            logger.error("Concierge health check failed (%s)", type(exc).__name__)
            payload = {"status": "degraded", "services": {"concierge": {"status": "unavailable"}}}

        if not isinstance(payload, dict):
            payload = {}

        services = payload.get("services", {})
        if not isinstance(services, dict):
            services = {}

        if "concierge" not in services and isinstance(payload, dict):
            services = {key: value for key, value in payload.items() if key in {"concierge", "policy", "research"}}

        healthy = bool(services) and all(
            isinstance(service, dict) and service.get("status") == "available"
            for service in services.values()
        )
        return {
            "status": "ok" if healthy and payload.get("status", "ok") == "ok" else "degraded",
            "services": services,
        }

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail={"message": "Message cannot be empty."})

        started = perf_counter()
        try:
            agent = get_concierge()
        except Exception as exc:
            logger.error("Concierge initialization failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=503, detail="The healthcare concierge is not configured or is unavailable.") from exc
        # Reject concurrent work instead of queuing expensive requests after a
        # browser has timed out. The worker thread lets tools use asyncio.run.
        if not query_lock.acquire(blocking=False):
            raise HTTPException(status_code=503, detail="The healthcare concierge is busy. Please try again shortly.")
        try:
            payload = agent.answer_query_with_metadata(message)
            return _chat_response(payload, started)
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail="The specialist agent request timed out.") from exc
        except Exception as exc:
            logger.error("Concierge request failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=502, detail="The healthcare concierge is currently unavailable.") from exc
        finally:
            query_lock.release()

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", FrontendFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_api_app()
