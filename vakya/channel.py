"""
Sūtra — Communication Channels
================================

सूत्र (Sūtra) = Thread / String / Connection

A Sūtra is a communication channel through which Dūtas exchange Vākyas.
Channels can be:
    - Direct (one-to-one)
    - Group (many-to-many, a Sabhā channel)
    - Broadcast (one-to-all)
    - Topic-based (subscribe to specific viṣayas)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from vakya.message import Vakya, MessageType


class SutraType(str, Enum):
    """Channel types."""

    DIRECT = "direct"        # One-to-one
    SABHA = "sabha"          # Group / assembly
    BROADCAST = "broadcast"  # One-to-all
    VISAYA = "visaya"        # Topic-based subscription


# Type for message handler callbacks
MessageHandler = Callable[[Vakya], Awaitable[None] | None]


class Sutra(BaseModel):
    """
    A Sūtra (सूत्र) — communication channel between Dūtas.

    Manages message flow, subscriptions, and channel history.
    """

    id: str = Field(
        default_factory=lambda: f"sutra-{uuid.uuid4().hex[:8]}",
        description="Channel ID",
    )
    name: str = Field(default="", description="Channel name")
    sutra_type: SutraType = Field(default=SutraType.SABHA, description="Channel type")
    members: list[str] = Field(default_factory=list, description="Member Dūta IDs")
    visaya: str | None = Field(default=None, description="Topic filter (for visaya channels)")
    created: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    itihas: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Message history (इतिहास = history)",
    )
    max_itihas: int = Field(default=1000, description="Max history size")

    # Runtime state (not serialized)
    _handlers: dict[str, list[MessageHandler]] = {}
    _lock: asyncio.Lock | None = None

    model_config = {"arbitrary_types_allowed": True}

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def join(self, duta_id: str) -> None:
        """A Dūta joins this channel."""
        if duta_id not in self.members:
            self.members.append(duta_id)

    def leave(self, duta_id: str) -> None:
        """A Dūta leaves this channel."""
        if duta_id in self.members:
            self.members.remove(duta_id)

    def subscribe(self, duta_id: str, handler: MessageHandler) -> None:
        """Subscribe a handler for messages on this channel."""
        if duta_id not in self._handlers:
            self._handlers[duta_id] = []
        self._handlers[duta_id].append(handler)
        self.join(duta_id)

    def unsubscribe(self, duta_id: str) -> None:
        """Remove all handlers for a Dūta."""
        self._handlers.pop(duta_id, None)
        self.leave(duta_id)

    async def send(self, message: Vakya) -> None:
        """
        Send a message through this channel.

        Routes to appropriate recipients based on channel type and message prapaka.
        """
        # Record in history
        self._record(message)

        # Determine recipients
        recipients = self._resolve_recipients(message)

        # Dispatch to handlers
        tasks = []
        for duta_id in recipients:
            if duta_id in self._handlers:
                for handler in self._handlers[duta_id]:
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        tasks.append(result)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def send_sync(self, message: Vakya) -> None:
        """Synchronous send — calls handlers directly (non-async only)."""
        self._record(message)
        recipients = self._resolve_recipients(message)

        for duta_id in recipients:
            if duta_id in self._handlers:
                for handler in self._handlers[duta_id]:
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        raise RuntimeError(
                            "Cannot call async handler from send_sync. Use 'await send()' instead."
                        )

    def _resolve_recipients(self, message: Vakya) -> list[str]:
        """Determine which members should receive the message."""
        if self.sutra_type == SutraType.BROADCAST:
            # Everyone except sender
            return [m for m in self.members if m != message.presaka]

        if self.sutra_type == SutraType.DIRECT:
            # Only the other party
            return [m for m in self.members if m != message.presaka]

        if message.prapaka is None:
            # No specific recipient = broadcast within channel
            return [m for m in self.members if m != message.presaka]

        if isinstance(message.prapaka, str):
            return [message.prapaka] if message.prapaka in self.members else []

        if isinstance(message.prapaka, list):
            return [p for p in message.prapaka if p in self.members]

        return []

    def _record(self, message: Vakya) -> None:
        """Record message in channel history."""
        entry = {
            "id": message.id,
            "presaka": message.presaka,
            "prapaka": message.prapaka,
            "prakara": message.prakara.value,
            "samaya": message.samaya,
            "preview": str(message)[:200],
        }
        self.itihas.append(entry)

        # Trim history if needed
        if len(self.itihas) > self.max_itihas:
            self.itihas = self.itihas[-self.max_itihas :]

    def get_itihas(
        self,
        limit: int = 50,
        prakara: MessageType | None = None,
        duta_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve channel history with optional filters.

        Args:
            limit: Max messages to return
            prakara: Filter by message type
            duta_id: Filter by sender
        """
        history = self.itihas

        if prakara is not None:
            history = [h for h in history if h["prakara"] == prakara.value]

        if duta_id is not None:
            history = [h for h in history if h["presaka"] == duta_id]

        return history[-limit:]

    def __str__(self) -> str:
        return f"सूत्र '{self.name}' ({self.sutra_type.value}) [{len(self.members)} members]"


# ─── Channel Factories ──────────────────────────────────────────────────────


def create_direct_sutra(duta_a: str, duta_b: str, name: str = "") -> Sutra:
    """Create a direct (one-to-one) channel between two Dūtas."""
    return Sutra(
        name=name or f"{duta_a}↔{duta_b}",
        sutra_type=SutraType.DIRECT,
        members=[duta_a, duta_b],
    )


def create_sabha_sutra(name: str, members: list[str] | None = None) -> Sutra:
    """Create a group/assembly channel."""
    return Sutra(
        name=name,
        sutra_type=SutraType.SABHA,
        members=members or [],
    )


def create_visaya_sutra(visaya: str, name: str = "") -> Sutra:
    """Create a topic-based subscription channel."""
    return Sutra(
        name=name or f"topic:{visaya}",
        sutra_type=SutraType.VISAYA,
        visaya=visaya,
    )
