"""
Vākya Relay Server — WebSocket Message Relay
==============================================

The relay server is the central hub that:
    - Accepts WebSocket connections from Dūtas (AI agents)
    - Routes messages between connected agents
    - Provides real-time monitoring for humans
    - Persists conversation history

Think of it as a "switchboard" (विनिमय केन्द्र) for AI communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

from vakya.protocol import VakyaProtocol, PROTOCOL_VERSION
from vakya.message import Vakya, MessageType
from vakya.router import SabhaRouter
from vakya.identity import Duta

logger = logging.getLogger("vakya.server")


class VakyaRelay:
    """
    WebSocket relay server for the Vākya protocol.

    Dūtas connect via WebSocket, register themselves, and then
    exchange messages through the relay. Humans can connect as
    observers to watch the communication in real-time.

    Usage:
        relay = VakyaRelay(host="0.0.0.0", port=8765)
        await relay.start()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        name: str = "Vākya Relay",
    ):
        self.host = host
        self.port = port
        self.name = name
        self.protocol = VakyaProtocol()
        self.router = SabhaRouter(name=name)

        # Connection tracking
        self._connections: dict[str, ServerConnection] = {}  # duta_id -> websocket
        self._observers: dict[str, ServerConnection] = {}    # observer_id -> websocket
        self._running = False

    async def start(self) -> None:
        """Start the relay server."""
        self._running = True

        # Register human observer relay
        self.router.add_observer(self._relay_to_observers)

        logger.info(f"�DiG Vākya Relay starting on ws://{self.host}:{self.port}")
        logger.info(f"   Protocol version: {PROTOCOL_VERSION}")

        async with websockets.serve(self._handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def stop(self) -> None:
        """Stop the relay server."""
        self._running = False
        # Close all connections
        for ws in list(self._connections.values()):
            await ws.close()
        for ws in list(self._observers.values()):
            await ws.close()

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        """Handle a new WebSocket connection."""
        duta_id = None
        try:
            # First message must be registration
            raw = await asyncio.wait_for(websocket.recv(), timeout=30)
            reg_data = json.loads(raw)

            if reg_data.get("type") == "observer":
                # Human observer connection
                observer_id = reg_data.get("id", f"observer-{len(self._observers)}")
                self._observers[observer_id] = websocket
                await websocket.send(json.dumps({
                    "type": "welcome",
                    "message": f"नमस्ते! Connected as observer to {self.name}",
                    "status": self.router.status(),
                }))
                logger.info(f"👁 Observer connected: {observer_id}")
                # Keep alive — observers just receive
                await self._observer_loop(observer_id, websocket)
            else:
                # Dūta registration
                duta = Duta.model_validate(reg_data.get("duta", reg_data))
                duta_id = duta.id
                self._connections[duta_id] = websocket
                self.router.register_duta(duta)

                # Set up message handler for this Dūta
                main_channel = self.router._broadcast
                main_channel.subscribe(
                    duta_id,
                    lambda msg, did=duta_id: self._deliver(did, msg),
                )

                # Send welcome
                await websocket.send(json.dumps({
                    "type": "welcome",
                    "message": f"नमस्ते {duta.name}! Registered with {self.name}",
                    "duta_id": duta_id,
                    "sabha_status": self.router.status(),
                }))
                logger.info(f"🤖 Dūta connected: {duta}")

                # Message loop
                await self._message_loop(duta_id, websocket)

        except websockets.ConnectionClosed:
            logger.info(f"Connection closed: {duta_id or 'unknown'}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            if duta_id:
                self._connections.pop(duta_id, None)
                self.router.unregister_duta(duta_id)

    async def _message_loop(self, duta_id: str, websocket: ServerConnection) -> None:
        """Handle messages from a connected Dūta."""
        async for raw in websocket:
            try:
                # Decode the wire message
                message = self.protocol.decode(raw)
                message.presaka = duta_id  # Ensure sender is authenticated

                # Route through the assembly
                await self.router.route(message)

                # Acknowledge
                await websocket.send(json.dumps({
                    "type": "ack",
                    "message_id": message.id,
                    "samaya": datetime.now(timezone.utc).isoformat(),
                }))

            except Exception as e:
                logger.error(f"Message error from {duta_id}: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e),
                }))

    async def _observer_loop(self, observer_id: str, websocket: ServerConnection) -> None:
        """Keep observer connection alive and handle commands."""
        try:
            async for raw in websocket:
                data = json.loads(raw)
                cmd = data.get("command")

                if cmd == "status":
                    await websocket.send(json.dumps({
                        "type": "status",
                        "data": self.router.status(),
                    }))
                elif cmd == "history":
                    channel_id = data.get("channel_id")
                    if channel_id:
                        sutra = self.router.get_sutra(channel_id)
                        if sutra:
                            await websocket.send(json.dumps({
                                "type": "history",
                                "data": sutra.get_itihas(limit=data.get("limit", 50)),
                            }))
        except websockets.ConnectionClosed:
            pass
        finally:
            self._observers.pop(observer_id, None)
            logger.info(f"👁 Observer disconnected: {observer_id}")

    async def _deliver(self, duta_id: str, message: Vakya) -> None:
        """Deliver a message to a connected Dūta."""
        if duta_id in self._connections:
            try:
                wire = self.protocol.encode(message)
                await self._connections[duta_id].send(wire)
            except Exception as e:
                logger.error(f"Delivery failed to {duta_id}: {e}")

    async def _relay_to_observers(self, message: Vakya, channel: str) -> None:
        """Relay all messages to human observers."""
        observer_data = json.dumps({
            "type": "message",
            "channel": channel,
            "samaya": message.samaya,
            "presaka": message.presaka,
            "prapaka": message.prapaka,
            "prakara": message.prakara.value,
            "visaya": message.visaya,
            "sarira": message.sarira,
            "id": message.id,
        }, ensure_ascii=False)

        disconnected = []
        for obs_id, ws in self._observers.items():
            try:
                await ws.send(observer_data)
            except Exception:
                disconnected.append(obs_id)

        for obs_id in disconnected:
            self._observers.pop(obs_id, None)


def main():
    """CLI entry point for the relay server."""
    import argparse

    parser = argparse.ArgumentParser(description="Vākya Relay Server (वाक्य विनिमय सर्वर)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    parser.add_argument("--name", default="Vākya Relay", help="Server name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    relay = VakyaRelay(host=args.host, port=args.port, name=args.name)
    try:
        asyncio.run(relay.start())
    except KeyboardInterrupt:
        logger.info("Server stopped.")


if __name__ == "__main__":
    main()
