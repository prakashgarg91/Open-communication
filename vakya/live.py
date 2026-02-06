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
    - Kimi CLI (Moonshot AI coding agent — subprocess)
    - OpenCode CLI (GLM-4.7, multi-provider coding agent — subprocess)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
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

# Embedding models should not be used for chat
OLLAMA_EMBED_KEYWORDS = {"embed", "embedding", "nomic-embed", "mxbai-embed", "bge-", "e5-"}


def _is_chat_model(name: str) -> bool:
    """Return True if an Ollama model is a chat model (not embedding)."""
    lower = name.lower()
    return not any(kw in lower for kw in OLLAMA_EMBED_KEYWORDS)


class OllamaAgent(LiveAgent):
    """Live agent connected to local Ollama instance."""

    def __init__(self, model: str = "auto", host: str = "http://localhost:11434"):
        # Short display name (strip :latest but keep :cloud etc.)
        display = model.replace(":latest", "") if model != "auto" else model
        duta = Duta(
            name=f"Ollama ({display})",
            model=model,  # Will be resolved to full tag in connect()
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
                    if resp.status != 200:
                        self.connected = False
                        return False

                    data = await resp.json()
                    # Full names with tags (e.g. 'kimi-k2.5:cloud', 'glm-4.7-flash:latest')
                    all_models = [m["name"] for m in data.get("models", [])]
                    chat_models = [m for m in all_models if _is_chat_model(m)]

                    if not chat_models:
                        logger.warning("Ollama: running but no chat models installed")
                        self.connected = False
                        return False

                    wanted = self.duta.model

                    if wanted == "auto":
                        # Auto-select first chat model
                        self._set_model(chat_models[0])
                        self.connected = True
                        return True

                    # Try exact match first → then base-name match
                    for full in chat_models:
                        if full == wanted or full.split(":")[0] == wanted:
                            self._set_model(full)
                            self.connected = True
                            return True

                    # Fuzzy: substring match
                    for full in chat_models:
                        if wanted.lower() in full.lower() or full.split(":")[0].lower() in wanted.lower():
                            self._set_model(full)
                            self.connected = True
                            return True

                    logger.warning(f"Ollama: model '{wanted}' not found. Available: {chat_models}")
                    self.connected = False
                    return False

        except aiohttp.ClientConnectorError:
            logger.warning("Ollama: not running (connection refused)")
            self.connected = False
            return False
        except Exception as e:
            logger.warning(f"Ollama connect error: {e}")
            self.connected = False
            return False

    def _set_model(self, full_name: str):
        """Set the model to the full Ollama tag name."""
        self.duta.model = full_name
        display = full_name.replace(":latest", "")
        self.duta.name = f"Ollama ({display})"

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


# ─── Kimi CLI Agent (Subprocess) ─────────────────────────────────────────────

class KimiCLIAgent(LiveAgent):
    """
    Live agent that runs Kimi CLI as a subprocess.
    Kimi CLI is a coding agent from Moonshot AI — similar to Claude Code.
    It runs in --print mode (non-interactive) with --final-message-only.
    """

    def __init__(self, work_dir: str = "", model: str = ""):
        duta = Duta(
            name="Kimi CLI",
            model=model or "kimi-k2.5",
            provider="kimi",
            role=DutaRole.KARTR,
            skills=["code-generation", "analysis", "file-editing", "testing"],
        )
        env = IDEEnvironment(ide_type=IDEType.TERMINAL, ide_name="Kimi CLI")
        super().__init__(duta, env)
        self.work_dir = work_dir or os.getcwd()
        self._kimi_path = shutil.which("kimi") or "kimi"

    async def connect(self) -> bool:
        """Verify kimi CLI is available."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [self._kimi_path, "--version"],
                    capture_output=True, text=True, timeout=10,
                ),
            )
            if result.returncode == 0 and "kimi" in result.stdout.lower():
                version = result.stdout.strip().split("\n")[0]
                self.duta.name = f"Kimi CLI ({version})"
                self.connected = True
                logger.info(f"Kimi CLI connected: {version}")
                return True
            self.connected = False
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"Kimi CLI connect error: {e}")
            self.connected = False
            return False

    async def chat(self, message: str, system: str | None = None) -> str:
        """Run kimi CLI with a prompt and return the output."""
        self.add_to_history("user", message)

        cmd = [
            self._kimi_path,
            "--print",
            "--final-message-only",
            "--work-dir", self.work_dir,
            "--prompt", message,
        ]

        if system:
            # Prepend system context to the prompt
            cmd[-1] = f"[Context: {system}]\n\n{message}"

        t0 = time.monotonic()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True, text=True,
                    timeout=300,  # 5 min max for complex tasks
                    cwd=self.work_dir,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                ),
            )
            self.last_latency = time.monotonic() - t0
            self.request_count += 1

            if result.returncode == 0:
                reply = result.stdout.strip()
                if not reply and result.stderr.strip():
                    reply = f"(stderr output)\n{result.stderr.strip()[:500]}"
                if not reply:
                    reply = "(Kimi CLI returned no output)"
                self.add_to_history("assistant", reply)
                # Estimate tokens (rough: ~4 chars per token)
                self.total_tokens += len(reply) // 4
                return reply
            else:
                error = result.stderr.strip()[:500] or result.stdout.strip()[:500]
                return f"[Kimi CLI Error (exit {result.returncode})]: {error}"

        except subprocess.TimeoutExpired:
            self.last_latency = time.monotonic() - t0
            return "[Kimi CLI Error]: Command timed out (5 min limit)"
        except FileNotFoundError:
            return "[Kimi CLI Error]: kimi command not found. Install: pip install kimi-cli"
        except Exception as e:
            self.last_latency = time.monotonic() - t0
            return f"[Kimi CLI Error]: {e}"


# ─── OpenCode CLI Agent (Subprocess) ─────────────────────────────────────────

class OpenCodeCLIAgent(LiveAgent):
    """
    Live agent that runs OpenCode CLI as a subprocess.
    OpenCode is a coding agent that supports multiple providers/models
    including free GLM models (opencode/glm-4.7-free).

    Usage: opencode run -m <model> "prompt"
    """

    def __init__(self, work_dir: str = "", model: str = "zai-coding-plan/glm-4.7"):
        duta = Duta(
            name="OpenCode (GLM-4.7)",
            model=model,
            provider="opencode",
            role=DutaRole.KARTR,
            skills=["code-generation", "analysis", "file-editing", "testing"],
        )
        env = IDEEnvironment(ide_type=IDEType.OPENCODE, ide_name="OpenCode")
        super().__init__(duta, env)
        self.work_dir = work_dir or os.getcwd()
        self._opencode_path = shutil.which("opencode") or "opencode"
        self._model = model

    async def connect(self) -> bool:
        """Verify opencode CLI is available."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [self._opencode_path, "--version"],
                    capture_output=True, text=True, timeout=10,
                ),
            )
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip().split("\n")[0]
                model_short = self._model.split("/")[-1] if "/" in self._model else self._model
                self.duta.name = f"OpenCode v{version} ({model_short})"
                self.connected = True
                logger.info(f"OpenCode CLI connected: v{version}, model: {self._model}")
                return True
            self.connected = False
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"OpenCode CLI connect error: {e}")
            self.connected = False
            return False

    async def chat(self, message: str, system: str | None = None) -> str:
        """Run opencode with a prompt and return the output."""
        self.add_to_history("user", message)

        prompt = message
        if system:
            prompt = f"[Context: {system}]\n\n{message}"

        cmd = [
            self._opencode_path, "run",
            "-m", self._model,
            prompt,
        ]

        t0 = time.monotonic()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True, text=True,
                    timeout=300,  # 5 min max
                    cwd=self.work_dir,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                ),
            )
            self.last_latency = time.monotonic() - t0
            self.request_count += 1

            if result.returncode == 0 or (result.stdout.strip() and result.returncode == 1):
                # opencode may exit 1 even on success (stderr noise)
                reply = result.stdout.strip()
                if not reply and result.stderr.strip():
                    reply = f"(stderr output)\n{result.stderr.strip()[:500]}"
                if not reply:
                    reply = "(OpenCode returned no output)"
                self.add_to_history("assistant", reply)
                self.total_tokens += len(reply) // 4
                return reply
            else:
                error = result.stderr.strip()[:500] or result.stdout.strip()[:500]
                return f"[OpenCode Error (exit {result.returncode})]: {error}"

        except subprocess.TimeoutExpired:
            self.last_latency = time.monotonic() - t0
            return "[OpenCode Error]: Command timed out (5 min limit)"
        except FileNotFoundError:
            return "[OpenCode Error]: opencode command not found. Install: https://opencode.ai"
        except Exception as e:
            self.last_latency = time.monotonic() - t0
            return f"[OpenCode Error]: {e}"


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


def create_agent(provider: str, api_key: str = "", model: str = "", work_dir: str = "") -> LiveAgent | None:
    """Factory to create a live agent for a given provider."""
    if provider == "openai":
        return OpenAIAgent(api_key, model or "gpt-4o")
    elif provider == "anthropic":
        return AnthropicAgent(api_key, model or "claude-sonnet-4-20250514")
    elif provider == "ollama":
        return OllamaAgent(model or "auto")
    elif provider == "gemini":
        return GeminiAgent(api_key, model or "gemini-2.0-flash")
    elif provider == "kimi":
        return KimiCLIAgent(work_dir=work_dir, model=model)
    elif provider == "opencode":
        return OpenCodeCLIAgent(work_dir=work_dir, model=model or "zai-coding-plan/glm-4.7")
    return None


def discover_cli_agents() -> list[tuple[str, str]]:
    """Discover available CLI coding agents on the system.
    Returns list of (provider, path) tuples."""
    agents = []
    # Kimi CLI
    kimi_path = shutil.which("kimi")
    if kimi_path:
        agents.append(("kimi", kimi_path))
    # Claude Code
    claude_path = shutil.which("claude")
    if claude_path:
        agents.append(("claude-code", claude_path))
    # OpenCode
    opencode_path = shutil.which("opencode")
    if opencode_path:
        agents.append(("opencode", opencode_path))
    return agents


async def discover_ollama_models(host: str = "http://localhost:11434") -> list[str]:
    """Discover all chat-capable models available in local Ollama."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{host.rstrip('/')}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                all_models = [m["name"] for m in data.get("models", [])]
                return [m for m in all_models if _is_chat_model(m)]
    except Exception:
        return []
