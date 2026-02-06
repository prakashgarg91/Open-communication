"""
Vākya Web API — REST/HTTP interface
=====================================

Provides a FastAPI-based HTTP interface for:
    - Sending messages via REST
    - Querying assembly status
    - Viewing conversation history
    - Managing Dūtas and channels
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from vakya.protocol import VakyaProtocol, PROTOCOL_VERSION
from vakya.message import Vakya, MessageType
from vakya.router import SabhaRouter
from vakya.identity import Duta


class SendMessageRequest(BaseModel):
    presaka: str
    prapaka: str | list[str] | None = None
    prakara: str = "vakya"
    visaya: str | None = None
    sarira: dict[str, Any] = {}
    samvada_id: str | None = None


class RegisterDutaRequest(BaseModel):
    name: str
    model: str
    provider: str = "unknown"
    role: str = "kartr"
    skills: list[str] = []


def create_app(router: SabhaRouter | None = None) -> FastAPI:
    """
    Create the FastAPI web application.

    Args:
        router: Existing SabhaRouter to use, or creates a new one
    """
    app = FastAPI(
        title="Vākya API (वाक्य)",
        description="Open Protocol for AI-to-AI Communication",
        version=PROTOCOL_VERSION,
    )
    protocol = VakyaProtocol()

    if router is None:
        router = SabhaRouter(name="Vākya Web")

    # ─── Status ─────────────────────────────────────────────────────────

    @app.get("/")
    async def root():
        return {
            "name": "Vākya Protocol API",
            "namaste": "नमस्ते! Welcome to the Vākya protocol.",
            "version": PROTOCOL_VERSION,
            "status": router.status(),
        }

    @app.get("/status")
    async def status():
        return router.status()

    # ─── Dūta Management ────────────────────────────────────────────────

    @app.post("/dutas")
    async def register_duta(req: RegisterDutaRequest):
        duta = Duta(
            name=req.name,
            model=req.model,
            provider=req.provider,
            skills=req.skills,
        )
        router.register_duta(duta)
        return {"message": f"Dūta registered: {duta.name}", "duta_id": duta.id}

    @app.get("/dutas")
    async def list_dutas(role: str | None = None, skill: str | None = None):
        dutas = router.list_dutas(role=role, skill=skill)
        return [d.model_dump() for d in dutas]

    @app.get("/dutas/{duta_id}")
    async def get_duta(duta_id: str):
        duta = router.get_duta(duta_id)
        if not duta:
            raise HTTPException(status_code=404, detail="Dūta not found")
        return duta.model_dump()

    @app.delete("/dutas/{duta_id}")
    async def unregister_duta(duta_id: str):
        router.unregister_duta(duta_id)
        return {"message": f"Dūta removed: {duta_id}"}

    # ─── Message Sending ────────────────────────────────────────────────

    @app.post("/messages")
    async def send_message(req: SendMessageRequest):
        message = Vakya(
            presaka=req.presaka,
            prapaka=req.prapaka,
            prakara=MessageType(req.prakara),
            visaya=req.visaya,
            sarira=req.sarira,
            samvada_id=req.samvada_id,
        )
        await router.route(message)
        return {
            "message": "Message routed",
            "id": message.id,
            "wire": protocol.encode(message),
        }

    @app.get("/messages/{message_id}")
    async def get_message(message_id: str):
        msg = router.get_message(message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        return msg.to_dict()

    # ─── Conversations ──────────────────────────────────────────────────

    @app.get("/samvada/{samvada_id}")
    async def get_conversation(samvada_id: str):
        messages = router.get_samvada(samvada_id)
        return [m.to_dict() for m in messages]

    # ─── WebSocket for real-time observation ────────────────────────────

    @app.websocket("/ws/observe")
    async def observe(websocket: WebSocket):
        await websocket.accept()
        queue: list[dict] = []

        async def observer_callback(message: Vakya, channel: str):
            data = {
                "type": "message",
                "channel": channel,
                "presaka": message.presaka,
                "prapaka": message.prapaka,
                "prakara": message.prakara.value,
                "visaya": message.visaya,
                "sarira": message.sarira,
                "samaya": message.samaya,
                "id": message.id,
            }
            try:
                await websocket.send_json(data)
            except Exception:
                pass

        router.add_observer(observer_callback)
        try:
            await websocket.send_json({
                "type": "welcome",
                "message": "नमस्ते! Observing Vākya communications.",
                "status": router.status(),
            })
            # Keep alive
            while True:
                data = await websocket.receive_text()
                if data == "status":
                    await websocket.send_json({"type": "status", "data": router.status()})
        except WebSocketDisconnect:
            router.remove_observer(observer_callback)

    # ─── Protocol Validation ────────────────────────────────────────────

    @app.post("/validate")
    async def validate_message(raw: dict[str, Any]):
        import json
        is_valid, errors = protocol.validate(json.dumps(raw))
        return {"valid": is_valid, "errors": errors}

    return app
