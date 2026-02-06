"""
Khoj — IDE Discovery Service
==============================

खोज (Khoj) = Search / Discovery

The discovery service automatically detects which IDE environments
are running on the machine and manages the registry of connected
AI agents across all IDEs.

Discovery Methods:
    1. Registry File — A shared JSON file at ~/.vakya/registry.json
    2. Well-known Port — Setu daemon listens on port 8765
    3. Process Scan — Detect running IDE processes
    4. Environment Variables — IDE-specific env vars
"""

from __future__ import annotations

import json
import os
import platform
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("vakya.bridge.khoj")


# ─── IDE Environment Definitions ─────────────────────────────────────────────

class IDEType(str, Enum):
    """Known IDE types that can host AI agents."""

    VSCODE = "vscode"            # Visual Studio Code
    CLAUDE_CODE = "claude-code"  # Claude Code (Anthropic)
    OPENCODE = "opencode"        # OpenCode
    ZED = "zed"                  # Zed Editor
    CURSOR = "cursor"            # Cursor IDE
    WINDSURF = "windsurf"        # Windsurf / Codeium
    NEOVIM = "neovim"            # Neovim with AI plugins
    JETBRAINS = "jetbrains"      # JetBrains IDEs
    TERMINAL = "terminal"        # Raw terminal / CLI
    UNKNOWN = "unknown"          # Unknown environment


class IDEEnvironment(BaseModel):
    """
    Describes an IDE environment hosting an AI agent.

    Detected automatically or specified manually.
    """

    ide_type: IDEType = Field(default=IDEType.UNKNOWN, description="IDE type")
    ide_name: str = Field(default="Unknown", description="Human-readable IDE name")
    ide_version: str | None = Field(default=None, description="IDE version")
    pid: int | None = Field(default=None, description="Process ID of the IDE")
    workspace: str | None = Field(default=None, description="Current workspace/project path")
    extensions: list[str] = Field(default_factory=list, description="Relevant extensions")
    meta: dict[str, Any] = Field(default_factory=dict, description="IDE-specific metadata")


class IDEAgent(BaseModel):
    """
    An AI agent registered from a specific IDE environment.

    Combines the agent's identity with its IDE context.
    """

    id: str = Field(
        default_factory=lambda: f"ide-agent-{uuid.uuid4().hex[:8]}",
        description="Unique agent registration ID",
    )
    duta_id: str = Field(description="The Dūta ID of the AI agent")
    duta_name: str = Field(default="", description="Display name of the Dūta")
    environment: IDEEnvironment = Field(
        default_factory=IDEEnvironment,
        description="IDE environment info",
    )
    transport: str = Field(default="websocket", description="Connection transport type")
    endpoint: str = Field(default="", description="Connection endpoint (URL, pipe name, etc.)")
    registered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    last_heartbeat: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    active: bool = Field(default=True, description="Whether the agent is currently active")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Agent capabilities (e.g., 'code-generation', 'review')",
    )


# ─── Registry File Management ────────────────────────────────────────────────

def _get_registry_dir() -> Path:
    """Get the Vākya configuration directory."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vakya"


def _get_registry_path() -> Path:
    """Get the path to the agent registry file."""
    return _get_registry_dir() / "registry.json"


def _get_lock_path() -> Path:
    """Get the path to the registry lock file."""
    return _get_registry_dir() / "registry.lock"


class Khoj:
    """
    खोज (Khoj) = Discovery Service

    Manages discovery and registration of AI agents across IDE environments.
    Uses a shared registry file and environment detection to maintain
    awareness of all active AI agents on the machine.

    Usage:
        khoj = Khoj()

        # Detect current IDE
        env = khoj.detect_environment()
        print(f"Running in: {env.ide_name}")

        # Register this agent
        agent = khoj.register_agent(
            duta_id="claude-1",
            duta_name="Claude",
            transport="websocket",
            endpoint="ws://localhost:8765",
        )

        # Find other agents
        others = khoj.discover_agents()
        for other in others:
            print(f"Found: {other.duta_name} in {other.environment.ide_name}")
    """

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or _get_registry_path()
        self._lock_path = self.registry_path.parent / "registry.lock"
        self._ensure_registry_dir()

    def _ensure_registry_dir(self) -> None:
        """Create the registry directory if it doesn't exist."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    # ─── Environment Detection ───────────────────────────────────────────

    def detect_environment(self) -> IDEEnvironment:
        """
        Auto-detect the current IDE environment.

        Checks environment variables, process info, and other signals
        to determine which IDE/container we're running inside.
        """
        # Check for VS Code
        if os.environ.get("VSCODE_PID") or os.environ.get("TERM_PROGRAM") == "vscode":
            return IDEEnvironment(
                ide_type=IDEType.VSCODE,
                ide_name="Visual Studio Code",
                ide_version=os.environ.get("VSCODE_VERSION"),
                pid=int(os.environ["VSCODE_PID"]) if os.environ.get("VSCODE_PID") else None,
                workspace=os.environ.get("VSCODE_WORKSPACE_FOLDER"),
            )

        # Check for Cursor (VS Code fork)
        if os.environ.get("CURSOR_PID") or "cursor" in os.environ.get("TERM_PROGRAM", "").lower():
            return IDEEnvironment(
                ide_type=IDEType.CURSOR,
                ide_name="Cursor",
                pid=int(os.environ["CURSOR_PID"]) if os.environ.get("CURSOR_PID") else None,
                workspace=os.environ.get("VSCODE_WORKSPACE_FOLDER"),
            )

        # Check for Windsurf
        if os.environ.get("WINDSURF_PID") or "windsurf" in os.environ.get("TERM_PROGRAM", "").lower():
            return IDEEnvironment(
                ide_type=IDEType.WINDSURF,
                ide_name="Windsurf",
                pid=int(os.environ["WINDSURF_PID"]) if os.environ.get("WINDSURF_PID") else None,
            )

        # Check for Claude Code (Anthropic's CLI tool)
        if os.environ.get("CLAUDE_CODE") or os.environ.get("ANTHROPIC_AGENT"):
            return IDEEnvironment(
                ide_type=IDEType.CLAUDE_CODE,
                ide_name="Claude Code",
                ide_version=os.environ.get("CLAUDE_CODE_VERSION"),
            )

        # Check for OpenCode
        if os.environ.get("OPENCODE") or os.environ.get("OPENCODE_PID"):
            return IDEEnvironment(
                ide_type=IDEType.OPENCODE,
                ide_name="OpenCode",
                ide_version=os.environ.get("OPENCODE_VERSION"),
            )

        # Check for Zed
        if os.environ.get("ZED_TERM") or "zed" in os.environ.get("TERM_PROGRAM", "").lower():
            return IDEEnvironment(
                ide_type=IDEType.ZED,
                ide_name="Zed",
                pid=int(os.environ["ZED_PID"]) if os.environ.get("ZED_PID") else None,
            )

        # Check for Neovim
        if os.environ.get("NVIM") or os.environ.get("NVIM_LISTEN_ADDRESS"):
            return IDEEnvironment(
                ide_type=IDEType.NEOVIM,
                ide_name="Neovim",
            )

        # Check for JetBrains
        if os.environ.get("JETBRAINS_IDE") or os.environ.get("IDEA_INITIAL_DIRECTORY"):
            return IDEEnvironment(
                ide_type=IDEType.JETBRAINS,
                ide_name=os.environ.get("JETBRAINS_IDE", "JetBrains IDE"),
            )

        # Check if we're in a basic terminal
        if os.environ.get("TERM") or os.environ.get("SHELL") or os.environ.get("COMSPEC"):
            return IDEEnvironment(
                ide_type=IDEType.TERMINAL,
                ide_name="Terminal",
            )

        return IDEEnvironment()

    # ─── Agent Registry ──────────────────────────────────────────────────

    def _read_registry(self) -> dict[str, Any]:
        """Read the current registry file."""
        if not self.registry_path.exists():
            return {"agents": {}, "setu": None, "updated": None}
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"agents": {}, "setu": None, "updated": None}

    def _write_registry(self, data: dict[str, Any]) -> None:
        """Write to the registry file (with simple file-based locking)."""
        data["updated"] = datetime.now(timezone.utc).isoformat()
        lock_path = self._lock_path

        # Ensure parent directory exists
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Simple spinlock (adequate for local single-machine use)
        retries = 10
        while lock_path.exists() and retries > 0:
            time.sleep(0.1)
            retries -= 1

        try:
            lock_path.write_text(str(os.getpid()), encoding="utf-8")
            self.registry_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def register_agent(
        self,
        duta_id: str,
        duta_name: str = "",
        transport: str = "websocket",
        endpoint: str = "",
        capabilities: list[str] | None = None,
        environment: IDEEnvironment | None = None,
    ) -> IDEAgent:
        """
        Register an AI agent from the current IDE environment.

        Args:
            duta_id: The Dūta ID of the agent
            duta_name: Display name
            transport: Connection type (websocket, stdio, http)
            endpoint: Connection endpoint
            capabilities: Agent capabilities
            environment: IDE environment (auto-detected if None)

        Returns:
            The registered IDEAgent
        """
        env = environment or self.detect_environment()
        agent = IDEAgent(
            duta_id=duta_id,
            duta_name=duta_name,
            environment=env,
            transport=transport,
            endpoint=endpoint,
            capabilities=capabilities or [],
        )

        registry = self._read_registry()
        registry["agents"][agent.id] = json.loads(agent.model_dump_json())
        self._write_registry(registry)

        logger.info(
            f"खोज: Agent registered: {duta_name} ({duta_id}) "
            f"from {env.ide_name} via {transport}"
        )
        return agent

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the registry."""
        registry = self._read_registry()
        if agent_id in registry["agents"]:
            agent_data = registry["agents"].pop(agent_id)
            self._write_registry(registry)
            logger.info(f"खोज: Agent unregistered: {agent_data.get('duta_name', agent_id)}")

    def heartbeat(self, agent_id: str) -> None:
        """Update the heartbeat timestamp for an agent."""
        registry = self._read_registry()
        if agent_id in registry["agents"]:
            registry["agents"][agent_id]["last_heartbeat"] = (
                datetime.now(timezone.utc).isoformat()
            )
            self._write_registry(registry)

    def discover_agents(
        self,
        ide_type: IDEType | None = None,
        active_only: bool = True,
        max_age_seconds: int = 300,
    ) -> list[IDEAgent]:
        """
        Discover all registered AI agents.

        Args:
            ide_type: Filter by IDE type (None for all)
            active_only: Only return active agents
            max_age_seconds: Consider agents inactive if no heartbeat within this period

        Returns:
            List of discovered IDEAgent instances
        """
        registry = self._read_registry()
        agents: list[IDEAgent] = []
        now = datetime.now(timezone.utc)

        for agent_data in registry.get("agents", {}).values():
            try:
                agent = IDEAgent.model_validate(agent_data)

                # Check staleness
                if max_age_seconds > 0:
                    last_hb = datetime.fromisoformat(agent.last_heartbeat)
                    if last_hb.tzinfo is None:
                        last_hb = last_hb.replace(tzinfo=timezone.utc)
                    age = (now - last_hb).total_seconds()
                    if age > max_age_seconds:
                        agent.active = False

                # Apply filters
                if active_only and not agent.active:
                    continue
                if ide_type and agent.environment.ide_type != ide_type:
                    continue

                agents.append(agent)
            except Exception as e:
                logger.warning(f"खोज: Could not parse agent registry entry: {e}")

        return agents

    def register_setu(self, host: str, port: int) -> None:
        """Register the Setu daemon's address in the registry."""
        registry = self._read_registry()
        registry["setu"] = {
            "host": host,
            "port": port,
            "url": f"ws://{host}:{port}",
            "started": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
        }
        self._write_registry(registry)
        logger.info(f"खोज: Setu registered at ws://{host}:{port}")

    def find_setu(self) -> dict[str, Any] | None:
        """Find the running Setu daemon from the registry."""
        registry = self._read_registry()
        return registry.get("setu")

    def cleanup_stale(self, max_age_seconds: int = 300) -> int:
        """Remove stale agents from the registry. Returns count removed."""
        registry = self._read_registry()
        now = datetime.now(timezone.utc)
        to_remove = []

        for agent_id, agent_data in registry.get("agents", {}).items():
            try:
                last_hb = datetime.fromisoformat(agent_data.get("last_heartbeat", ""))
                if last_hb.tzinfo is None:
                    last_hb = last_hb.replace(tzinfo=timezone.utc)
                age = (now - last_hb).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(agent_id)
            except (ValueError, KeyError):
                to_remove.append(agent_id)

        for agent_id in to_remove:
            registry["agents"].pop(agent_id, None)

        if to_remove:
            self._write_registry(registry)
            logger.info(f"खोज: Cleaned up {len(to_remove)} stale agents")

        return len(to_remove)

    def status(self) -> dict[str, Any]:
        """Get a summary of the current discovery state."""
        agents = self.discover_agents(active_only=False, max_age_seconds=0)
        active = [a for a in agents if a.active]
        setu = self.find_setu()

        ide_counts: dict[str, int] = {}
        for a in active:
            ide_name = a.environment.ide_name
            ide_counts[ide_name] = ide_counts.get(ide_name, 0) + 1

        return {
            "total_agents": len(agents),
            "active_agents": len(active),
            "setu_running": setu is not None,
            "setu_url": setu.get("url") if setu else None,
            "ide_breakdown": ide_counts,
            "registry_path": str(self.registry_path),
        }
