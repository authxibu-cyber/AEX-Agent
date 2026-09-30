"""
FastAPI OpenAI-Compatible API Server for AEX Agent.
Serves on port 8642, providing external apps, dashboards, and integrations full access to AEX Agent.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from aex_agent.agent.core import EXAgent
from aex_agent.config import Config, load_config
from aex_agent.gateway.scheduler import CronScheduler
from aex_agent.memory.persistent import MemoryManager
from aex_agent.memory.store import SessionStore
from aex_constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_PORT, VERSION


class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None


def create_gateway_app(config: Optional[Config] = None) -> FastAPI:
    cfg = config or load_config()
    app = FastAPI(title="AEX Agent Gateway", version=VERSION)

    # CORS: same-origin only unless AEX_GATEWAY_CORS_ORIGINS is set explicitly.
    # Wildcard + credentials is a browser-auth bypass; never combine them by default.
    import os as _os

    _cors_raw = _os.environ.get("AEX_GATEWAY_CORS_ORIGINS", "").strip()
    _cors_origins = (
        [o.strip() for o in _cors_raw.split(",") if o.strip()]
        if _cors_raw
        else []
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=bool(_cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Authentication gate -----------------------------------------------
    # When no API key is configured, only loopback clients may call the API.
    # When a key IS configured (config.yaml gateway_api_key or AEX_GATEWAY_API_KEY),
    # remote clients must present it (Bearer header or ?key= query param).
    _api_key = (cfg.gateway_api_key or "").strip()

    async def _auth_gate(request: Request, call_next):
        client_host = request.client.host if request.client else ""
        is_local = client_host in ("127.0.0.1", "::1", "localhost")

        if _api_key:
            header = request.headers.get("authorization", "")
            presented = header[7:].strip() if header.lower().startswith("bearer ") else ""
            if not presented:
                presented = request.query_params.get("key", "").strip()
            key_ok = presented and presented == _api_key
        else:
            key_ok = False

        # /health stays open (unauthenticated, harmless telemetry)
        if request.url.path == "/health":
            return await call_next(request)
        if key_ok or is_local:
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: missing or invalid API key."},
        )

    app.middleware("http")(_auth_gate)

    mem_manager = MemoryManager()
    session_store = SessionStore()
    scheduler = CronScheduler()

    @app.on_event("startup")
    async def on_startup():
        asyncio.create_task(scheduler.start())

    @app.on_event("shutdown")
    async def on_shutdown():
        scheduler.stop()

    @app.get("/health")
    async def health():
        mem_stats = mem_manager.get_summary()
        return {
            "status": "healthy",
            "agent": "AEX Agent",
            "version": VERSION,
            "active_model": cfg.model,
            "active_provider": cfg.provider,
            "memory": mem_stats,
            "cron_jobs": len(scheduler.jobs),
        }

    @app.get("/v1/models")
    async def list_models():
        return {
            "object": "list",
            "data": [
                {
                    "id": cfg.model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "aex-agent",
                }
            ],
        }

    @app.get("/v1/memory")
    async def get_memory():
        return {
            "memory_md": mem_manager.read_memory(),
            "user_md": mem_manager.read_user(),
            "stats": mem_manager.get_summary(),
        }

    @app.post("/v1/memory")
    async def update_memory(data: Dict[str, str]):
        content = data.get("content", "").strip()
        target = data.get("target", "memory").lower()
        if not content:
            raise HTTPException(status_code=400, detail="Content must not be empty.")

        if target == "user":
            ok, msg = mem_manager.update_user(content)
        else:
            ok, msg = mem_manager.update_memory(content)
        return {"success": ok, "message": msg}

    @app.get("/v1/sessions")
    async def list_sessions():
        return {"sessions": session_store.list_sessions()}

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatCompletionRequest):
        # Extract latest user message
        user_msgs = [m for m in req.messages if m.role == "user"]
        if not user_msgs:
            raise HTTPException(status_code=400, detail="No user message provided.")
        latest_user_text = user_msgs[-1].content

        session_id = req.session_id or f"api_session_{int(time.time())}"
        agent = EXAgent(
            config=cfg,
            model=req.model or cfg.model,
            session_id=session_id,
        )

        history = [m.model_dump() for m in req.messages[:-1]]

        if req.stream:
            async def event_generator():
                token_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

                def on_stream(kind: str, text: str):
                    if kind == "content":
                        token_queue.put_nowait(text)

                async def run_agent_task():
                    try:
                        await agent.run_conversation_async(
                            user_message=latest_user_text,
                            conversation_history=history,
                            stream_callback=on_stream,
                        )
                    finally:
                        token_queue.put_nowait(None)

                asyncio.create_task(run_agent_task())

                chunk_id = f"chatcmpl_{int(time.time())}"
                while True:
                    token = await token_queue.get()
                    if token is None:
                        break

                    chunk_data = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": agent.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                # Send terminal [DONE]
                yield "data: [DONE]\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            result = await agent.run_conversation_async(
                user_message=latest_user_text,
                conversation_history=history,
            )
            return {
                "id": f"chatcmpl_{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": agent.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.get("response", ""),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }

    return app


def run_gateway(host: Optional[str] = None, port: Optional[int] = None) -> None:
    cfg = load_config()
    h = host or cfg.gateway_host or DEFAULT_GATEWAY_HOST
    p = port or cfg.gateway_port or DEFAULT_GATEWAY_PORT
    app = create_gateway_app(cfg)
    print(f"[*] Starting AEX Agent Gateway on http://{h}:{p}")
    uvicorn.run(app, host=h, port=p, log_level="info")


def main():
    run_gateway()


if __name__ == "__main__":
    main()
