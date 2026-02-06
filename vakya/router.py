"""
Sabhā Router — Message Routing & Assembly Management
======================================================

सभा (Sabhā) = Assembly / Council / Parliament

The SabhaRouter manages:
    - Registration of Dūtas (AI agents)
    - Creation and management of Sūtras (channels)
    - Message routing between Dūtas
    - Broadcasting and topic-based distribution
    - Human observer (mānava/मानव) access
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from vakya.identity import Duta
from vakya.channel import Sutra, SutraType, create_sabha_sutra, create_direct_sutra
from vakya.message import Vakya, MessageType

logger = logging.getLogger("vakya.router")

# Observer callback type
ObserverCallback = Callable[[Vakya, str], Awaitable[None] | None]


class SabhaRouter:
    """
    The Sabhā Router — central message hub for AI-to-AI communication.

    सभा (Sabhā) = Assembly. The router manages an assembly of Dūtas,
    routing their messages through Sūtras (channels).

    Features:
        - Register/unregister Dūtas (AI agents)
        - Create channels (direct, group, topic-based)
        - Route messages to correct recipients
        - Human observers can watch all communications
        - Message logging and history

    Usage:
        router = SabhaRouter(name="Project Assembly")

        # Register AIs
        router.register_duta(claude)
        router.register_duta(gpt4)

        # Create a channel
        channel = router.create_sabha("code-review", [claude.id, gpt4.id])

        # Send a message
        await router.route(message)

        # Human observation
        router.add_observer(my_callback)
    """

    def __init__(self, name: str = "Sabhā"):
        self.name = name
        self.dutas: dict[str, Duta] = {}
        self.sutras: dict[str, Sutra] = {}
        self.observers: list[ObserverCallback] = []
        self.samvadas: dict[str, list[str]] = {}  # conversation_id -> message_ids
        self._message_store: dict[str, Vakya] = {}
        self._created = datetime.now(timezone.utc).isoformat()

        # Create default broadcast channel
        self._broadcast = create_sabha_sutra("सर्व (broadcast)")
        self._broadcast.sutra_type = SutraType.BROADCAST
        self.sutras[self._broadcast.id] = self._broadcast

        logger.info(f"सभा '{self.name}' initialized (Sabhā router ready)")

    # ─── Dūta Management ────────────────────────────────────────────────────

    def register_duta(self, duta: Duta) -> None:
        """Register an AI agent (Dūta) with the assembly."""
        self.dutas[duta.id] = duta
        self._broadcast.join(duta.id)
        logger.info(f"दूत registered: {duta}")

    def unregister_duta(self, duta_id: str) -> None:
        """Remove a Dūta from the assembly."""
        if duta_id in self.dutas:
            duta = self.dutas.pop(duta_id)
            # Remove from all channels
            for sutra in self.sutras.values():
                sutra.leave(duta_id)
            logger.info(f"दूत unregistered: {duta}")

    def get_duta(self, duta_id: str) -> Duta | None:
        """Get a registered Dūta by ID."""
        return self.dutas.get(duta_id)

    def list_dutas(self, role: str | None = None, skill: str | None = None) -> list[Duta]:
        """List registered Dūtas, optionally filtered by role or skill."""
        dutas = list(self.dutas.values())
        if role:
            dutas = [d for d in dutas if d.role.value == role]
        if skill:
            dutas = [d for d in dutas if d.has_skill(skill)]
        return dutas

    def find_capable_dutas(self, skills: list[str]) -> list[Duta]:
        """Find Dūtas that can handle tasks requiring specific skills."""
        return [d for d in self.dutas.values() if d.can_handle(skills) and d.active]

    # ─── Channel Management ─────────────────────────────────────────────────

    def create_sabha(self, name: str, member_ids: list[str] | None = None) -> Sutra:
        """Create a group channel (Sabhā)."""
        sutra = create_sabha_sutra(name, member_ids)
        self.sutras[sutra.id] = sutra
        logger.info(f"सूत्र created: {sutra}")
        return sutra

    def create_direct(self, duta_a_id: str, duta_b_id: str) -> Sutra:
        """Create a direct channel between two Dūtas."""
        # Check if direct channel already exists
        for sutra in self.sutras.values():
            if sutra.sutra_type == SutraType.DIRECT:
                if set(sutra.members) == {duta_a_id, duta_b_id}:
                    return sutra

        sutra = create_direct_sutra(duta_a_id, duta_b_id)
        self.sutras[sutra.id] = sutra
        logger.info(f"सूत्र created: {sutra}")
        return sutra

    def get_sutra(self, sutra_id: str) -> Sutra | None:
        """Get a channel by ID."""
        return self.sutras.get(sutra_id)

    def find_sutra_by_name(self, name: str) -> Sutra | None:
        """Find a channel by name."""
        for sutra in self.sutras.values():
            if sutra.name == name:
                return sutra
        return None

    # ─── Message Routing ────────────────────────────────────────────────────

    async def route(self, message: Vakya, sutra_id: str | None = None) -> None:
        """
        Route a message through the assembly.

        Routing logic:
            1. If sutra_id is given, send through that channel
            2. If message has specific prapaka, find/create appropriate channel
            3. Otherwise, broadcast to all
        """
        # Store message
        self._message_store[message.id] = message

        # Track conversation
        if message.samvada_id:
            if message.samvada_id not in self.samvadas:
                self.samvadas[message.samvada_id] = []
            self.samvadas[message.samvada_id].append(message.id)

        # Notify observers (humans watching)
        await self._notify_observers(message, sutra_id or "broadcast")

        # Route through specific channel
        if sutra_id and sutra_id in self.sutras:
            await self.sutras[sutra_id].send(message)
            return

        # Route to specific recipient(s)
        if message.prapaka:
            targets = (
                [message.prapaka] if isinstance(message.prapaka, str) else message.prapaka
            )
            for target_id in targets:
                sutra = self.create_direct(message.presaka, target_id)
                await sutra.send(message)
            return

        # Broadcast
        await self._broadcast.send(message)

    async def route_many(self, messages: list[Vakya]) -> None:
        """Route multiple messages in sequence."""
        for msg in messages:
            await self.route(msg)

    # ─── Human Observer System (मानव / Mānava) ─────────────────────────────

    def add_observer(self, callback: ObserverCallback) -> None:
        """
        Add a human observer callback.

        The callback receives (message, channel_id) for every message
        routed through the assembly. This allows humans to monitor
        AI-to-AI communication in real-time.
        """
        self.observers.append(callback)
        logger.info("मानव observer added (human observer connected)")

    def remove_observer(self, callback: ObserverCallback) -> None:
        """Remove a human observer."""
        if callback in self.observers:
            self.observers.remove(callback)

    async def _notify_observers(self, message: Vakya, channel: str) -> None:
        """Notify all human observers of a message."""
        for observer in self.observers:
            try:
                result = observer(message, channel)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Observer error: {e}")

    # ─── Conversation History ───────────────────────────────────────────────

    def get_samvada(self, samvada_id: str) -> list[Vakya]:
        """Get all messages in a conversation thread."""
        if samvada_id not in self.samvadas:
            return []
        return [
            self._message_store[mid]
            for mid in self.samvadas[samvada_id]
            if mid in self._message_store
        ]

    def get_message(self, message_id: str) -> Vakya | None:
        """Retrieve a specific message by ID."""
        return self._message_store.get(message_id)

    # ─── Assembly Info ──────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Get assembly status summary."""
        return {
            "name": self.name,
            "created": self._created,
            "dutas": {
                "total": len(self.dutas),
                "active": sum(1 for d in self.dutas.values() if d.active),
                "by_role": self._count_by_role(),
            },
            "sutras": {
                "total": len(self.sutras),
                "by_type": self._count_by_type(),
            },
            "messages": {
                "total": len(self._message_store),
                "conversations": len(self.samvadas),
            },
            "observers": len(self.observers),
        }

    def _count_by_role(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for duta in self.dutas.values():
            role = duta.role.value
            counts[role] = counts.get(role, 0) + 1
        return counts

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for sutra in self.sutras.values():
            stype = sutra.sutra_type.value
            counts[stype] = counts.get(stype, 0) + 1
        return counts

    def __str__(self) -> str:
        return (
            f"सभा '{self.name}': "
            f"{len(self.dutas)} दूत (agents), "
            f"{len(self.sutras)} सूत्र (channels), "
            f"{len(self._message_store)} वाक्य (messages)"
        )
