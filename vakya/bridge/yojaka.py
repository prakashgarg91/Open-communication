"""
Yojaka — IDE Connector Adapters
=================================

योजक (Yojaka) = Connector / Joiner / One who unites

A Yojaka connects an AI agent running inside an IDE to the Vākya Bridge (Setu).
Each IDE environment may use a different transport, so we provide
specific connectors for different connection types.

Connectors:
    WebSocketYojaka  — For VS Code, Cursor, browser-based IDEs
    StdioYojaka      — For Claude Code, OpenCode, terminal tools
    HttpYojaka       — For REST-based integrations
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from vakya.bridge.khoj import Khoj, IDEAgent, IDEEnvironment
from vakya.bridge.dwar import (
    Dwar,
    TransportType,
    TransportMessage,
    WebSocketDwar,
    StdioDwar,
    HttpDwar,
    create_dwar,
)
from vakya.identity import Duta
from vakya.message import Vakya
from vakya.protocol import VakyaProtocol

logger = logging.getLogger("vakya.bridge.yojaka")

# Callback for received Vakya messages
VakyaCallback = Callable[[Vakya], Awaitable[None] | None]


class BaseYojaka(ABC):
    """
    योजक (Yojaka) = Connector — base class for IDE connectors.

    A Yojaka is the bridge between an AI agent in an IDE and the
    central Setu (bridge) daemon. It handles:
        - Registering the agent with the discovery service
        - Connecting to the Setu via the appropriate transport
        - Sending and receiving Vākya messages
        - Heartbeat management
        - Graceful disconnect
    """

    def __init__(
        self,
        duta: Duta,
        setu_url: str = "ws://localhost:8765",
        transport_type: TransportType = TransportType.WEBSOCKET,
    ):
        self.duta = duta
        self.setu_url = setu_url
        self.transport_type = transport_type
        self.protocol = VakyaProtocol()
        self.khoj = Khoj()

        self._dwar: Dwar | None = None
        self._agent: IDEAgent | None = None
        self._callbacks: list[VakyaCallback] = []
        self._heartbeat_task: asyncio.Task | None = None
        self._receive_task: asyncio.Task | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def on_vakya(self, callback: VakyaCallback) -> None:
        """Register a callback for incoming Vākya messages."""
        self._callbacks.append(callback)

    async def connect(self) -> IDEAgent:
        """
        Connect to the Setu bridge and register this agent.

        Returns:
            The registered IDEAgent
        """
        # Detect the IDE environment
        environment = self.khoj.detect_environment()

        # Create the transport gateway
        self._dwar = create_dwar(self.transport_type)
        await self._dwar.connect(self.setu_url)

        # Register with the Setu
        reg_msg = TransportMessage(
            type="register",
            payload={
                "duta": json.loads(self.duta.model_dump_json()),
                "environment": json.loads(environment.model_dump_json()),
            },
            source=self.duta.id,
        )
        await self._dwar.send(reg_msg)

        # Register with local discovery
        self._agent = self.khoj.register_agent(
            duta_id=self.duta.id,
            duta_name=self.duta.name,
            transport=self.transport_type.value,
            endpoint=self.setu_url,
            capabilities=self.duta.skills,
            environment=environment,
        )

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start receiving
        self._receive_task = asyncio.create_task(self._receive_loop())

        self._connected = True
        logger.info(
            f"योजक: {self.duta.name} connected to Setu from "
            f"{environment.ide_name} via {self.transport_type.value}"
        )
        return self._agent

    async def disconnect(self) -> None:
        """Disconnect from the Setu and unregister."""
        self._connected = False

        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Unregister
        if self._agent:
            self.khoj.unregister_agent(self._agent.id)

        # Disconnect transport
        if self._dwar:
            await self._dwar.disconnect()

        logger.info(f"योजक: {self.duta.name} disconnected")

    async def send_vakya(self, message: Vakya) -> None:
        """
        Send a Vākya message through the bridge to other IDE agents.

        Args:
            message: A Vākya message to send
        """
        if not self._dwar or not self._connected:
            raise ConnectionError("Not connected to Setu")

        # Encode as wire format
        wire_json = self.protocol.encode(message)

        transport_msg = TransportMessage(
            type="vakya",
            payload=json.loads(wire_json),
            source=self.duta.id,
            target=message.prapaka,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        await self._dwar.send(transport_msg)

    async def discover_peers(self) -> list[IDEAgent]:
        """Discover other AI agents across IDEs."""
        agents = self.khoj.discover_agents()
        # Exclude self
        return [a for a in agents if a.duta_id != self.duta.id]

    async def _heartbeat_loop(self) -> None:
        """Periodically send heartbeats."""
        while self._connected:
            try:
                if self._agent:
                    self.khoj.heartbeat(self._agent.id)
                if self._dwar and self._dwar.is_connected:
                    hb = TransportMessage(
                        type="heartbeat",
                        source=self.duta.id,
                        payload={"active": True},
                    )
                    await self._dwar.send(hb)
            except Exception as e:
                logger.warning(f"योजक heartbeat error: {e}")
            await asyncio.sleep(30)

    async def _receive_loop(self) -> None:
        """Receive messages from the bridge."""
        if not self._dwar:
            return
        try:
            async for transport_msg in self._dwar.receive():
                if transport_msg.type == "vakya":
                    try:
                        # Decode the Vākya message
                        wire_json = json.dumps(transport_msg.payload)
                        vakya = self.protocol.decode(wire_json)
                        # Dispatch to callbacks
                        for cb in self._callbacks:
                            result = cb(vakya)
                            if asyncio.iscoroutine(result):
                                await result
                    except Exception as e:
                        logger.warning(f"योजक: Failed to decode message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"योजक receive loop error: {e}")


class WebSocketYojaka(BaseYojaka):
    """
    WebSocket connector for IDE environments with WebSocket support.

    Best for: VS Code, Cursor, Windsurf, browser-based tools
    """

    def __init__(self, duta: Duta, setu_url: str = "ws://localhost:8765"):
        super().__init__(duta, setu_url, TransportType.WEBSOCKET)


class StdioYojaka(BaseYojaka):
    """
    Stdio connector for CLI-based AI tools.

    Communicates using newline-delimited JSON (NDJSON) over stdin/stdout.
    Ideal for tools that are invoked as subprocesses or CLI commands.

    Best for: Claude Code, OpenCode, terminal-based AI agents
    """

    def __init__(self, duta: Duta, setu_url: str = ""):
        super().__init__(duta, setu_url, TransportType.STDIO)


class HttpYojaka(BaseYojaka):
    """
    HTTP polling connector for simpler integrations.

    Uses periodic HTTP requests to send/receive messages.
    Higher latency but works everywhere with HTTP support.

    Best for: Simple integrations, REST-only environments
    """

    def __init__(self, duta: Duta, setu_url: str = "http://localhost:8000"):
        super().__init__(duta, setu_url, TransportType.HTTP)
