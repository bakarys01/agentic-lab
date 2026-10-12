from __future__ import annotations

import uuid
import logging
import os
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.types import Scope
from pydantic import BaseModel, ConfigDict, Field, field_validator
from dotenv import load_dotenv
from medinova.backend.storage import Store
from medinova.backend.title_generation import generate_title
from medinova.backend.auth import install_auth
from medinova.agents.config_loader import load_agent_definition
from medinova.agents.runtime import AgentRuntime
from medinova.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)


def build_concierge() -> AgentRuntime:
    return AgentRuntime(load_agent_definition("concierge"))


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

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="User question for the healthcare concierge")
    conversation_id: uuid.UUID
    request_id: uuid.UUID


class ConversationTitle(BaseModel):
    title: str = Field(min_length=1, max_length=80)

    @field_validator('title')
    @classmethod
    def nonempty_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError('Enter a conversation title.')
        return title


class ChatResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    answer: str = Field(min_length=1)
    agents_used: list[str]
    request_id: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)
    conversation_id: str | None = None


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


def create_api_app(concierge: Any | None = None, db_path: str | Path | None = None, title_generator=None) -> FastAPI:
    """Create the small backend API that exposes the concierge agent."""
    app = FastAPI(title="Health Concierge API", version="1.0.0")
    concierge_agent = concierge
    initialization_lock = Lock()
    query_lock = Lock()
    storage_lock = Lock()
    store = None
    title_generator = title_generator or generate_title

    def update_title(conversation_id: str, question: str, answer: str) -> None:
        try:
            get_store().apply_generated_title(conversation_id, title_generator(question, answer))
        except Exception as exc:
            logger.warning("Conversation title generation failed (%s)", type(exc).__name__)

    def get_store():
        nonlocal store
        with storage_lock:
            if store is None:
                path = Path(db_path or os.getenv('DATABASE_PATH', 'data/concierge.sqlite3'))
                if not path.is_absolute():
                    path = PROJECT_ROOT / path
                store = Store(path)
        return store

    identity = install_auth(app, get_store)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo passwords or medical content in validation error payloads.
        errors = [{'loc': list(error['loc']), 'msg': error['msg'], 'type': error['type']} for error in exc.errors()]
        return JSONResponse({'detail': errors}, status_code=422)

    @app.get('/api/conversations')
    def conversations(request: Request):
        user = identity(request)['user']
        return {'conversations': get_store().conversations(user['id'])}

    @app.post('/api/conversations', status_code=201)
    def create_conversation(request: Request):
        return get_store().create_conversation(identity(request)['user']['id'])

    @app.get('/api/conversations/{conversation_id}/messages')
    def messages(conversation_id: uuid.UUID, request: Request):
        return {'messages': get_store().messages(identity(request)['user']['id'], str(conversation_id))}

    @app.patch('/api/conversations/{conversation_id}')
    def rename_conversation(conversation_id: uuid.UUID, body: ConversationTitle, request: Request):
        return get_store().rename_conversation(identity(request)['user']['id'], str(conversation_id), body.title)

    @app.delete('/api/conversations/{conversation_id}', status_code=204)
    def delete_conversation(conversation_id: uuid.UUID, request: Request):
        get_store().delete_conversation(identity(request)['user']['id'], str(conversation_id))
        return Response(status_code=204)

    def get_concierge():
        nonlocal concierge_agent
        with initialization_lock:
            if concierge_agent is None:
                concierge_agent = build_concierge()
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
            services = {
                name: service
                for name, service in payload.items()
                if isinstance(service, dict) and "status" in service
            }

        healthy = bool(services) and all(
            isinstance(service, dict) and service.get("status") == "available"
            for service in services.values()
        )
        return {
            "status": "ok" if healthy and payload.get("status", "ok") == "ok" else "degraded",
            "services": services,
        }

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest, request: Request, background_tasks: BackgroundTasks) -> ChatResponse:
        user = identity(request)['user']
        conversation_id, request_id = str(body.conversation_id), str(body.request_id)
        get_store().messages(user['id'], conversation_id)
        message = body.message.strip()
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
        begun = False
        try:
            existing = get_store().begin_turn(user['id'], conversation_id, request_id, message)
            if existing is not None:
                return ChatResponse(**existing)
            begun = True
            history = get_store().history(conversation_id)
            payload = agent.answer_query_with_metadata(message, history=history)
            result = _chat_response(payload, started).model_copy(update={
                'request_id': request_id, 'conversation_id': conversation_id,
            })
            if get_store().finish_turn(conversation_id, request_id, result.model_dump()):
                background_tasks.add_task(update_title, conversation_id, message, result.answer)
            begun = False
            return result
        except HTTPException:
            raise
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail="The specialist agent request timed out.") from exc
        except Exception as exc:
            logger.error("Concierge request failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=502, detail="The healthcare concierge is currently unavailable.") from exc
        finally:
            try:
                if begun:
                    get_store().fail_turn(request_id)
            finally:
                query_lock.release()

    frontend_dir = PROJECT_ROOT / "frontend"
    if frontend_dir.exists():
        app.mount("/", FrontendFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_api_app()
