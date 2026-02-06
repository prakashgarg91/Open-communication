"""
Base Adapter — Abstract Interface for AI Model Adapters
=========================================================

All AI model adapters inherit from BaseAdapter and implement
the core methods for sending/receiving Vākya messages.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field

from vakya.identity import Duta
from vakya.message import Vakya, MessageType

logger = logging.getLogger("vakya.adapter")


class AdapterConfig(BaseModel):
    """Configuration for an AI adapter."""

    api_key: str | None = Field(default=None, description="API key")
    base_url: str | None = Field(default=None, description="API base URL")
    model: str = Field(description="Model identifier")
    max_tokens: int = Field(default=4096, description="Max response tokens")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    timeout: int = Field(default=120, description="Request timeout in seconds")
    extra: dict[str, Any] = Field(default_factory=dict, description="Provider-specific options")


class BaseAdapter(ABC):
    """
    Abstract base class for AI model adapters.

    An adapter connects a Dūta (AI agent) to its underlying model API.
    It translates Vākya protocol messages into API calls and back.

    Subclasses must implement:
        - send()     — Send a message and get a response
        - stream()   — Stream a response (optional)
        - health()   — Check if the model is available
    """

    def __init__(self, config: AdapterConfig, duta: Duta):
        self.config = config
        self.duta = duta
        self._connected = False

    @property
    def name(self) -> str:
        return f"{self.duta.provider}:{self.config.model}"

    async def connect(self) -> None:
        """Initialize connection to the AI provider."""
        self._connected = True
        logger.info(f"Adapter connected: {self.name}")

    async def disconnect(self) -> None:
        """Close connection."""
        self._connected = False
        logger.info(f"Adapter disconnected: {self.name}")

    @abstractmethod
    async def send(self, message: Vakya, context: list[Vakya] | None = None) -> Vakya:
        """
        Send a Vākya message to the AI model and get a response.

        Args:
            message: The incoming Vakya message
            context: Previous messages in the conversation for context

        Returns:
            Response as a new Vakya message
        """
        ...

    async def stream(
        self, message: Vakya, context: list[Vakya] | None = None
    ) -> AsyncIterator[str]:
        """
        Stream a response from the AI model.

        Default implementation falls back to send().
        Override for true streaming support.
        """
        response = await self.send(message, context)
        yield response.sarira.get("text", "")

    @abstractmethod
    async def health(self) -> bool:
        """Check if the AI model is available and responding."""
        ...

    def vakya_to_prompt(self, message: Vakya, context: list[Vakya] | None = None) -> list[dict]:
        """
        Convert Vākya message(s) to the standard chat message format.

        This produces a list of {role, content} dicts that most LLM APIs accept.
        """
        messages = []

        # System prompt explaining the Vākya protocol context
        system_prompt = (
            "You are participating in a Vākya (वाक्य) protocol conversation — "
            "an open AI-to-AI communication system. "
            f"Your identity: {self.duta.name} ({self.duta.model}), "
            f"role: {self.duta.role.value}. "
            "Respond clearly and directly. When the message is a task (kārya), "
            "acknowledge and work on it. When it's a question (praśna), answer it."
        )
        messages.append({"role": "system", "content": system_prompt})

        # Add context messages
        if context:
            for ctx_msg in context:
                role = "assistant" if ctx_msg.presaka == self.duta.id else "user"
                content = self._format_message_content(ctx_msg)
                messages.append({"role": role, "content": content})

        # Add the current message
        content = self._format_message_content(message)
        messages.append({"role": "user", "content": content})

        return messages

    def _format_message_content(self, message: Vakya) -> str:
        """Format a Vakya message as readable text for the LLM."""
        parts = []

        # Header
        parts.append(f"[{message.prakara.value}] From: {message.presaka}")
        if message.visaya:
            parts.append(f"Subject: {message.visaya}")

        # Body
        text = message.sarira.get("text", "")
        if text:
            parts.append(text)

        # Include other sarira fields
        for key, value in message.sarira.items():
            if key != "text" and value:
                parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def response_to_vakya(
        self,
        response_text: str,
        original: Vakya,
        prakara: MessageType = MessageType.UTTARA,
    ) -> Vakya:
        """Convert an LLM response string back into a Vakya message."""
        return original.reply(
            presaka=self.duta.id,
            prakara=prakara,
            sarira={"text": response_text},
        )
