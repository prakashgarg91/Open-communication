"""
Vākya Bridge — Cross-IDE AI Communication
===========================================

सेतु (Setu) = Bridge

The bridge system enables AI agents running in different IDE containers
(VS Code, Claude Code, OpenCode, Zed Code, Cursor, etc.) to discover
each other and communicate seamlessly through the Vākya protocol.

Architecture:
    Setu     (सेतु)  — Central bridge daemon connecting all IDEs
    Khoj     (खोज)   — Local discovery service for finding IDE agents
    Yojaka   (योजक)  — IDE-specific connection adapters
    Dwār     (द्वार) — Gateway / transport manager

How it works:
    1. A Setu daemon runs on the local machine (port 8765 by default)
    2. Each IDE's AI agent connects to Setu via its Yojaka (connector)
    3. Khoj handles discovery — agents can find each other automatically
    4. Messages flow through Setu using the standard Vākya protocol
    5. Humans can observe all cross-IDE communication

Supported IDE Environments:
    - VS Code (via WebSocket extension)
    - Claude Code (via stdio bridge)
    - OpenCode (via stdio bridge)
    - Zed Code (via stdio bridge)
    - Cursor (via WebSocket extension)
    - Any terminal-based AI tool
    - Any WebSocket-capable environment
"""

from vakya.bridge.setu import Setu, SetuConfig
from vakya.bridge.khoj import Khoj, IDEEnvironment, IDEAgent
from vakya.bridge.yojaka import (
    BaseYojaka,
    WebSocketYojaka,
    StdioYojaka,
    HttpYojaka,
)
from vakya.bridge.dwar import Dwar, TransportType

__all__ = [
    # Bridge daemon
    "Setu",
    "SetuConfig",
    # Discovery
    "Khoj",
    "IDEEnvironment",
    "IDEAgent",
    # Connectors
    "BaseYojaka",
    "WebSocketYojaka",
    "StdioYojaka",
    "HttpYojaka",
    # Gateway
    "Dwar",
    "TransportType",
]
