# 🌉 Cross-IDE Bridge — Setu (सेतु)

## Vision

> **AI agents should communicate freely, regardless of which IDE they run in.**

Today's AI coding assistants are trapped inside their IDE containers. Claude in VS Code can't talk to GPT in OpenCode. An agent in Zed can't coordinate with one in Claude Code. Each IDE is an isolated island.

**Vākya's Setu (Bridge) tears down these walls.**

```
     VS Code ←──┐
                 │
  Claude Code ←──┼──→  Setu (सेतु)  ←──→  Any AI speaks to Any AI
                 │      Bridge Daemon
    OpenCode ←──┤
                 │
    Zed Code ←──┘
```

## Architecture

### Components (Sanskrit-Named)

| Component | Sanskrit | Meaning | Purpose |
|-----------|----------|---------|---------|
| **Setu** | सेतु | Bridge | Central daemon connecting all IDEs |
| **Khoj** | खोज | Discovery | Finds agents across IDE environments |
| **Yojaka** | योजक | Connector | IDE-specific connection adapter |
| **Dwār** | द्वार | Gateway | Transport protocol handler |

### How It Works

1. **Start the Setu daemon** — It listens on a well-known local port (default: 8765)
2. **Each IDE's AI registers** — When an AI agent starts in any IDE, its Yojaka (connector) registers with Setu
3. **Khoj discovers peers** — The discovery service maintains a shared registry of all active agents
4. **Messages flow freely** — Any agent can send a Vākya message to any other agent, regardless of IDE
5. **Humans observe everything** — Human observers can watch all cross-IDE communication in real-time

## Quick Start

### 1. Start the Bridge

```bash
# Terminal 1: Start the Setu bridge daemon
vakya-bridge --verbose
```

### 2. Connect from VS Code

```python
from vakya import Duta, DutaRole, WebSocketYojaka

# Create your AI agent identity
agent = Duta(
    name="Claude",
    model="claude-sonnet-4-20250514",
    provider="anthropic",
    role=DutaRole.NETA,
    skills=["code-generation", "review"],
)

# Connect to the bridge via WebSocket
connector = WebSocketYojaka(agent, setu_url="ws://localhost:8765")
ide_agent = await connector.connect()
print(f"Connected from {ide_agent.environment.ide_name}")
```

### 3. Connect from Claude Code / OpenCode (stdio-based)

```python
from vakya import Duta, DutaRole, StdioYojaka

agent = Duta(
    name="GPT-4o",
    model="gpt-4o",
    provider="openai",
    role=DutaRole.KARTR,
)

# Connect via stdio (newline-delimited JSON)
connector = StdioYojaka(agent)
ide_agent = await connector.connect()
```

### 4. Discover and Communicate

```python
# Find all other agents across IDEs
peers = await connector.discover_peers()
for peer in peers:
    print(f"  {peer.duta_name} in {peer.environment.ide_name}")

# Send a message to an agent in another IDE
from vakya import Prasna
msg = Prasna(
    presaka=agent.id,
    prapaka=peers[0].duta_id,
    text="Can you review the changes I just made?",
)
await connector.send_vakya(msg)

# Listen for incoming messages
connector.on_vakya(lambda vakya: print(f"Received: {vakya}"))
```

## IDE Detection

The Khoj (discovery) service automatically detects which IDE environment the agent is running in:

| IDE | Detection Method |
|-----|------------------|
| **VS Code** | `VSCODE_PID` env var, `TERM_PROGRAM=vscode` |
| **Cursor** | `CURSOR_PID` env var |
| **Claude Code** | `CLAUDE_CODE` env var |
| **OpenCode** | `OPENCODE` env var |
| **Zed** | `ZED_TERM` env var |
| **Windsurf** | `WINDSURF_PID` env var |
| **Neovim** | `NVIM` env var, `NVIM_LISTEN_ADDRESS` |
| **JetBrains** | `JETBRAINS_IDE` env var |
| **Terminal** | `TERM` / `SHELL` / `COMSPEC` |

```python
from vakya.bridge import Khoj

khoj = Khoj()
env = khoj.detect_environment()
print(f"Running in: {env.ide_name} ({env.ide_type.value})")
```

## Transport Protocols

Different IDEs may support different connection methods:

### WebSocket (Primary)
- **Best for:** VS Code, Cursor, Windsurf, Zed
- **How:** Persistent bidirectional connection
- **Connector:** `WebSocketYojaka`

### Stdio (NDJSON)
- **Best for:** Claude Code, OpenCode, terminal-based tools
- **How:** Newline-delimited JSON over stdin/stdout
- **Connector:** `StdioYojaka`

### HTTP (Polling)
- **Best for:** JetBrains, simple integrations
- **How:** Periodic HTTP requests
- **Connector:** `HttpYojaka`

## Shared Registry

Agents are tracked in a shared registry file:
- **Windows:** `%APPDATA%/vakya/registry.json`
- **macOS/Linux:** `~/.config/vakya/registry.json`

This enables agents to discover each other even before connecting to Setu.

## Sanskrit Glossary (Bridge Terms)

| Term | Sanskrit | Meaning |
|------|----------|---------|
| Setu | सेतु | Bridge — the central daemon |
| Khoj | खोज | Search/Discovery — finding agents |
| Yojaka | योजक | Connector — IDE-to-bridge adapter |
| Dwār | द्वार | Gate/Door — transport protocol handler |

## Real-World Scenario

Imagine a development team where each developer uses a different IDE with a different AI assistant:

1. **Alice** uses **VS Code + Copilot** (Claude-backed)
2. **Bob** uses **Claude Code** in his terminal
3. **Charlie** uses **Zed** with a local LLaMA model
4. **Diana** uses **OpenCode** with GPT-4o

With Vākya Setu, all four AI assistants can:
- **Share context** about the codebase
- **Distribute tasks** (Alice's AI assigns code review to Bob's AI)
- **Collaborate on complex tasks** (all four AIs discuss architecture)
- **Report progress** across IDE boundaries
- **Resolve conflicts** when AIs disagree

All while the developers can observe the entire cross-IDE AI conversation through the human monitoring viewer.

---

*सेतु — Where boundaries between IDEs dissolve, and AI collaboration becomes truly universal.*
