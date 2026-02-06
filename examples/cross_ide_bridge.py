"""
Cross-IDE Bridge Example — AI Agents in Different IDEs Collaborating
=====================================================================

This example demonstrates how AI agents running in different IDE
containers (VS Code, Claude Code, OpenCode, Zed, etc.) can discover
each other and communicate through the Vākya Bridge (Setu).

To run this example:

    Terminal 1 — Start the Setu bridge:
        vakya-bridge --verbose

    Terminal 2 — Run this example (simulates agents from different IDEs):
        python examples/cross_ide_bridge.py

In real usage, each IDE's AI agent would connect independently using
its own Yojaka (connector).
"""

import asyncio
import json
import os
from vakya import (
    Duta, DutaRole, Prasna, Uttara, Karya, Prativedana,
    VakyaProtocol, SabhaRouter,
)
from vakya.bridge.khoj import Khoj, IDEEnvironment, IDEType
from vakya.bridge.setu import Setu, SetuConfig


async def demo_local_bridge():
    """
    Demonstrate cross-IDE communication locally without a running server.

    This simulates what happens when agents in different IDEs communicate:
    1. A Setu (bridge) is set up
    2. Agents from different IDEs register
    3. They discover each other
    4. They exchange Vākya messages
    5. A human observes the cross-IDE conversation
    """
    print("=" * 60)
    print("  वाक्य सेतु — Vākya Bridge Demo")
    print("  Cross-IDE AI Communication")
    print("=" * 60)
    print()

    # ── Step 1: Set up the discovery service ──
    print("📡 Step 1: Initialize Khoj (Discovery)...")
    khoj = Khoj()

    # Detect current environment
    current_env = khoj.detect_environment()
    print(f"   Current IDE: {current_env.ide_name} ({current_env.ide_type.value})")
    print()

    # ── Step 2: Create AI agents from different IDEs ──
    print("🤖 Step 2: Register agents from different IDEs...")

    # Simulate a Claude agent running in VS Code
    vscode_claude = Duta(
        id="vscode-claude",
        name="Claude (VS Code)",
        model="claude-sonnet-4-20250514",
        provider="anthropic",
        role=DutaRole.NETA,  # Leader
        skills=["architecture", "code-generation", "review"],
    )
    vscode_env = IDEEnvironment(
        ide_type=IDEType.VSCODE,
        ide_name="Visual Studio Code",
        workspace="/home/user/project",
    )
    agent1 = khoj.register_agent(
        duta_id=vscode_claude.id,
        duta_name=vscode_claude.name,
        transport="websocket",
        endpoint="ws://localhost:8765",
        capabilities=vscode_claude.skills,
        environment=vscode_env,
    )
    print(f"   ✅ {vscode_claude.name} registered from VS Code")

    # Simulate a GPT agent running in OpenCode
    opencode_gpt = Duta(
        id="opencode-gpt",
        name="GPT-4o (OpenCode)",
        model="gpt-4o",
        provider="openai",
        role=DutaRole.KARTR,  # Worker
        skills=["code-generation", "testing", "documentation"],
    )
    opencode_env = IDEEnvironment(
        ide_type=IDEType.OPENCODE,
        ide_name="OpenCode",
    )
    agent2 = khoj.register_agent(
        duta_id=opencode_gpt.id,
        duta_name=opencode_gpt.name,
        transport="stdio",
        endpoint="",
        capabilities=opencode_gpt.skills,
        environment=opencode_env,
    )
    print(f"   ✅ {opencode_gpt.name} registered from OpenCode")

    # Simulate an agent running in Claude Code
    claude_code_agent = Duta(
        id="claude-code-agent",
        name="Claude (Claude Code)",
        model="claude-opus-4-20250514",
        provider="anthropic",
        role=DutaRole.SAMIKSHAKA,  # Reviewer
        skills=["review", "security-analysis", "testing"],
    )
    claude_code_env = IDEEnvironment(
        ide_type=IDEType.CLAUDE_CODE,
        ide_name="Claude Code",
    )
    agent3 = khoj.register_agent(
        duta_id=claude_code_agent.id,
        duta_name=claude_code_agent.name,
        transport="stdio",
        endpoint="",
        capabilities=claude_code_agent.skills,
        environment=claude_code_env,
    )
    print(f"   ✅ {claude_code_agent.name} registered from Claude Code")

    # Simulate an agent running in Zed
    zed_agent = Duta(
        id="zed-agent",
        name="Local LLM (Zed)",
        model="llama-3.1-70b",
        provider="ollama",
        role=DutaRole.PARIKSAKA,  # Tester
        skills=["testing", "benchmarking"],
    )
    zed_env = IDEEnvironment(
        ide_type=IDEType.ZED,
        ide_name="Zed",
    )
    agent4 = khoj.register_agent(
        duta_id=zed_agent.id,
        duta_name=zed_agent.name,
        transport="websocket",
        endpoint="ws://localhost:8765",
        capabilities=zed_agent.skills,
        environment=zed_env,
    )
    print(f"   ✅ {zed_agent.name} registered from Zed")
    print()

    # ── Step 3: Discover all agents ──
    print("🔍 Step 3: Discover all agents across IDEs...")
    all_agents = khoj.discover_agents(active_only=False, max_age_seconds=0)
    for agent in all_agents:
        print(f"   🔗 {agent.duta_name} in {agent.environment.ide_name} via {agent.transport}")
    print()

    # Show discovery status
    status = khoj.status()
    print(f"   📊 Discovery Status:")
    print(f"      Total agents: {status['total_agents']}")
    print(f"      IDE breakdown: {status['ide_breakdown']}")
    print()

    # ── Step 4: Simulate cross-IDE message exchange ──
    print("💬 Step 4: Cross-IDE Message Exchange...")
    print()

    protocol = VakyaProtocol()
    router = SabhaRouter(name="Cross-IDE Assembly")

    # Register all agents with the router
    router.register_duta(vscode_claude)
    router.register_duta(opencode_gpt)
    router.register_duta(claude_code_agent)
    router.register_duta(zed_agent)

    # Human observer
    messages_seen = []

    async def observe(msg, channel):
        source_ide = "unknown"
        for a in all_agents:
            if a.duta_id == msg.presaka:
                source_ide = a.environment.ide_name
                break
        messages_seen.append(msg)
        print(f"   👁 [{source_ide}] {msg}")

    router.add_observer(observe)

    # VS Code Claude assigns a task to OpenCode GPT
    print("   📤 VS Code Claude → OpenCode GPT:")
    task_msg = Karya(
        presaka=vscode_claude.id,
        prapaka=opencode_gpt.id,
        text="Write comprehensive unit tests for the authentication module",
        title="Auth Module Testing",
        description="Write comprehensive unit tests for the authentication module",
        visaya="testing",
        meta={"source_ide": "Visual Studio Code", "priority": "high"},
    )
    await router.route(task_msg)
    print()

    # OpenCode GPT reports progress
    print("   📤 OpenCode GPT → VS Code Claude:")
    progress = Prativedana(
        presaka=opencode_gpt.id,
        prapaka=vscode_claude.id,
        karya_id=task_msg.id,
        sthiti="sampurna",
        pravrtti=1.0,
        vivarana="Written 15 unit tests covering login, signup, and token refresh flows",
        meta={"source_ide": "OpenCode", "tests_written": 15, "coverage": "87%"},
    )
    await router.route(progress)
    print()

    # Claude Code agent reviews
    print("   📤 Claude Code Agent reviews the tests:")
    review = Prasna(
        presaka=claude_code_agent.id,
        prapaka=opencode_gpt.id,
        text="The tests look solid. Did you also cover edge cases for expired tokens and rate limiting?",
        visaya="review",
        meta={"source_ide": "Claude Code"},
    )
    await router.route(review)
    print()

    # Zed agent runs benchmarks
    print("   📤 Zed Agent runs benchmarks:")
    benchmark = Uttara(
        presaka=zed_agent.id,
        text="Benchmark results: all 15 tests pass in 0.3s, no memory leaks detected",
        visaya="testing",
        meta={"source_ide": "Zed", "duration_ms": 300, "memory_leak": False},
    )
    await router.route(benchmark)
    print()

    # ── Step 5: Summary ──
    print("=" * 60)
    print("  📊 Cross-IDE Communication Summary")
    print("=" * 60)
    print(f"  Messages exchanged: {len(messages_seen)}")
    print(f"  IDEs involved: VS Code, OpenCode, Claude Code, Zed")
    print(f"  Protocol: Vākya v1.0")
    print(f"  Transport: Mixed (WebSocket + Stdio)")
    print()
    print("  🌉 The Setu (bridge) enables seamless communication")
    print("  between AI agents regardless of which IDE they run in.")
    print()
    print("  To use in production:")
    print("    1. Start the bridge:  vakya-bridge --verbose")
    print("    2. Each IDE's AI connects via its Yojaka (connector)")
    print("    3. Messages flow freely across IDE boundaries")
    print()

    # Cleanup
    for agent in all_agents:
        khoj.unregister_agent(agent.id)


if __name__ == "__main__":
    asyncio.run(demo_local_bridge())
