"""
Dwār — Gateway & Transport Manager
=====================================

द्वार (Dwār) = Gate / Door / Gateway

Manages transport protocols for cross-IDE communication.
Supports multiple transport types to accommodate different
IDE environments and connection capabilities.

Transport Types:
    WebSocket  — Primary transport for real-time bidirectional communication
    Stdio      — Standard I/O for CLI tools (Claude Code, OpenCode, etc.)
    HTTP       — REST-based polling for simpler integrations
    Pipe       — Named pipes for high-performance local IPC
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Callable, Awaitable

from pydantic import BaseModel, Field

logger = logging.getLogger("vakya.bridge.dwar")


class TransportType(str, Enum):
    """Available transport protocols."""

    WEBSOCKET = "websocket"   # WebSocket (primary)
    STDIO = "stdio"           # Standard I/O (for CLI tools)
    HTTP = "http"             # HTTP polling
    PIPE = "pipe"             # Named pipes (local IPC)


class TransportMessage(BaseModel):
    """A message going through a transport layer."""

    type: str = Field(description="Message type (vakya, register, heartbeat, etc.)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")
    source: str | None = Field(default=None, description="Source agent/IDE ID")
    target: str | None = Field(default=None, description="Target agent/IDE ID")
    timestamp: str | None = Field(default=None, description="ISO timestamp")


# Type for message receive callbacks
MessageCallback = Callable[[TransportMessage], Awaitable[None] | None]


class Dwar(ABC):
    """
    द्वार (Dwār) = Gateway — abstract base for transport implementations.

    Each Dwār handles a specific transport protocol.
    Subclasses implement connect/disconnect/send/receive for their protocol.
    """

    def __init__(self, transport_type: TransportType):
        self.transport_type = transport_type
        self._connected = False
        self._callbacks: list[MessageCallback] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback for incoming messages."""
        self._callbacks.append(callback)

    async def _dispatch(self, message: TransportMessage) -> None:
        """Dispatch a received message to all callbacks."""
        for cb in self._callbacks:
            try:
                result = cb(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"द्वार callback error: {e}")

    @abstractmethod
    async def connect(self, endpoint: str, **kwargs: Any) -> None:
        """Connect to the endpoint."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the endpoint."""
        ...

    @abstractmethod
    async def send(self, message: TransportMessage) -> None:
        """Send a message through the transport."""
        ...

    @abstractmethod
    async def receive(self) -> AsyncIterator[TransportMessage]:
        """Receive messages (as an async iterator)."""
        ...


class WebSocketDwar(Dwar):
    """
    WebSocket transport gateway.

    Primary transport for real-time bidirectional communication.
    Used by VS Code, Cursor, and browser-based environments.
    """

    def __init__(self) -> None:
        super().__init__(TransportType.WEBSOCKET)
        self._ws = None
        self._endpoint = ""

    async def connect(self, endpoint: str, **kwargs: Any) -> None:
        """Connect to a WebSocket endpoint."""
        import websockets
        self._endpoint = endpoint
        self._ws = await websockets.connect(endpoint)
        self._connected = True
        logger.info(f"द्वार WebSocket connected: {endpoint}")

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False
        logger.info("द्वार WebSocket disconnected")

    async def send(self, message: TransportMessage) -> None:
        """Send a message over WebSocket."""
        if not self._ws:
            raise ConnectionError("WebSocket not connected")
        await self._ws.send(message.model_dump_json())

    async def receive(self) -> AsyncIterator[TransportMessage]:
        """Receive messages from WebSocket."""
        if not self._ws:
            raise ConnectionError("WebSocket not connected")
        async for raw in self._ws:
            try:
                data = json.loads(raw)
                msg = TransportMessage.model_validate(data)
                await self._dispatch(msg)
                yield msg
            except Exception as e:
                logger.warning(f"द्वार WebSocket parse error: {e}")


class StdioDwar(Dwar):
    """
    Standard I/O transport gateway.

    Uses stdin/stdout for communication. Ideal for CLI-based AI tools
    like Claude Code, OpenCode, and other terminal-based agents.

    Messages are sent as single-line JSON (newline-delimited JSON / NDJSON).
    """

    def __init__(self) -> None:
        super().__init__(TransportType.STDIO)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._subprocess: asyncio.subprocess.Process | None = None

    async def connect(self, endpoint: str = "", **kwargs: Any) -> None:
        """
        Connect to a stdio-based process.

        Args:
            endpoint: Command to spawn (empty = use current process stdin/stdout)
        """
        if endpoint:
            # Spawn a subprocess
            self._subprocess = await asyncio.create_subprocess_exec(
                *endpoint.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._reader = self._subprocess.stdout
            self._writer = self._subprocess.stdin
            logger.info(f"द्वार Stdio connected to subprocess: {endpoint}")
        else:
            # Use current process stdin/stdout
            loop = asyncio.get_event_loop()
            self._reader = asyncio.StreamReader()
            transport, _ = await loop.connect_read_pipe(
                lambda: asyncio.StreamReaderProtocol(self._reader),
                sys.stdin,
            )
            # For writing, we can use sys.stdout directly
            self._writer = None  # Will write to stdout directly
            logger.info("द्वार Stdio connected to current process")

        self._connected = True

    async def disconnect(self) -> None:
        """Close the stdio connection."""
        if self._subprocess:
            self._subprocess.terminate()
            self._subprocess = None
        self._reader = None
        self._writer = None
        self._connected = False
        logger.info("द्वार Stdio disconnected")

    async def send(self, message: TransportMessage) -> None:
        """Send a message via stdout (NDJSON format)."""
        line = message.model_dump_json() + "\n"
        if self._writer:
            self._writer.write(line.encode("utf-8"))
            await self._writer.drain()
        else:
            sys.stdout.write(line)
            sys.stdout.flush()

    async def receive(self) -> AsyncIterator[TransportMessage]:
        """Receive messages from stdin (NDJSON format)."""
        if not self._reader:
            raise ConnectionError("Stdio not connected")
        while True:
            line = await self._reader.readline()
            if not line:
                break
            try:
                data = json.loads(line.decode("utf-8").strip())
                msg = TransportMessage.model_validate(data)
                await self._dispatch(msg)
                yield msg
            except Exception as e:
                logger.warning(f"द्वार Stdio parse error: {e}")


class HttpDwar(Dwar):
    """
    HTTP transport gateway.

    Uses HTTP polling for environments that don't support persistent
    connections. Simpler but higher latency than WebSocket.
    """

    def __init__(self) -> None:
        super().__init__(TransportType.HTTP)
        self._endpoint = ""
        self._session = None
        self._poll_interval = 1.0  # seconds

    async def connect(self, endpoint: str, **kwargs: Any) -> None:
        """Connect to an HTTP endpoint."""
        import aiohttp
        self._endpoint = endpoint.rstrip("/")
        self._session = aiohttp.ClientSession()
        self._poll_interval = kwargs.get("poll_interval", 1.0)
        self._connected = True
        logger.info(f"द्वार HTTP connected: {endpoint}")

    async def disconnect(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False
        logger.info("द्वार HTTP disconnected")

    async def send(self, message: TransportMessage) -> None:
        """Send a message via HTTP POST."""
        if not self._session:
            raise ConnectionError("HTTP not connected")
        async with self._session.post(
            f"{self._endpoint}/messages",
            json=message.model_dump(),
        ) as resp:
            if resp.status != 200:
                logger.warning(f"द्वार HTTP send failed: {resp.status}")

    async def receive(self) -> AsyncIterator[TransportMessage]:
        """Poll for messages via HTTP GET."""
        if not self._session:
            raise ConnectionError("HTTP not connected")
        while self._connected:
            try:
                async with self._session.get(
                    f"{self._endpoint}/messages/poll",
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("messages", []):
                            msg = TransportMessage.model_validate(item)
                            await self._dispatch(msg)
                            yield msg
            except Exception as e:
                logger.warning(f"द्वार HTTP poll error: {e}")
            await asyncio.sleep(self._poll_interval)


def create_dwar(transport_type: TransportType) -> Dwar:
    """Factory function to create a gateway for the given transport type."""
    factories = {
        TransportType.WEBSOCKET: WebSocketDwar,
        TransportType.STDIO: StdioDwar,
        TransportType.HTTP: HttpDwar,
    }
    factory = factories.get(transport_type)
    if not factory:
        raise ValueError(f"Unsupported transport type: {transport_type}")
    return factory()
