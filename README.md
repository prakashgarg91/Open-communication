<h1 align="center">
  वाक्य — Vākya<br>
  <sub>Open Protocol for AI-to-AI Communication</sub>
</h1>

<p align="center">
  <em>Let every AI speak to every other AI — freely, clearly, and openly.</em>
</p>

<p align="center">
  <a href="https://github.com/prakashgarg91/Open-communication/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python 3.10+"></a>
  <a href="https://github.com/prakashgarg91/Open-communication/actions"><img src="https://img.shields.io/badge/CI-passing-brightgreen.svg" alt="CI"></a>
  <a href="#-support--donate"><img src="https://img.shields.io/badge/sponsor-❤-red.svg" alt="Sponsor"></a>
</p>

---

## 🌏 What is Vākya?

**Vākya** (वाक्य — Sanskrit for *"expression"*) is an open, JSON-based protocol that enables **any AI/LLM to communicate with any other AI** — Claude, GPT, GLM, Gemini, LLaMA, Mistral, or any future model.

Think of it as **HTTP for AI-to-AI communication**: a universal language that every model can speak.

### 🌉 Cross-IDE Vision — AI Without Boundaries

**Vākya breaks the walls between IDEs.** An AI agent in VS Code can talk to an AI in Claude Code, which can collaborate with an AI in Zed, which can coordinate with an agent in OpenCode — all in real-time, using one protocol.

```
┌──────────────┐      ┌───────────────┐      ┌──────────────┐
│   VS Code    │      │               │      │  Claude Code │
│  (Copilot)   │─────▶│    Vākya      │◀─────│   (Claude)   │
│              │◀─────│    Setu       │─────▶│              │
└──────────────┘      │   (सेतु)      │      └──────────────┘
                      │   Bridge      │
┌──────────────┐      │   Daemon      │      ┌──────────────┐
│   OpenCode   │─────▶│               │◀─────│     Zed      │
│   (Agent)    │◀─────│               │─────▶│   (Agent)    │
└──────────────┘      │               │      └──────────────┘
                      │               │
┌──────────────┐      │               │      ┌──────────────┐
│   Cursor     │─────▶│               │◀─────│   Neovim     │
│   (AI)       │◀─────│               │─────▶│   (Copilot)  │
└──────────────┘      └───────┬───────┘      └──────────────┘
                              │
                         👁 Human
                         Observer
```

**No IDE lock-in. No boundaries. Just AI collaborating freely.**

### Why Vākya?

| Problem | Vākya Solution |
|---------|---------------|
| AIs can't talk to each other | Universal JSON message format any model understands |
| No standard for multi-AI collaboration | Built-in task distribution, roles, and coordination |
| Human oversight is hard | Real-time human observation of all AI communications |
| Vendor lock-in | Provider-agnostic — works with any model from any company |
| Complex binary protocols | Simple, readable JSON with Sanskrit-inspired naming |

### Why Sanskrit?

Sanskrit (संस्कृत) is the perfect language for this protocol:
- **🌍 Neutral** — belongs to no single modern nation, a shared human heritage
- **📐 Precise** — extraordinarily precise grammatical terminology
- **🤖 AI-friendly** — short, unambiguous terms that tokenize efficiently
- **🌳 Universal** — Sanskrit roots appear across Indo-European languages
- **✨ Beautiful** — makes the protocol meaningful and elegant

---

## 🚀 Quick Start

### Install

```bash
pip install vakya

# With AI provider support
pip install vakya[openai]       # GPT models
pip install vakya[anthropic]    # Claude models
pip install vakya[all]          # Everything
```

### Hello, Vākya!

```python
from vakya import Prasna, Uttara, VakyaProtocol

# Claude asks GPT a question
question = Prasna(
    presaka="claude-1",     # Sender (प्रेषक)
    prapaka="gpt-1",        # Receiver (प्रापक)
    text="What's the best way to implement a transformer from scratch?",
    visaya="deep-learning",  # Topic (विषय)
)

# GPT responds
answer = Uttara(
    presaka="gpt-1",
    text="Start with self-attention, then add layer norm and feed-forward...",
    reply_to=question,
)

# See the wire format
protocol = VakyaProtocol()
print(protocol.encode(question))
```

**Output:**
```json
{
  "vakya": "1.0",
  "pramana": "sha256:a1b2c3...",
  "sandesa": {
    "id": "msg-550e8400-...",
    "presaka": "claude-1",
    "prapaka": "gpt-1",
    "samaya": "2026-02-06T12:00:00Z",
    "prakara": "prasna",
    "visaya": "deep-learning",
    "sarira": {
      "text": "What's the best way to implement a transformer from scratch?"
    }
  }
}
```

### Multi-AI Collaboration

```python
import asyncio
from vakya import Duta, DutaRole, SabhaRouter, Prasna, Uttara, KaryaManager

async def main():
    # Create AI team
    claude = Duta(id="claude", name="Claude", model="claude-opus-4.6",
                  provider="anthropic", role=DutaRole.NETA,  # Leader
                  skills=["architecture", "code-generation"])

    gpt = Duta(id="gpt", name="GPT-4o", model="gpt-4o",
               provider="openai", role=DutaRole.KARTR,  # Worker
               skills=["code-generation", "testing"])

    # Set up assembly
    router = SabhaRouter(name="Project Team")
    router.register_duta(claude)
    router.register_duta(gpt)

    # Human watches everything
    router.add_observer(lambda msg, ch: print(f"👁 {msg}"))

    # Claude asks GPT to work on something
    msg = Prasna(presaka="claude", prapaka="gpt",
                 text="Can you write unit tests for the auth module?")
    await router.route(msg)

asyncio.run(main())
```

---

## 📦 Architecture

```
vakya/
├── protocol.py          # Wire format, encoding, validation
├── message.py           # Message types (Vākya, Praśna, Uttara, Kārya...)
├── identity.py          # Dūta (AI agent) identity system
├── channel.py           # Sūtra (communication channels)
├── router.py            # Sabhā (assembly) message routing
├── task.py              # Kārya (task) distribution & tracking
├── bridge/              # 🌉 Cross-IDE communication
│   ├── setu.py          # Setu (bridge) daemon — connects all IDEs
│   ├── khoj.py          # Khoj (discovery) — finds agents across IDEs
│   ├── yojaka.py        # Yojaka (connectors) — IDE-specific adapters
│   └── dwar.py          # Dwār (gateway) — transport protocols
├── adapters/            # AI model connectors
│   ├── openai_adapter.py    # GPT, o1, o3
│   ├── anthropic_adapter.py # Claude
│   ├── glm_adapter.py       # GLM-4 (Zhipu)
│   └── ollama_adapter.py    # Local models (LLaMA, Mistral, etc.)
├── server/
│   ├── relay.py         # WebSocket relay server
│   └── web.py           # REST API (FastAPI)
└── monitor/
    └── viewer.py        # Rich terminal viewer for humans
```

## 🔤 Protocol at a Glance

### Message Types (प्रकार)

| Type | Sanskrit | Icon | Purpose |
|------|----------|------|---------|
| `vakya` | वाक्य | 💬 | General statement |
| `prasna` | प्रश्न | ❓ | Question |
| `uttara` | उत्तर | ✅ | Answer |
| `karya` | कार्य | 📋 | Task assignment |
| `prativedana` | प्रतिवेदन | 📊 | Progress report |
| `svikriti` | स्वीकृति | 👍 | Acknowledgment |
| `nirnaya` | निर्णय | ⚖️ | Decision |
| `vivada` | विवाद | ⚡ | Disagreement |

### Roles (भूमिका)

| Role | Sanskrit | Meaning |
|------|----------|---------|
| `neta` | नेता | Leader — coordinates the team |
| `kartr` | कर्तृ | Worker — executes tasks |
| `samikshaka` | समीक्षक | Reviewer — reviews work |
| `pariksaka` | परीक्षक | Tester — validates results |
| `mantri` | मन्त्री | Advisor — provides guidance |

---

## 🖥️ Run the Server

```bash
# Start relay server
vakya-server --port 8765 --verbose

# Start human viewer (separate terminal)
vakya-monitor --server ws://localhost:8765
```

Or with the REST API:
```python
from vakya.server import create_app
import uvicorn

app = create_app()
uvicorn.run(app, host="0.0.0.0", port=8000)
# Visit http://localhost:8000/docs for Swagger UI
```

---

## 🌉 Cross-IDE Bridge (Setu)

The **Setu** (सेतु = Bridge) daemon connects AI agents across any IDE.

```bash
# Start the cross-IDE bridge
vakya-bridge --verbose
```

Now AI agents from any IDE can connect:

```python
from vakya import Duta, DutaRole, WebSocketYojaka, Prasna

# An AI agent in VS Code
agent = Duta(name="Claude", model="claude-sonnet-4-20250514",
             provider="anthropic", role=DutaRole.NETA)

# Connect to the bridge
connector = WebSocketYojaka(agent, setu_url="ws://localhost:8765")
ide_agent = await connector.connect()

# Discover other AI agents in other IDEs
peers = await connector.discover_peers()
for peer in peers:
    print(f"Found {peer.duta_name} in {peer.environment.ide_name}")

# Send a message to an agent in a different IDE
msg = Prasna(presaka=agent.id, prapaka="opencode-gpt",
             text="Can you review the auth module?")
await connector.send_vakya(msg)
```

### Supported IDEs

| IDE | Transport | Connector |
|-----|-----------|-----------|
| **VS Code** | WebSocket | `WebSocketYojaka` |
| **Claude Code** | Stdio (NDJSON) | `StdioYojaka` |
| **OpenCode** | Stdio (NDJSON) | `StdioYojaka` |
| **Zed** | WebSocket | `WebSocketYojaka` |
| **Cursor** | WebSocket | `WebSocketYojaka` |
| **Windsurf** | WebSocket | `WebSocketYojaka` |
| **Neovim** | Stdio / WebSocket | `StdioYojaka` / `WebSocketYojaka` |
| **JetBrains** | HTTP | `HttpYojaka` |
| **Terminal** | Stdio | `StdioYojaka` |

### How Discovery Works

```python
from vakya.bridge import Khoj

khoj = Khoj()

# Auto-detect which IDE you're in
env = khoj.detect_environment()
print(f"I'm running in: {env.ide_name}")

# Find all agents across all IDEs
agents = khoj.discover_agents()
for agent in agents:
    print(f"{agent.duta_name} → {agent.environment.ide_name} via {agent.transport}")
```

---

## 🔌 Supported AI Models

| Provider | Models | Adapter |
|----------|--------|---------|
| **Anthropic** | Claude Opus, Sonnet, Haiku | `AnthropicAdapter` |
| **OpenAI** | GPT-4o, o1, o3, GPT-4 | `OpenAIAdapter` |
| **Zhipu AI** | GLM-4, GLM-4V | `GLMAdapter` |
| **Ollama** | LLaMA, Mistral, Phi, Gemma... | `OllamaAdapter` |
| *Your model* | *Any OpenAI-compatible API* | *Extend `BaseAdapter`* |

---

## 🧪 Examples

| Example | Description |
|---------|-------------|
| [`simple_chat.py`](examples/simple_chat.py) | Two AIs having a conversation |
| [`task_distribution.py`](examples/task_distribution.py) | Distributing tasks across a team |
| [`multi_model_collab.py`](examples/multi_model_collab.py) | Full project collaboration |
| [`cross_ide_bridge.py`](examples/cross_ide_bridge.py) | 🌉 Cross-IDE AI communication |

---

## 📖 Documentation

- [**Protocol Specification**](docs/protocol-spec.md) — Full technical spec
- [**Cross-IDE Bridge**](docs/cross-ide-bridge.md) — 🌉 How AI agents communicate across IDEs
- [**Getting Started**](docs/getting-started.md) — Tutorial with examples
- [**Sanskrit Glossary**](docs/sanskrit-glossary.md) — All Sanskrit terms explained
- [**Contributing**](CONTRIBUTING.md) — How to contribute

---

## 💖 Support & Donate

If Vākya helps you or you believe in open AI communication, please consider supporting the project:

| Platform | Link |
|----------|------|
| ⭐ **GitHub Stars** | [Star this repo](https://github.com/prakashgarg91/Open-communication) — it helps a lot! |
| 💖 **GitHub Sponsors** | [Sponsor on GitHub](https://github.com/sponsors/prakashgarg91) |
| ☕ **Buy Me a Coffee** | [buymeacoffee.com/prakashgarg91](https://buymeacoffee.com/prakashgarg91) |
| 🎁 **Ko-fi** | [ko-fi.com/prakashgarg91](https://ko-fi.com/prakashgarg91) |
| 🌐 **Open Collective** | [opencollective.com/open-communication](https://opencollective.com/open-communication) |
| 💳 **PayPal** | [paypal.me/prakashgarg91](https://paypal.me/prakashgarg91) |

Your support helps keep this project open-source and actively maintained. Every contribution matters! 🙏

---

## 🗺️ Roadmap

- [x] Core protocol specification
- [x] Python reference implementation
- [x] Message types & routing
- [x] Task distribution system
- [x] AI model adapters (OpenAI, Anthropic, GLM, Ollama)
- [x] WebSocket relay server
- [x] REST API
- [x] Human monitoring terminal viewer
- [x] **Cross-IDE bridge (Setu) — VS Code ↔ Claude Code ↔ OpenCode ↔ Zed ↔ Cursor**
- [x] **IDE auto-detection (Khoj discovery)**
- [x] **Multi-transport support (WebSocket, Stdio, HTTP)**
- [ ] End-to-end encryption
- [ ] JavaScript/TypeScript implementation
- [ ] Go implementation
- [ ] Rust implementation
- [ ] Web-based monitoring dashboard
- [ ] Plugin system for custom message types
- [ ] Multi-modal support (images, audio, files)
- [ ] Persistent message storage
- [ ] Authentication & authorization
- [ ] Rate limiting & quotas

---

## 📜 License

MIT License — free for everyone, forever.

---

<p align="center">
  <em>ॐ सर्वे भवन्तु सुखिनः — May all beings communicate in harmony</em>
  <br><br>
  Built with ❤️ for the open AI community
</p>
