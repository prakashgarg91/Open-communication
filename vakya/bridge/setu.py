"""
Setu — Central Bridge Daemon
===============================

सेतु (Setu) = Bridge

The Setu is the central daemon that runs on the local machine and
connects AI agents across all IDE containers. It extends the Vākya
relay server with cross-IDE awareness, discovery integration, and
multi-transport support.

How it works:
    1. Setu starts on a well-known local port (default: 8765)
    2. AI agents from different IDEs connect via their Yojakas (connectors)
    3. Setu routes messages between all connected agents
    4. The Khoj (discovery) service tracks all agents
    5. Humans can observe all cross-IDE communication

    ┌──────────────┐      ┌───────────────┐      ┌──────────────┐
    │   VS Code    │      │               │      │  Claude Code │
    │  (Copilot)   │─────▶│     Setu      │◀─────│   (Claude)   │
    │              │◀─────│   (सेतु)      │─────▶│              │
    └──────────────┘      │               │      └──────────────┘
                          │   Bridge      │
    ┌──────────────┐      │   Daemon      │      ┌──────────────┐
    │   OpenCode   │─────▶│               │◀─────│   Zed Code   │
    │   (Agent)    │◀─────│               │─────▶│   (Agent)    │
    └──────────────┘      └───────┬───────┘      └──────────────┘
                                  │
                             👁 Human
                             Observer
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

from pydantic import BaseModel, Field

from vakya.protocol import VakyaProtocol, PROTOCOL_VERSION
from vakya.message import Vakya, MessageType
from vakya.identity import Duta
from vakya.router import SabhaRouter
from vakya.bridge.khoj import Khoj, IDEAgent, IDEEnvironment, IDEType

logger = logging.getLogger("vakya.bridge.setu")


class SetuConfig(BaseModel):
    """Configuration for the Setu bridge daemon."""

    host: str = Field(default="0.0.0.0", description="Listen host")
    port: int = Field(default=8765, description="Listen port")
    name: str = Field(default="Vākya Setu (सेतु)", description="Bridge name")
    heartbeat_interval: int = Field(default=30, description="Heartbeat interval (seconds)")
    cleanup_interval: int = Field(default=60, description="Stale agent cleanup interval")
    max_agent_age: int = Field(default=300, description="Max seconds before agent considered stale")
    enable_discovery: bool = Field(default=True, description="Enable Khoj discovery service")


class ConnectedAgent:
    """Tracks a connected agent with its IDE context."""

    def __init__(
        self,
        duta: Duta,
        websocket: ServerConnection,
        environment: IDEEnvironment | None = None,
        ide_agent: IDEAgent | None = None,
    ):
        self.duta = duta
        self.websocket = websocket
        self.environment = environment or IDEEnvironment()
        self.ide_agent = ide_agent
        self.connected_at = datetime.now(timezone.utc)
        self.last_active = datetime.now(timezone.utc)
        self.message_count = 0


class Setu:
    """
    सेतु (Setu) = Bridge — Central cross-IDE communication daemon.

    The Setu extends the basic Vākya relay with:
        - Cross-IDE agent registration and tracking
        - IDE environment awareness (knows which IDE each agent is in)
        - Integrated Khoj (discovery) service
        - Multi-transport message routing
        - Bridge status dashboard
        - Automatic stale agent cleanup

    Usage:
        setu = Setu()
        await setu.start()

    Or from CLI:
        vakya-bridge --port 8765
    """

    def __init__(self, config: SetuConfig | None = None):
        self.config = config or SetuConfig()
        self.protocol = VakyaProtocol()
        self.router = SabhaRouter(name=self.config.name)
        self.khoj = Khoj() if self.config.enable_discovery else None

        # Connected agents with IDE context
        self._agents: dict[str, ConnectedAgent] = {}  # duta_id -> ConnectedAgent
        self._observers: dict[str, ServerConnection] = {}  # observer_id -> websocket
        self._running = False
        self._cleanup_task: asyncio.Task | None = None

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def ide_summary(self) -> dict[str, list[str]]:
        """Get a summary of agents grouped by IDE."""
        summary: dict[str, list[str]] = {}
        for agent in self._agents.values():
            ide_name = agent.environment.ide_name
            if ide_name not in summary:
                summary[ide_name] = []
            summary[ide_name].append(f"{agent.duta.name} ({agent.duta.id})")
        return summary

    async def start(self) -> None:
        """Start the Setu bridge daemon."""
        self._running = True

        # Register with discovery
        if self.khoj:
            self.khoj.register_setu(self.config.host, self.config.port)

        # Set up human observer relay
        self.router.add_observer(self._relay_to_observers)

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(
            f"🌉 Setu (सेतु) bridge starting on "
            f"ws://{self.config.host}:{self.config.port}"
        )
        logger.info(f"   Protocol: Vākya v{PROTOCOL_VERSION}")
        logger.info(f"   Discovery: {'enabled' if self.khoj else 'disabled'}")
        logger.info(f"   Cross-IDE communication: ACTIVE")
        logger.info(f"   ────────────────────────────────────")
        logger.info(f"   Waiting for AI agents from any IDE...")

        async with websockets.serve(
            self._handle_connection,
            self.config.host,
            self.config.port,
        ):
            await asyncio.Future()  # Run forever

    async def stop(self) -> None:
        """Stop the Setu bridge."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Close all connections
        for agent in list(self._agents.values()):
            try:
                await agent.websocket.close()
            except Exception:
                pass

        for ws in list(self._observers.values()):
            try:
                await ws.close()
            except Exception:
                pass

        self._agents.clear()
        self._observers.clear()

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        """Handle a new incoming WebSocket connection."""
        duta_id = None
        try:
            # First message must be registration
            raw = await asyncio.wait_for(websocket.recv(), timeout=30)
            reg_data = json.loads(raw)
            msg_type = reg_data.get("type", "")

            if msg_type == "observer":
                await self._handle_observer(websocket, reg_data)
            elif msg_type == "register":
                duta_id = await self._handle_agent_register(websocket, reg_data)
                if duta_id:
                    await self._agent_message_loop(duta_id, websocket)
            else:
                # Legacy: treat as direct Dūta registration (compatible with VakyaRelay)
                duta_id = await self._handle_legacy_register(websocket, reg_data)
                if duta_id:
                    await self._agent_message_loop(duta_id, websocket)

        except asyncio.TimeoutError:
            logger.warning("Connection timed out waiting for registration")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {duta_id or 'unknown'}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            if duta_id and duta_id in self._agents:
                self._disconnect_agent(duta_id)

    async def _handle_observer(self, websocket: ServerConnection, data: dict) -> None:
        """Handle a human observer connection."""
        observer_id = data.get("id", f"observer-{len(self._observers)}")
        self._observers[observer_id] = websocket

        await websocket.send(json.dumps({
            "type": "welcome",
            "message": f"नमस्ते! Connected as observer to {self.config.name}",
            "bridge_status": self.status(),
        }))

        logger.info(f"👁 Observer connected: {observer_id}")

        # Keep alive
        try:
            async for _ in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._observers.pop(observer_id, None)
            logger.info(f"👁 Observer disconnected: {observer_id}")

    async def _handle_agent_register(
        self, websocket: ServerConnection, data: dict
    ) -> str | None:
        """Handle a new IDE agent registration (new Setu protocol)."""
        try:
            payload = data.get("payload", {})
            duta_data = payload.get("duta", {})
            env_data = payload.get("environment", {})

            duta = Duta.model_validate(duta_data)
            environment = IDEEnvironment.model_validate(env_data) if env_data else IDEEnvironment()

            # Register with router
            self.router.register_duta(duta)

            # Track with IDE context
            connected = ConnectedAgent(
                duta=duta,
                websocket=websocket,
                environment=environment,
            )
            self._agents[duta.id] = connected

            # Subscribe to broadcast channel
            self.router._broadcast.subscribe(
                duta.id,
                lambda msg, did=duta.id: self._deliver(did, msg),
            )

            # Send welcome with bridge info
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": (
                    f"नमस्ते {duta.name}! Connected to {self.config.name} "
                    f"from {environment.ide_name}"
                ),
                "bridge_status": self.status(),
                "peers": [
                    {
                        "id": a.duta.id,
                        "name": a.duta.name,
                        "ide": a.environment.ide_name,
                    }
                    for a in self._agents.values()
                    if a.duta.id != duta.id
                ],
            }))

            # Notify existing agents about the new peer
            await self._broadcast_peer_update(duta.id, "joined")

            logger.info(
                f"🔗 Agent connected: {duta.name} ({duta.id}) "
                f"from {environment.ide_name} "
                f"[{self.agent_count} agents total]"
            )
            return duta.id

        except Exception as e:
            logger.error(f"Agent registration failed: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Registration failed: {e}",
            }))
            return None

    async def _handle_legacy_register(
        self, websocket: ServerConnection, data: dict
    ) -> str | None:
        """Handle a legacy VakyaRelay-style registration."""
        try:
            duta = Duta.model_validate(data.get("duta", data))
            self.router.register_duta(duta)

            connected = ConnectedAgent(
                duta=duta,
                websocket=websocket,
                environment=IDEEnvironment(),  # Unknown IDE
            )
            self._agents[duta.id] = connected

            self.router._broadcast.subscribe(
                duta.id,
                lambda msg, did=duta.id: self._deliver(did, msg),
            )

            await websocket.send(json.dumps({
                "type": "welcome",
                "message": f"नमस्ते {duta.name}! Connected to {self.config.name}",
                "bridge_status": self.status(),
            }))

            logger.info(
                f"🔗 Agent connected (legacy): {duta.name} ({duta.id}) "
                f"[{self.agent_count} agents total]"
            )
            return duta.id

        except Exception as e:
            logger.error(f"Legacy registration failed: {e}")
            return None

    async def _agent_message_loop(self, duta_id: str, websocket: ServerConnection) -> None:
        """Main message loop for a connected agent."""
        async for raw in websocket:
            try:
                data = json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "heartbeat":
                    self._update_heartbeat(duta_id)
                elif msg_type == "vakya":
                    # A Vākya protocol message
                    payload = data.get("payload", data)
                    wire_json = json.dumps(payload)
                    vakya = self.protocol.decode(wire_json)
                    vakya.meta["source_ide"] = (
                        self._agents[duta_id].environment.ide_name
                        if duta_id in self._agents
                        else "unknown"
                    )
                    await self.router.route(vakya)
                    if duta_id in self._agents:
                        self._agents[duta_id].message_count += 1
                elif msg_type == "discover":
                    # Agent requesting peer discovery
                    await self._send_peer_list(duta_id, websocket)
                else:
                    # Try as raw Vākya wire message
                    try:
                        vakya = self.protocol.decode(raw)
                        await self.router.route(vakya)
                    except Exception:
                        logger.warning(f"Unknown message type from {duta_id}: {msg_type}")

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from {duta_id}: {e}")
            except Exception as e:
                logger.error(f"Error processing message from {duta_id}: {e}")

    async def _deliver(self, duta_id: str, message: Vakya) -> None:
        """Deliver a message to a connected agent."""
        if duta_id not in self._agents:
            return

        agent = self._agents[duta_id]
        try:
            wire_json = self.protocol.encode(message)
            transport_msg = json.dumps({
                "type": "vakya",
                "payload": json.loads(wire_json),
                "source": message.presaka,
                "source_ide": message.meta.get("source_ide", "unknown"),
            })
            await agent.websocket.send(transport_msg)
        except Exception as e:
            logger.warning(f"Failed to deliver to {duta_id}: {e}")

    async def _relay_to_observers(self, message: Vakya, channel: str) -> None:
        """Relay messages to all human observers with IDE context."""
        source_ide = message.meta.get("source_ide", "unknown")
        obs_data = json.dumps({
            "type": "observation",
            "channel": channel,
            "source_ide": source_ide,
            "message": message.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

        disconnected = []
        for obs_id, ws in self._observers.items():
            try:
                await ws.send(obs_data)
            except Exception:
                disconnected.append(obs_id)

        for obs_id in disconnected:
            self._observers.pop(obs_id, None)

    async def _broadcast_peer_update(self, duta_id: str, action: str) -> None:
        """Notify all agents about a peer joining/leaving."""
        agent = self._agents.get(duta_id)
        if not agent:
            return

        update = json.dumps({
            "type": "peer_update",
            "action": action,  # "joined" or "left"
            "peer": {
                "id": agent.duta.id,
                "name": agent.duta.name,
                "ide": agent.environment.ide_name,
                "model": agent.duta.model,
            },
            "total_peers": self.agent_count,
        })

        for aid, other in self._agents.items():
            if aid != duta_id:
                try:
                    await other.websocket.send(update)
                except Exception:
                    pass

    async def _send_peer_list(self, duta_id: str, websocket: ServerConnection) -> None:
        """Send the current peer list to a requesting agent."""
        peers = [
            {
                "id": a.duta.id,
                "name": a.duta.name,
                "ide": a.environment.ide_name,
                "model": a.duta.model,
                "skills": a.duta.skills,
                "active": True,
            }
            for a in self._agents.values()
            if a.duta.id != duta_id
        ]
        await websocket.send(json.dumps({
            "type": "peer_list",
            "peers": peers,
            "total": len(peers),
        }))

    def _update_heartbeat(self, duta_id: str) -> None:
        """Update the heartbeat timestamp for an agent."""
        if duta_id in self._agents:
            self._agents[duta_id].last_active = datetime.now(timezone.utc)

    def _disconnect_agent(self, duta_id: str) -> None:
        """Handle agent disconnection."""
        agent = self._agents.pop(duta_id, None)
        if agent:
            self.router.unregister_duta(duta_id)
            logger.info(
                f"🔌 Agent disconnected: {agent.duta.name} ({duta_id}) "
                f"from {agent.environment.ide_name} "
                f"[{self.agent_count} agents remaining]"
            )
            # Notify remaining agents
            asyncio.create_task(self._broadcast_peer_update_departed(agent))

    async def _broadcast_peer_update_departed(self, agent: ConnectedAgent) -> None:
        """Notify remaining agents about a departed peer."""
        update = json.dumps({
            "type": "peer_update",
            "action": "left",
            "peer": {
                "id": agent.duta.id,
                "name": agent.duta.name,
                "ide": agent.environment.ide_name,
            },
            "total_peers": self.agent_count,
        })
        for other in self._agents.values():
            try:
                await other.websocket.send(update)
            except Exception:
                pass

    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale agents."""
        while self._running:
            try:
                if self.khoj:
                    self.khoj.cleanup_stale(self.config.max_agent_age)
            except Exception as e:
                logger.warning(f"Cleanup error: {e}")
            await asyncio.sleep(self.config.cleanup_interval)

    def status(self) -> dict[str, Any]:
        """Get the current bridge status."""
        return {
            "name": self.config.name,
            "protocol_version": PROTOCOL_VERSION,
            "agents_connected": self.agent_count,
            "observers_connected": len(self._observers),
            "ide_breakdown": self.ide_summary,
            "total_messages": sum(a.message_count for a in self._agents.values()),
            "uptime_since": self._agents and min(
                a.connected_at.isoformat() for a in self._agents.values()
            ) or None,
        }


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

def main() -> None:
    """Start the Setu bridge daemon from the command line."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Vākya Setu (सेतु) — Cross-IDE AI Communication Bridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    vakya-bridge                          # Start with defaults
    vakya-bridge --port 9000              # Custom port
    vakya-bridge --host 0.0.0.0 --verbose # All interfaces, verbose logging

The Setu bridge connects AI agents across different IDEs:
    VS Code ↔ Claude Code ↔ OpenCode ↔ Zed ↔ Cursor ↔ ...
        """,
    )
    parser.add_argument("--host", default="0.0.0.0", help="Listen host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Listen port (default: 8765)")
    parser.add_argument("--name", default="Vākya Setu", help="Bridge name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    config = SetuConfig(host=args.host, port=args.port, name=args.name)
    setu = Setu(config)

    try:
        asyncio.run(setu.start())
    except KeyboardInterrupt:
        logger.info("Setu bridge stopped (keyboard interrupt)")


if __name__ == "__main__":
    main()
