"""
GLM Adapter — Connect Zhipu GLM models to the Vākya protocol
==============================================================

Supports: GLM-4, GLM-4V, ChatGLM, and Zhipu AI models.
Uses OpenAI-compatible API format.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from vakya.adapters.base import BaseAdapter, AdapterConfig
from vakya.identity import Duta
from vakya.message import Vakya

logger = logging.getLogger("vakya.adapter.glm")

# Default Zhipu API base URL
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


class GLMAdapter(BaseAdapter):
    """
    Adapter for Zhipu GLM models (GLM-4, GLM-4V, etc.).

    Uses the OpenAI-compatible API that Zhipu provides.

    Usage:
        from vakya.adapters import GLMAdapter, AdapterConfig
        from vakya.identity import create_glm_duta

        duta = create_glm_duta(model="glm-4")
        config = AdapterConfig(api_key="your-key", model="glm-4")
        adapter = GLMAdapter(config, duta)

        response = await adapter.send(message)
    """

    def __init__(self, config: AdapterConfig, duta: Duta):
        if config.base_url is None:
            config.base_url = ZHIPU_BASE_URL
        super().__init__(config, duta)
        self._client: Any = None

    async def connect(self) -> None:
        """Initialize GLM client via OpenAI-compatible interface."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package required for GLM adapter. "
                "Install with: pip install vakya[openai]"
            )

        self._client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )
        await super().connect()

    async def send(self, message: Vakya, context: list[Vakya] | None = None) -> Vakya:
        """Send a message to GLM and get a response."""
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
        logger.debug(f"GLM response: {response_text[:100]}...")

        return self.response_to_vakya(response_text, message)

    async def stream(
        self, message: Vakya, context: list[Vakya] | None = None
    ) -> AsyncIterator[str]:
        """Stream a response from GLM."""
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
        """Check if GLM API is reachable."""
        try:
            if not self._client:
                await self.connect()
            await self._client.models.list()
            return True
        except Exception as e:
            logger.error(f"GLM health check failed: {e}")
            return False
