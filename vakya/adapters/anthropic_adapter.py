"""
Anthropic Adapter — Connect Claude models to the Vākya protocol
=================================================================

Supports: Claude Opus, Sonnet, Haiku and future models.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from vakya.adapters.base import BaseAdapter, AdapterConfig
from vakya.identity import Duta
from vakya.message import Vakya, MessageType

logger = logging.getLogger("vakya.adapter.anthropic")


class AnthropicAdapter(BaseAdapter):
    """
    Adapter for Anthropic Claude models.

    Usage:
        from vakya.adapters import AnthropicAdapter, AdapterConfig
        from vakya.identity import create_claude_duta

        duta = create_claude_duta(model="claude-opus-4.6")
        config = AdapterConfig(api_key="sk-ant-...", model="claude-opus-4.6")
        adapter = AnthropicAdapter(config, duta)

        response = await adapter.send(message)
    """

    def __init__(self, config: AdapterConfig, duta: Duta):
        super().__init__(config, duta)
        self._client: Any = None

    async def connect(self) -> None:
        """Initialize Anthropic client."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install vakya[anthropic]"
            )

        self._client = AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )
        await super().connect()

    async def send(self, message: Vakya, context: list[Vakya] | None = None) -> Vakya:
        """Send a message to Claude and get a response."""
        if not self._client:
            await self.connect()

        prompt_messages = self.vakya_to_prompt(message, context)

        # Anthropic uses separate system parameter
        system_msg = ""
        api_messages = []
        for msg in prompt_messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                api_messages.append(msg)

        response = await self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_msg,
            messages=api_messages,
            temperature=self.config.temperature,
            **self.config.extra,
        )

        response_text = response.content[0].text if response.content else ""
        logger.debug(f"Claude response: {response_text[:100]}...")

        return self.response_to_vakya(response_text, message)

    async def stream(
        self, message: Vakya, context: list[Vakya] | None = None
    ) -> AsyncIterator[str]:
        """Stream a response from Claude."""
        if not self._client:
            await self.connect()

        prompt_messages = self.vakya_to_prompt(message, context)

        system_msg = ""
        api_messages = []
        for msg in prompt_messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                api_messages.append(msg)

        async with self._client.messages.stream(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_msg,
            messages=api_messages,
            temperature=self.config.temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def health(self) -> bool:
        """Check if Anthropic API is reachable."""
        try:
            if not self._client:
                await self.connect()
            # Simple health check - try a minimal request
            await self._client.messages.create(
                model=self.config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False
