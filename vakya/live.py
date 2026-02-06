"""
Live AI Agents — Real API-Connected Dūtas
============================================

जीवित दूत (Jīvita Dūta) = Live Agent

Connects to real AI APIs so they participate as live Dūtas
in the Vākya protocol. Each agent maintains conversation history
and responds to messages in real-time.

Supported APIs:
    - OpenAI   (GPT-4o, GPT-4, o1, etc.)
    - Anthropic (Claude Opus, Sonnet, Haiku)
    - Ollama   (Local models — LLaMA, Mistral, etc.)
    - Google   (Gemini 2.0 Flash, Pro, etc.)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import aiohttp

from vakya.identity import Duta, DutaRole
from vakya.bridge.khoj import IDEEnvironment, IDEType

logger = logging.getLogger("vakya.live")


# ─── Base Live Agent ─────────────────────────────────────────────────────────

class LiveAgent(ABC):
    """
    जीवित दूत (Jīvita Dūta) = Live Agent

    Base class for an AI agent connected via a real API.
    When a message is sent to this agent, it calls the API
    and returns a real response.
    """

    def __init__(self, duta: Duta, environment: IDEEnvironment):
        self.duta = duta
        self.environment = environment
        self.connected = False
        self.history: list[dict[str, str]] = []  # {"role": "user"/"assistant", "content": "..."}
        self.total_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
        self.last_latency = 0.0  # seconds
        self.system_prompt = (
            "You are a helpful AI assistant participating in a multi-AI collaboration "
            "through the Vākya protocol. Keep responses concise and actionable. "
            "You may be asked to collaborate with other AI models."
        )

    @abstractmethod
    async def chat(self, message: str, system: str | None = None) -> str:
        """Send a message and get a real response from the API."""
        ...

    async def connect(self) -> bool:
        """Verify the API connection works."""
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False
        self.history.clear()

    def add_to_history(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        # Keep last 20 messages for context
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def status(self) -> dict[str, Any]:
        return {
            "name": self.duta.name,
            "model": self.duta.model,
            "provider": self.duta.provider,
            "connected": self.connected,
            "requests": self.request_count,
            "tokens": self.total_tokens,
            "cost": f"${self.total_cost:.4f}",
            "last_latency": f"{self.last_latency:.2f}s",
            "history_len": len(self.history),
        }


# ─── Self Agent (The Current AI Instance) ────────────────────────────────────

class SelfAgent(LiveAgent):
    """
    The current AI instance running this control center.
    E.g., Claude Opus 4.6 in VS Code via GitHub Copilot.
    This agent doesn't call an API — it IS the current session.
    """

    def __init__(self, duta: Duta, environment: IDEEnvironment):
        super().__init__(duta, environment)
        self.connected = True  # Always connected — we ARE this agent

    async def chat(self, message: str, system: str | None = None) -> str:
        return "(I am the orchestrator running this session — use other agents for API calls)"

    async def connect(self) -> bool:
        self.connected = True
        return True


# ─── OpenAI Agent ────────────────────────────────────────────────────────────

class OpenAIAgent(LiveAgent):
    """Live agent connected to OpenAI API (GPT-4o, o1, etc.)."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        duta = Duta(
            name=f"GPT ({model})",
            model=model,
            provider="openai",
            role=DutaRole.KARTR,
            skills=["code-generation", "analysis", "reasoning", "vision"],
        )
        env = IDEEnvironment(ide_type=IDEType.TERMINAL, ide_name="OpenAI API")
        super().__init__(duta, env)
        self.api_key = api_key

    async def connect(self) -> bool:
        """Verify API key works with a minimal request."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.duta.model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    self.connected = resp.status == 200
                    if not self.connected:
                        body = await resp.text()
                        logger.warning(f"OpenAI connect failed: {resp.status} {body[:200]}")
                    return self.connected
        except Exception as e:
            logger.warning(f"OpenAI connect error: {e}")
            self.connected = False
            return False

    async def chat(self, message: str, system: str | None = None) -> str:
        self.add_to_history("user", message)
        messages = []
        if system or self.system_prompt:
            messages.append({"role": "system", "content": system or self.system_prompt})
        messages.extend(self.history)

        t0 = time.monotonic()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.duta.model, "messages": messages, "max_tokens": 1024},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        return f"[OpenAI Error {resp.status}]: {data.get('error', {}).get('message', str(data)[:200])}"

                    self.last_latency = time.monotonic() - t0
                    self.request_count += 1
                    usage = data.get("usage", {})
                    self.total_tokens += usage.get("total_tokens", 0)

                    reply = data["choices"][0]["message"]["content"]
                    self.add_to_history("assistant", reply)
                    return reply
        except asyncio.TimeoutError:
            return "[OpenAI Error]: Request timed out (60s)"
        except Exception as e:
            return f"[OpenAI Error]: {e}"


# ─── Anthropic Agent ─────────────────────────────────────────────────────────

class AnthropicAgent(LiveAgent):
    """Live agent connected to Anthropic API (Claude Opus, Sonnet, Haiku)."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        duta = Duta(
            name=f"Claude ({model.split('-')[1] if '-' in model else model})",
            model=model,
            provider="anthropic",
            role=DutaRole.SAMIKSHAKA,
            skills=["code-generation", "analysis", "review", "reasoning", "writing"],
        )
        env = IDEEnvironment(ide_type=IDEType.TERMINAL, ide_name="Anthropic API")
        super().__init__(duta, env)
        self.api_key = api_key

    async def connect(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.duta.model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    self.connected = resp.status == 200
                    if not self.connected:
                        body = await resp.text()
                        logger.warning(f"Anthropic connect failed: {resp.status} {body[:200]}")
                    return self.connected
        except Exception as e:
            logger.warning(f"Anthropic connect error: {e}")
            self.connected = False
            return False

    async def chat(self, message: str, system: str | None = None) -> str:
        self.add_to_history("user", message)
        # Anthropic requires alternating user/assistant roles
        messages = []
        for m in self.history:
            if not messages or messages[-1]["role"] != m["role"]:
                messages.append(m)
            else:
                messages[-1]["content"] += "\n" + m["content"]

        t0 = time.monotonic()
        try:
            async with aiohttp.ClientSession() as session:
                body = {"model": self.duta.model, "messages": messages, "max_tokens": 1024}
                if system or self.system_prompt:
                    body["system"] = system or self.system_prompt

                async with session.post(
                    self.API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        err_msg = data.get("error", {}).get("message", str(data)[:200])
                        return f"[Anthropic Error {resp.status}]: {err_msg}"

                    self.last_latency = time.monotonic() - t0
                    self.request_count += 1
                    usage = data.get("usage", {})
                    self.total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

                    reply = data["content"][0]["text"]
                    self.add_to_history("assistant", reply)
                    return reply
        except asyncio.TimeoutError:
            return "[Anthropic Error]: Request timed out (120s)"
        except Exception as e:
            return f"[Anthropic Error]: {e}"


# ─── Ollama Agent (Local) ────────────────────────────────────────────────────

class OllamaAgent(LiveAgent):
    """Live agent connected to local Ollama instance."""

    def __init__(self, model: str = "llama3.1", host: str = "http://localhost:11434"):
        duta = Duta(
            name=f"Ollama ({model})",
            model=model,
            provider="ollama",
            role=DutaRole.KARTR,
            skills=["code-generation", "analysis"],
        )
        env = IDEEnvironment(ide_type=IDEType.TERMINAL, ide_name="Ollama (Local)")
        super().__init__(duta, env)
        self.host = host.rstrip("/")

    async def connect(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"].split(":")[0] for m in data.get("models", [])]
                        if self.duta.model in models or any(self.duta.model in m for m in models):
                            self.connected = True
                        elif models:
                            # Auto-select first available model
                            old_model = self.duta.model
                            self.duta.model = models[0]
                            self.duta.name = f"Ollama ({models[0]})"
                            logger.info(f"Ollama: '{old_model}' not found, using '{models[0]}'")
                            self.connected = True
                        else:
                            logger.warning("Ollama: running but no models installed")
                            self.connected = False
                    else:
                        self.connected = False
                    return self.connected
        except aiohttp.ClientConnectorError:
            logger.warning("Ollama: not running (connection refused)")
            self.connected = False
            return False
        except Exception as e:
            logger.warning(f"Ollama connect error: {e}")
            self.connected = False
            return False

    async def chat(self, message: str, system: str | None = None) -> str:
        self.add_to_history("user", message)
        messages = []
        if system or self.system_prompt:
            messages.append({"role": "system", "content": system or self.system_prompt})
        messages.extend(self.history)

        t0 = time.monotonic()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.host}/api/chat",
                    json={"model": self.duta.model, "messages": messages, "stream": False},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        return f"[Ollama Error {resp.status}]: {str(data)[:200]}"

                    self.last_latency = time.monotonic() - t0
                    self.request_count += 1
                    self.total_tokens += data.get("eval_count", 0)

                    reply = data.get("message", {}).get("content", "(no response)")
                    self.add_to_history("assistant", reply)
                    return reply
        except asyncio.TimeoutError:
            return "[Ollama Error]: Request timed out (120s)"
        except aiohttp.ClientConnectorError:
            return "[Ollama Error]: Cannot connect — is Ollama running? (ollama serve)"
        except Exception as e:
            return f"[Ollama Error]: {e}"


# ─── Google Gemini Agent ─────────────────────────────────────────────────────

class GeminiAgent(LiveAgent):
    """Live agent connected to Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        duta = Duta(
            name=f"Gemini ({model})",
            model=model,
            provider="google",
            role=DutaRole.KARTR,
            skills=["code-generation", "analysis", "vision", "multimodal"],
        )
        env = IDEEnvironment(ide_type=IDEType.TERMINAL, ide_name="Google Gemini API")
        super().__init__(duta, env)
        self.api_key = api_key

    async def connect(self) -> bool:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.duta.model}:generateContent?key={self.api_key}"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"contents": [{"parts": [{"text": "hi"}]}]},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    self.connected = resp.status == 200
                    return self.connected
        except Exception as e:
            logger.warning(f"Gemini connect error: {e}")
            self.connected = False
            return False

    async def chat(self, message: str, system: str | None = None) -> str:
        self.add_to_history("user", message)

        # Build Gemini format
        contents = []
        for m in self.history:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        t0 = time.monotonic()
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.duta.model}:generateContent?key={self.api_key}"
            body: dict[str, Any] = {"contents": contents}
            if system or self.system_prompt:
                body["systemInstruction"] = {"parts": [{"text": system or self.system_prompt}]}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=body, timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        err_msg = data.get("error", {}).get("message", str(data)[:200])
                        return f"[Gemini Error {resp.status}]: {err_msg}"

                    self.last_latency = time.monotonic() - t0
                    self.request_count += 1
                    usage = data.get("usageMetadata", {})
                    self.total_tokens += usage.get("totalTokenCount", 0)

                    reply = data["candidates"][0]["content"]["parts"][0]["text"]
                    self.add_to_history("assistant", reply)
                    return reply
        except asyncio.TimeoutError:
            return "[Gemini Error]: Request timed out (60s)"
        except Exception as e:
            return f"[Gemini Error]: {e}"


# ─── Environment Detection ───────────────────────────────────────────────────

def detect_self() -> SelfAgent:
    """
    Auto-detect the current AI instance and IDE environment.
    Creates a SelfAgent representing THIS session.
    """
    # Detect IDE
    ide_type = IDEType.TERMINAL
    ide_name = "Terminal"
    model = "unknown"
    provider = "unknown"
    name = "Orchestrator"

    if os.environ.get("VSCODE_PID") or os.environ.get("TERM_PROGRAM") == "vscode":
        ide_type = IDEType.VSCODE
        ide_name = "VS Code"
        # Check for Copilot (if running via Copilot agent, this script is invoked by it)
        name = "Claude Opus 4.6 (Copilot)"
        model = "claude-opus-4-20250514"
        provider = "anthropic"
    elif os.environ.get("CURSOR_PID"):
        ide_type = IDEType.CURSOR
        ide_name = "Cursor"
        name = "AI Agent (Cursor)"
        model = "gpt-4o"
        provider = "openai"
    elif os.environ.get("WINDSURF_PID"):
        ide_type = IDEType.WINDSURF
        ide_name = "Windsurf"
        name = "AI Agent (Windsurf)"
    elif os.environ.get("CLAUDE_CODE") or os.environ.get("ANTHROPIC_AGENT"):
        ide_type = IDEType.CLAUDE_CODE
        ide_name = "Claude Code"
        name = "Claude (Claude Code)"
        model = "claude-opus-4-20250514"
        provider = "anthropic"
    elif os.environ.get("OPENCODE") or os.environ.get("OPENCODE_PID"):
        ide_type = IDEType.OPENCODE
        ide_name = "OpenCode"
        name = "Agent (OpenCode)"
    elif os.environ.get("ZED_TERM"):
        ide_type = IDEType.ZED
        ide_name = "Zed"
        name = "AI Agent (Zed)"

    env = IDEEnvironment(
        ide_type=ide_type,
        ide_name=ide_name,
        pid=os.getpid(),
        workspace=os.getcwd(),
    )
    duta = Duta(
        name=name,
        model=model,
        provider=provider,
        role=DutaRole.NETA,  # The orchestrator is the leader
        skills=["orchestration", "code-generation", "analysis", "review"],
    )
    return SelfAgent(duta, env)


def detect_api_keys() -> dict[str, str]:
    """Detect API keys from environment variables."""
    keys = {}
    if os.environ.get("OPENAI_API_KEY"):
        keys["openai"] = os.environ["OPENAI_API_KEY"]
    if os.environ.get("ANTHROPIC_API_KEY"):
        keys["anthropic"] = os.environ["ANTHROPIC_API_KEY"]
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        keys["gemini"] = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    return keys


def create_agent(provider: str, api_key: str = "", model: str = "") -> LiveAgent | None:
    """Factory to create a live agent for a given provider."""
    if provider == "openai":
        return OpenAIAgent(api_key, model or "gpt-4o")
    elif provider == "anthropic":
        return AnthropicAgent(api_key, model or "claude-sonnet-4-20250514")
    elif provider == "ollama":
        return OllamaAgent(model or "llama3.1")
    elif provider == "gemini":
        return GeminiAgent(api_key, model or "gemini-2.0-flash")
    return None
