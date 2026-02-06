"""
Ollama Adapter — Connect local models to the Vākya protocol
==============================================================

Supports: Any model running on Ollama (LLaMA, Mistral, Phi, Gemma, etc.)
This enables fully local, private AI-to-AI communication.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

import aiohttp

from vakya.adapters.base import BaseAdapter, AdapterConfig
from vakya.identity import Duta
from vakya.message import Vakya

logger = logging.getLogger("vakya.adapter.ollama")

# Default Ollama server URL
OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaAdapter(BaseAdapter):
    """
    Adapter for locally-hosted models via Ollama.

    No API key needed — talks to your local Ollama server.

    Usage:
        from vakya.adapters import OllamaAdapter, AdapterConfig
        from vakya.identity import create_local_duta

        duta = create_local_duta(name="LLaMA", model="llama3.1:70b")
        config = AdapterConfig(model="llama3.1:70b")
        adapter = OllamaAdapter(config, duta)

        response = await adapter.send(message)
    """

    def __init__(self, config: AdapterConfig, duta: Duta):
        if config.base_url is None:
            config.base_url = OLLAMA_BASE_URL
        super().__init__(config, duta)
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> None:
        """Initialize HTTP session for Ollama."""
        self._session = aiohttp.ClientSession(
            base_url=self.config.base_url,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
        )
        await super().connect()

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        await super().disconnect()

    async def send(self, message: Vakya, context: list[Vakya] | None = None) -> Vakya:
        """Send a message to Ollama and get a response."""
        if not self._session:
            await self.connect()

        messages = self.vakya_to_prompt(message, context)

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        async with self._session.post("/api/chat", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise RuntimeError(f"Ollama error ({resp.status}): {error}")

            data = await resp.json()
            response_text = data.get("message", {}).get("content", "")

        logger.debug(f"Ollama response: {response_text[:100]}...")
        return self.response_to_vakya(response_text, message)

    async def stream(
        self, message: Vakya, context: list[Vakya] | None = None
    ) -> AsyncIterator[str]:
        """Stream a response from Ollama."""
        if not self._session:
            await self.connect()

        messages = self.vakya_to_prompt(message, context)

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        async with self._session.post("/api/chat", json=payload) as resp:
            async for line in resp.content:
                if line:
                    import json

                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content

    async def health(self) -> bool:
        """Check if Ollama server is running."""
        try:
            if not self._session:
                await self.connect()
            async with self._session.get("/api/tags") as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        if not self._session:
            await self.connect()

        async with self._session.get("/api/tags") as resp:
            data = await resp.json()
            return [m["name"] for m in data.get("models", [])]
