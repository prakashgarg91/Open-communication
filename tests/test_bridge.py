"""
Tests for the Vākya Bridge — Cross-IDE Communication System
=============================================================
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from vakya.bridge.khoj import (
    Khoj,
    IDEAgent,
    IDEEnvironment,
    IDEType,
)
from vakya.bridge.dwar import (
    TransportType,
    TransportMessage,
    create_dwar,
    WebSocketDwar,
    StdioDwar,
    HttpDwar,
)
from vakya.bridge.setu import Setu, SetuConfig, ConnectedAgent
from vakya.bridge.yojaka import WebSocketYojaka, StdioYojaka, HttpYojaka
from vakya.identity import Duta, DutaRole


# ─── Discovery (Khoj) Tests ──────────────────────────────────────────────────

class TestKhoj:
    """Test the discovery service."""

    def setup_method(self):
        """Create a temporary registry for each test."""
        self.tmp_dir = tempfile.mkdtemp()
        self.registry_path = Path(self.tmp_dir) / "test_registry.json"
        self.khoj = Khoj(registry_path=self.registry_path)

    def test_detect_environment_terminal(self):
        """Test environment detection in a basic terminal."""
        env = self.khoj.detect_environment()
        # In a test environment, should detect terminal or unknown
        assert isinstance(env, IDEEnvironment)
        assert env.ide_type in (IDEType.TERMINAL, IDEType.UNKNOWN, IDEType.VSCODE)

    def test_detect_environment_vscode(self, monkeypatch):
        """Test VS Code environment detection."""
        monkeypatch.setenv("VSCODE_PID", "12345")
        env = self.khoj.detect_environment()
        assert env.ide_type == IDEType.VSCODE
        assert env.ide_name == "Visual Studio Code"
        assert env.pid == 12345

    def test_detect_environment_claude_code(self, monkeypatch):
        """Test Claude Code environment detection."""
        monkeypatch.setenv("CLAUDE_CODE", "true")
        # Clear VS Code vars to avoid conflict
        monkeypatch.delenv("VSCODE_PID", raising=False)
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        env = self.khoj.detect_environment()
        assert env.ide_type == IDEType.CLAUDE_CODE
        assert env.ide_name == "Claude Code"

    def test_detect_environment_opencode(self, monkeypatch):
        """Test OpenCode environment detection."""
        monkeypatch.setenv("OPENCODE", "true")
        monkeypatch.delenv("VSCODE_PID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE", raising=False)
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        env = self.khoj.detect_environment()
        assert env.ide_type == IDEType.OPENCODE
        assert env.ide_name == "OpenCode"

    def test_detect_environment_zed(self, monkeypatch):
        """Test Zed environment detection."""
        monkeypatch.setenv("ZED_TERM", "true")
        monkeypatch.delenv("VSCODE_PID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE", raising=False)
        monkeypatch.delenv("OPENCODE", raising=False)
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        env = self.khoj.detect_environment()
        assert env.ide_type == IDEType.ZED

    def test_register_agent(self):
        """Test agent registration."""
        agent = self.khoj.register_agent(
            duta_id="test-claude",
            duta_name="Claude",
            transport="websocket",
            endpoint="ws://localhost:8765",
            capabilities=["code-gen", "review"],
        )
        assert isinstance(agent, IDEAgent)
        assert agent.duta_id == "test-claude"
        assert agent.duta_name == "Claude"
        assert agent.transport == "websocket"
        assert "code-gen" in agent.capabilities

    def test_discover_agents(self):
        """Test agent discovery."""
        # Register two agents from different IDEs
        self.khoj.register_agent(
            duta_id="vscode-agent",
            duta_name="VS Code Agent",
            environment=IDEEnvironment(ide_type=IDEType.VSCODE, ide_name="VS Code"),
        )
        self.khoj.register_agent(
            duta_id="claude-code-agent",
            duta_name="Claude Code Agent",
            environment=IDEEnvironment(ide_type=IDEType.CLAUDE_CODE, ide_name="Claude Code"),
        )

        agents = self.khoj.discover_agents(active_only=False, max_age_seconds=0)
        assert len(agents) == 2

        names = {a.duta_name for a in agents}
        assert "VS Code Agent" in names
        assert "Claude Code Agent" in names

    def test_discover_agents_filter_by_ide(self):
        """Test filtering discovered agents by IDE type."""
        self.khoj.register_agent(
            duta_id="vs1",
            duta_name="Agent 1",
            environment=IDEEnvironment(ide_type=IDEType.VSCODE, ide_name="VS Code"),
        )
        self.khoj.register_agent(
            duta_id="cc1",
            duta_name="Agent 2",
            environment=IDEEnvironment(ide_type=IDEType.CLAUDE_CODE, ide_name="Claude Code"),
        )

        vs_agents = self.khoj.discover_agents(
            ide_type=IDEType.VSCODE, active_only=False, max_age_seconds=0,
        )
        assert len(vs_agents) == 1
        assert vs_agents[0].duta_id == "vs1"

    def test_unregister_agent(self):
        """Test agent unregistration."""
        agent = self.khoj.register_agent(
            duta_id="temp-agent",
            duta_name="Temp",
        )
        agents = self.khoj.discover_agents(active_only=False, max_age_seconds=0)
        assert len(agents) == 1

        self.khoj.unregister_agent(agent.id)
        agents = self.khoj.discover_agents(active_only=False, max_age_seconds=0)
        assert len(agents) == 0

    def test_register_setu(self):
        """Test Setu daemon registration."""
        self.khoj.register_setu("localhost", 8765)
        setu = self.khoj.find_setu()
        assert setu is not None
        assert setu["host"] == "localhost"
        assert setu["port"] == 8765
        assert setu["url"] == "ws://localhost:8765"

    def test_status(self):
        """Test discovery status report."""
        self.khoj.register_agent(
            duta_id="a1", duta_name="Agent 1",
            environment=IDEEnvironment(ide_type=IDEType.VSCODE, ide_name="VS Code"),
        )
        self.khoj.register_agent(
            duta_id="a2", duta_name="Agent 2",
            environment=IDEEnvironment(ide_type=IDEType.ZED, ide_name="Zed"),
        )

        status = self.khoj.status()
        assert status["total_agents"] >= 2
        assert "VS Code" in status["ide_breakdown"]
        assert "Zed" in status["ide_breakdown"]

    def test_heartbeat(self):
        """Test heartbeat updates."""
        agent = self.khoj.register_agent(
            duta_id="hb-agent",
            duta_name="Heartbeat Agent",
        )
        # Just ensure no errors
        self.khoj.heartbeat(agent.id)


# ─── Transport (Dwār) Tests ──────────────────────────────────────────────────

class TestDwar:
    """Test transport gateways."""

    def test_create_websocket_dwar(self):
        """Test WebSocket gateway creation."""
        dwar = create_dwar(TransportType.WEBSOCKET)
        assert isinstance(dwar, WebSocketDwar)
        assert dwar.transport_type == TransportType.WEBSOCKET
        assert not dwar.is_connected

    def test_create_stdio_dwar(self):
        """Test Stdio gateway creation."""
        dwar = create_dwar(TransportType.STDIO)
        assert isinstance(dwar, StdioDwar)
        assert dwar.transport_type == TransportType.STDIO

    def test_create_http_dwar(self):
        """Test HTTP gateway creation."""
        dwar = create_dwar(TransportType.HTTP)
        assert isinstance(dwar, HttpDwar)
        assert dwar.transport_type == TransportType.HTTP

    def test_unsupported_transport(self):
        """Test that unsupported transport raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported transport"):
            create_dwar(TransportType.PIPE)

    def test_transport_message_model(self):
        """Test TransportMessage creation and serialization."""
        msg = TransportMessage(
            type="vakya",
            payload={"text": "Hello from VS Code!"},
            source="claude-1",
            target="gpt-1",
        )
        assert msg.type == "vakya"
        assert msg.source == "claude-1"

        # Serialization
        data = json.loads(msg.model_dump_json())
        assert data["type"] == "vakya"
        assert data["payload"]["text"] == "Hello from VS Code!"

    def test_on_message_callback(self):
        """Test registering a message callback."""
        dwar = create_dwar(TransportType.WEBSOCKET)
        received = []
        dwar.on_message(lambda msg: received.append(msg))
        assert len(dwar._callbacks) == 1


# ─── Setu Configuration Tests ────────────────────────────────────────────────

class TestSetuConfig:
    """Test Setu bridge configuration."""

    def test_default_config(self):
        """Test default Setu configuration."""
        config = SetuConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.enable_discovery is True

    def test_custom_config(self):
        """Test custom Setu configuration."""
        config = SetuConfig(
            host="127.0.0.1",
            port=9000,
            name="Test Bridge",
            enable_discovery=False,
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.name == "Test Bridge"
        assert config.enable_discovery is False

    def test_setu_creation(self):
        """Test Setu instance creation."""
        setu = Setu()
        assert setu.agent_count == 0
        assert setu.ide_summary == {}

    def test_setu_status(self):
        """Test Setu status report."""
        setu = Setu()
        status = setu.status()
        assert status["agents_connected"] == 0
        assert status["observers_connected"] == 0
        assert "protocol_version" in status


# ─── Yojaka (Connector) Tests ────────────────────────────────────────────────

class TestYojaka:
    """Test IDE connectors."""

    def test_websocket_yojaka_creation(self):
        """Test WebSocket connector creation."""
        duta = Duta(name="Claude", model="claude-sonnet-4-20250514", provider="anthropic")
        yojaka = WebSocketYojaka(duta)
        assert yojaka.transport_type == TransportType.WEBSOCKET
        assert yojaka.setu_url == "ws://localhost:8765"
        assert not yojaka.is_connected

    def test_stdio_yojaka_creation(self):
        """Test Stdio connector creation."""
        duta = Duta(name="GPT", model="gpt-4o", provider="openai")
        yojaka = StdioYojaka(duta)
        assert yojaka.transport_type == TransportType.STDIO

    def test_http_yojaka_creation(self):
        """Test HTTP connector creation."""
        duta = Duta(name="GLM", model="glm-4", provider="zhipu")
        yojaka = HttpYojaka(duta)
        assert yojaka.transport_type == TransportType.HTTP
        assert yojaka.setu_url == "http://localhost:8000"

    def test_yojaka_callback_registration(self):
        """Test registering a Vakya callback."""
        duta = Duta(name="Test", model="test", provider="test")
        yojaka = WebSocketYojaka(duta)

        received = []
        yojaka.on_vakya(lambda msg: received.append(msg))
        assert len(yojaka._callbacks) == 1


# ─── IDE Agent Model Tests ───────────────────────────────────────────────────

class TestIDEAgent:
    """Test IDE agent data models."""

    def test_ide_environment(self):
        """Test IDE environment creation."""
        env = IDEEnvironment(
            ide_type=IDEType.VSCODE,
            ide_name="Visual Studio Code",
            workspace="/home/user/project",
        )
        assert env.ide_type == IDEType.VSCODE
        assert env.workspace == "/home/user/project"

    def test_ide_agent(self):
        """Test IDE agent creation."""
        agent = IDEAgent(
            duta_id="claude-1",
            duta_name="Claude",
            environment=IDEEnvironment(ide_type=IDEType.VSCODE, ide_name="VS Code"),
            transport="websocket",
            capabilities=["code-gen", "review"],
        )
        assert agent.duta_id == "claude-1"
        assert agent.active is True
        assert len(agent.capabilities) == 2

    def test_ide_agent_serialization(self):
        """Test IDE agent serialization roundtrip."""
        agent = IDEAgent(
            duta_id="test-agent",
            duta_name="Test",
            environment=IDEEnvironment(ide_type=IDEType.CLAUDE_CODE, ide_name="Claude Code"),
        )
        data = json.loads(agent.model_dump_json())
        restored = IDEAgent.model_validate(data)
        assert restored.duta_id == "test-agent"
        assert restored.environment.ide_type == IDEType.CLAUDE_CODE

    def test_all_ide_types(self):
        """Test all IDE types are valid."""
        expected = {
            "vscode", "claude-code", "opencode", "zed", "cursor",
            "windsurf", "neovim", "jetbrains", "terminal", "unknown",
        }
        actual = {t.value for t in IDEType}
        assert actual == expected


# ─── Connected Agent Tests ────────────────────────────────────────────────────

class TestConnectedAgent:
    """Test the ConnectedAgent tracking class."""

    def test_connected_agent_creation(self):
        """Test creating a ConnectedAgent."""
        duta = Duta(name="Test", model="test", provider="test")
        # We can't create a real ServerConnection in tests, so just test the model
        env = IDEEnvironment(ide_type=IDEType.VSCODE, ide_name="VS Code")
        # Just verify our data models work
        assert duta.name == "Test"
        assert env.ide_type == IDEType.VSCODE
