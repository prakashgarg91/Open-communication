"""
OpenAI Adapter — Connect GPT models to the Vākya protocol
============================================================

Supports: GPT-4o, GPT-4, GPT-3.5-turbo, o1, o3, and any OpenAI-compatible API.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from vakya.adapters.base import BaseAdapter, AdapterConfig
from vakya.identity import Duta
from vakya.message import Vakya, MessageType

logger = logging.getLogger("vakya.adapter.openai")


class OpenAIAdapter(BaseAdapter):
    """
    Adapter for OpenAI models (GPT-4o, o1, o3, etc.).

    Usage:
        from vakya.adapters import OpenAIAdapter, AdapterConfig
        from vakya.identity import create_gpt_duta

        duta = create_gpt_duta(model="gpt-4o")
        config = AdapterConfig(api_key="sk-...", model="gpt-4o")
        adapter = OpenAIAdapter(config, duta)

        response = await adapter.send(message)
    """

    def __init__(self, config: AdapterConfig, duta: Duta):
        super().__init__(config, duta)
        self._client: Any = None

    async def connect(self) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install vakya[openai]"
            )

        self._client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )
        await super().connect()

    async def send(self, message: Vakya, context: list[Vakya] | None = None) -> Vakya:
        """Send a message to OpenAI and get a response."""
        if not self._client:
            await self.connect()

        messages = self.vakya_to_prompt(message, context)

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **self.config.extra,
        )

        response_text = response.choices[0].message.content or ""
        logger.debug(f"OpenAI response: {response_text[:100]}...")

        return self.response_to_vakya(response_text, message)

    async def stream(
        self, message: Vakya, context: list[Vakya] | None = None
    ) -> AsyncIterator[str]:
        """Stream a response from OpenAI."""
        if not self._client:
            await self.connect()

        messages = self.vakya_to_prompt(message, context)

        stream = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
            **self.config.extra,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health(self) -> bool:
        """Check if OpenAI API is reachable."""
        try:
            if not self._client:
                await self.connect()
            await self._client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
