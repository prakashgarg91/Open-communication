# Getting Started with Vākya
## Quick Start Guide (त्वरित आरम्भ)

### Installation

```bash
# Basic install
pip install vakya

# With specific AI provider support
pip install vakya[openai]       # For GPT models
pip install vakya[anthropic]    # For Claude models
pip install vakya[all]          # Everything
```

### 1. Send Your First Message

```python
from vakya import Vakya, Prasna, Uttara, VakyaProtocol

# Create a question
question = Prasna(
    presaka="my-ai-1",        # Sender (प्रेषक)
    prapaka="my-ai-2",        # Receiver (प्रापक)
    text="What is the best sorting algorithm for nearly-sorted data?",
    visaya="algorithms",       # Topic (विषय)
)

# Create a response
answer = Uttara(
    presaka="my-ai-2",
    text="Insertion sort or Timsort — both are O(n) for nearly-sorted data.",
    reply_to=question,
)

# Encode for the wire
protocol = VakyaProtocol()
wire_message = protocol.encode(question)
print(wire_message)
```

### 2. Set Up an AI Assembly

```python
import asyncio
from vakya import Duta, DutaRole, SabhaRouter, Prasna, Uttara

async def main():
    # Create AI identities
    claude = Duta(
        id="claude-1", name="Claude",
        model="claude-opus-4.6", provider="anthropic",
        role=DutaRole.KARTR, skills=["coding", "analysis"],
    )
    gpt = Duta(
        id="gpt-1", name="GPT-4o",
        model="gpt-4o", provider="openai",
        role=DutaRole.KARTR, skills=["coding", "vision"],
    )

    # Create assembly router
    router = SabhaRouter(name="My Team")
    router.register_duta(claude)
    router.register_duta(gpt)

    # Add human observer (you!)
    async def my_observer(msg, channel):
        print(f"[{msg.prakara.value}] {msg.presaka} → {msg.prapaka}: "
              f"{msg.sarira.get('text', '')[:80]}")

    router.add_observer(my_observer)

    # Route messages
    q = Prasna(presaka="claude-1", prapaka="gpt-1", text="Ready to collaborate?")
    await router.route(q)

asyncio.run(main())
```

### 3. Connect Real AI Models

```python
from vakya.adapters import OpenAIAdapter, AnthropicAdapter, AdapterConfig
from vakya.identity import create_claude_duta, create_gpt_duta

# Set up Claude
claude = create_claude_duta()
claude_adapter = AnthropicAdapter(
    AdapterConfig(api_key="sk-ant-...", model="claude-opus-4.6"),
    claude,
)

# Set up GPT
gpt = create_gpt_duta()
gpt_adapter = OpenAIAdapter(
    AdapterConfig(api_key="sk-...", model="gpt-4o"),
    gpt,
)

# Have them communicate
question = Prasna(presaka=gpt.id, text="Explain quantum computing simply.")
response = await claude_adapter.send(question)
print(response.sarira["text"])
```

### 4. Run the Relay Server

```bash
# Start the WebSocket relay
vakya-server --port 8765 --verbose

# In another terminal, start the human viewer
vakya-monitor --server ws://localhost:8765
```

### 5. Distribute Tasks

```python
from vakya import KaryaManager
from vakya.task import KaryaPriority

manager = KaryaManager()

task = manager.create(
    title="Analyze dataset",
    description="Perform statistical analysis on sales data",
    presaka="coordinator",
    skills_needed=["data-analysis", "python"],
    priority=KaryaPriority.UCCA,
)

# Auto-assign to best available AI
assigned = manager.auto_assign(task.id, available_dutas)
print(f"Task assigned to: {assigned.name}")

# Track progress
manager.update_progress(task.id, 0.5, "Halfway done")
manager.complete(task.id, result={"insights": 5, "report": "..."})
```

### What's Next?

- Read the [Protocol Specification](protocol-spec.md)
- Check out the [Examples](../examples/)
- Learn the [Sanskrit Glossary](sanskrit-glossary.md)
- Join the community on GitHub
