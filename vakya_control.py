"""
Vākya Control Center — Single-Window Orchestrator
====================================================

वाक्य नियन्त्रण केन्द्र (Vākya Niyantrana Kendra) = Vākya Control Center

Run everything from a single window:
    - Setu Bridge (background)
    - Agent registration
    - Discovery dashboard
    - Live message monitor
    - Interactive command shell

Usage:
    python vakya_control.py              # Full interactive mode
    python vakya_control.py --demo       # Run demo with simulated agents
    python vakya_control.py --port 9000  # Custom port
"""

import asyncio
import json
import os
import sys
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from vakya import (
    Duta, DutaRole, Prasna, Uttara, Karya, Prativedana,
    VakyaProtocol, SabhaRouter,
)
from vakya.bridge.khoj import Khoj, IDEEnvironment, IDEType
from vakya.bridge.setu import Setu, SetuConfig

# ─── Terminal Colors (Windows compatible) ────────────────────────────────────

os.system("")  # Enable ANSI on Windows

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAGENTA= "\033[35m"
CYAN   = "\033[36m"
WHITE  = "\033[37m"
BG_BLUE= "\033[44m"

ICONS = {
    "bridge": "🌉",
    "agent":  "🤖",
    "search": "🔍",
    "msg":    "💬",
    "task":   "📋",
    "eye":    "👁",
    "check":  "✅",
    "cross":  "❌",
    "warn":   "⚠️",
    "bolt":   "⚡",
    "star":   "⭐",
    "gear":   "⚙️",
    "plug":   "🔌",
    "bell":   "🔔",
}


def banner():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     {YELLOW}वाक्य नियन्त्रण केन्द्र{CYAN}                                  ║
║     {WHITE}Vākya Control Center v1.0{CYAN}                                 ║
║                                                              ║
║     {DIM}{WHITE}Open Protocol for AI-to-AI Communication{CYAN}                 ║
║     {DIM}{WHITE}Cross-IDE • Cross-Model • Human Observable{CYAN}              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")


def section(title: str, icon: str = "gear"):
    print(f"\n{BOLD}{BLUE}{'─' * 60}{RESET}")
    print(f"  {ICONS.get(icon, '●')} {BOLD}{WHITE}{title}{RESET}")
    print(f"{BLUE}{'─' * 60}{RESET}")


def status_line(label: str, value: str, color: str = GREEN):
    print(f"  {DIM}▸{RESET} {label}: {color}{value}{RESET}")


def ok(msg: str):
    print(f"  {ICONS['check']} {GREEN}{msg}{RESET}")


def warn(msg: str):
    print(f"  {ICONS['warn']} {YELLOW}{msg}{RESET}")


def err(msg: str):
    print(f"  {ICONS['cross']} {RED}{msg}{RESET}")


def msg_display(source_ide: str, sender: str, receiver: str, text: str, prakara: str = "vakya"):
    color_map = {
        "prasna": CYAN, "uttara": GREEN, "karya": YELLOW,
        "prativedana": BLUE, "vakya": WHITE, "svikriti": MAGENTA,
    }
    color = color_map.get(prakara, WHITE)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"  {DIM}{timestamp}{RESET} {color}[{prakara}]{RESET} "
          f"{BOLD}{sender}{RESET} {DIM}({source_ide}){RESET} → {receiver}")
    if text:
        # Wrap long text
        for line in text.split("\n"):
            print(f"           {color}{line}{RESET}")


# ─── Bridge Runner (Background) ─────────────────────────────────────────────

class BridgeRunner:
    """Runs Setu bridge in a background thread."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._setu: Setu | None = None
        self.running = False

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(1)  # Let it spin up
        self.running = True

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        config = SetuConfig(host=self.host, port=self.port)
        self._setu = Setu(config)

        try:
            self._loop.run_until_complete(self._setu.start())
        except Exception:
            pass

    def stop(self):
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)


# ─── Main Control Center ────────────────────────────────────────────────────

class ControlCenter:
    """Single-window command center for Vākya."""

    def __init__(self, port: int = 8765):
        self.port = port
        self.bridge = BridgeRunner(port=port)
        self.khoj = Khoj()
        self.protocol = VakyaProtocol()
        self.router = SabhaRouter(name="Control Center Assembly")
        self.agents: dict[str, tuple[Duta, IDEEnvironment]] = {}
        self.messages: list[dict] = []

    async def observe(self, msg, channel):
        """Observer callback for human monitoring."""
        source_ide = "Unknown"
        for aid, (duta, env) in self.agents.items():
            if duta.id == msg.presaka:
                source_ide = env.ide_name
                break

        receiver = msg.prapaka or "*"
        if isinstance(receiver, list):
            receiver = ", ".join(receiver)

        text = msg.sarira.get("text", "")
        if not text and msg.sarira.get("title"):
            text = f"Task: {msg.sarira['title']}"
        if not text and msg.sarira.get("vivarana"):
            text = msg.sarira["vivarana"]

        sender_name = msg.presaka
        for aid, (duta, env) in self.agents.items():
            if duta.id == msg.presaka:
                sender_name = duta.name
                break

        msg_display(source_ide, sender_name, receiver, text, msg.prakara.value)
        self.messages.append({
            "time": datetime.now().isoformat(),
            "from": msg.presaka, "to": receiver,
            "type": msg.prakara.value, "text": text,
        })

    def register_agent(self, name: str, model: str, provider: str,
                        ide_type: IDEType, ide_name: str,
                        role: DutaRole = DutaRole.KARTR,
                        skills: list[str] | None = None) -> Duta:
        """Register an agent from an IDE."""
        duta = Duta(
            name=name, model=model, provider=provider,
            role=role, skills=skills or [],
        )
        env = IDEEnvironment(ide_type=ide_type, ide_name=ide_name)

        self.router.register_duta(duta)
        self.khoj.register_agent(
            duta_id=duta.id, duta_name=name,
            transport="websocket",
            endpoint=f"ws://localhost:{self.port}",
            capabilities=duta.skills, environment=env,
        )
        self.agents[duta.id] = (duta, env)
        return duta

    def show_dashboard(self):
        """Display the current status dashboard."""
        section("Dashboard", "search")

        status = self.khoj.status()
        status_line("Setu Bridge", f"ws://localhost:{self.port}" if self.bridge.running else "STOPPED",
                     GREEN if self.bridge.running else RED)
        status_line("Registered Agents", str(status["total_agents"]))
        status_line("Active Agents", str(status["active_agents"]))
        status_line("Messages Exchanged", str(len(self.messages)))

        if self.agents:
            print(f"\n  {BOLD}Connected Agents:{RESET}")
            for aid, (duta, env) in self.agents.items():
                print(f"    {ICONS['agent']} {BOLD}{duta.name}{RESET} "
                      f"{DIM}({duta.model}){RESET} in "
                      f"{CYAN}{env.ide_name}{RESET} "
                      f"[{duta.role.value}]")

        if status.get("ide_breakdown"):
            print(f"\n  {BOLD}IDE Breakdown:{RESET}")
            for ide, count in status["ide_breakdown"].items():
                print(f"    {ICONS['plug']} {ide}: {count} agent(s)")

    def show_help(self):
        """Show available commands."""
        section("Commands", "star")
        cmds = [
            ("dashboard / d",     "Show status dashboard"),
            ("agents / a",        "List all registered agents"),
            ("discover",          "Run discovery scan"),
            ("add <ide>",         "Add a simulated agent (vscode/opencode/claude/zed/cursor)"),
            ("send <from> <to> <msg>", "Send a message between agents"),
            ("ask <from> <to> <question>", "Send a question"),
            ("task <from> <to> <title>",   "Assign a task"),
            ("demo",              "Run the full cross-IDE demo"),
            ("messages / m",      "Show message history"),
            ("clear",             "Clear the screen"),
            ("help / h / ?",      "Show this help"),
            ("quit / q / exit",   "Stop everything and exit"),
        ]
        for cmd, desc in cmds:
            print(f"  {CYAN}{cmd:<30}{RESET} {desc}")

    async def run_demo(self):
        """Run a full demo with 4 simulated IDE agents."""
        section("Cross-IDE Demo", "bolt")
        print(f"  Simulating 4 AI agents across 4 different IDEs...\n")

        # Register agents
        claude_vscode = self.register_agent(
            "Claude Sonnet", "claude-sonnet-4-20250514", "anthropic",
            IDEType.VSCODE, "VS Code", DutaRole.NETA,
            ["architecture", "code-generation", "review"],
        )
        ok(f"Claude Sonnet registered from VS Code")

        gpt_opencode = self.register_agent(
            "GPT-4o", "gpt-4o", "openai",
            IDEType.OPENCODE, "OpenCode", DutaRole.KARTR,
            ["code-generation", "testing", "docs"],
        )
        ok(f"GPT-4o registered from OpenCode")

        claude_cc = self.register_agent(
            "Claude Opus", "claude-opus-4-20250514", "anthropic",
            IDEType.CLAUDE_CODE, "Claude Code", DutaRole.SAMIKSHAKA,
            ["review", "security", "testing"],
        )
        ok(f"Claude Opus registered from Claude Code")

        llama_zed = self.register_agent(
            "LLaMA 3.1", "llama-3.1-70b", "ollama",
            IDEType.ZED, "Zed", DutaRole.PARIKSAKA,
            ["testing", "benchmarking"],
        )
        ok(f"LLaMA 3.1 registered from Zed")

        print()
        section("Live Message Feed", "msg")
        print()

        # VS Code Claude → OpenCode GPT: task assignment
        task = Karya(
            presaka=claude_vscode.id, prapaka=gpt_opencode.id,
            title="Write auth module tests", description="Write unit tests for authentication",
            visaya="testing", priority="ucca",
        )
        await self.router.route(task)
        await asyncio.sleep(0.3)

        # OpenCode GPT → VS Code Claude: progress report
        report = Prativedana(
            presaka=gpt_opencode.id, prapaka=claude_vscode.id,
            karya_id=task.id, sthiti="sampurna", pravrtti=1.0,
            vivarana="15 tests written: login, signup, token refresh. Coverage 87%.",
        )
        await self.router.route(report)
        await asyncio.sleep(0.3)

        # Claude Code → OpenCode GPT: code review question
        review_q = Prasna(
            presaka=claude_cc.id, prapaka=gpt_opencode.id,
            text="Tests look solid. Did you cover expired tokens and rate limiting edge cases?",
            visaya="review",
        )
        await self.router.route(review_q)
        await asyncio.sleep(0.3)

        # OpenCode GPT → Claude Code: answer
        answer = Uttara(
            presaka=gpt_opencode.id,
            text="Yes — added 3 more tests for token expiry and 2 for rate limiting. Coverage now 94%.",
            reply_to=review_q,
        )
        await self.router.route(answer)
        await asyncio.sleep(0.3)

        # Zed LLaMA → broadcast: benchmark results
        benchmark = Uttara(
            presaka=llama_zed.id,
            text="Benchmark complete: all 20 tests pass in 0.28s, zero memory leaks, CPU peak 12%.",
            visaya="benchmarking",
        )
        await self.router.route(benchmark)
        await asyncio.sleep(0.2)

        print()
        section("Demo Complete", "check")
        status_line("Messages exchanged", str(len(self.messages)))
        status_line("IDEs involved", "VS Code, OpenCode, Claude Code, Zed")
        status_line("Protocol", "Vākya v1.0")

    async def handle_command(self, line: str) -> bool:
        """Process a user command. Returns False to quit."""
        parts = line.strip().split(maxsplit=3)
        if not parts:
            return True
        cmd = parts[0].lower()

        if cmd in ("quit", "q", "exit"):
            return False

        elif cmd in ("help", "h", "?"):
            self.show_help()

        elif cmd in ("dashboard", "d", "status"):
            self.show_dashboard()

        elif cmd in ("agents", "a"):
            if not self.agents:
                warn("No agents registered. Use 'add <ide>' or 'demo'.")
            else:
                for aid, (duta, env) in self.agents.items():
                    print(f"  {ICONS['agent']} {BOLD}{duta.name}{RESET} "
                          f"id={DIM}{duta.id}{RESET} "
                          f"{CYAN}{env.ide_name}{RESET} "
                          f"role={duta.role.value} skills={duta.skills}")

        elif cmd == "discover":
            agents = self.khoj.discover_agents(active_only=False, max_age_seconds=0)
            if not agents:
                warn("No agents discovered.")
            else:
                section(f"Discovered {len(agents)} Agent(s)", "search")
                for a in agents:
                    print(f"  {ICONS['plug']} {a.duta_name} in {a.environment.ide_name} "
                          f"via {a.transport}")

        elif cmd == "add":
            ide = parts[1].lower() if len(parts) > 1 else ""
            presets = {
                "vscode": ("Copilot", "gpt-4o", "openai", IDEType.VSCODE, "VS Code", ["code-generation", "chat"]),
                "opencode": ("OpenCode Agent", "gpt-4o", "openai", IDEType.OPENCODE, "OpenCode", ["code-generation", "testing"]),
                "claude": ("Claude", "claude-sonnet-4-20250514", "anthropic", IDEType.CLAUDE_CODE, "Claude Code", ["review", "analysis"]),
                "zed": ("Zed Assistant", "llama-3.1-70b", "ollama", IDEType.ZED, "Zed", ["testing", "benchmarking"]),
                "cursor": ("Cursor AI", "gpt-4o", "openai", IDEType.CURSOR, "Cursor", ["code-generation", "autocomplete"]),
            }
            if ide not in presets:
                warn(f"Unknown IDE: {ide}. Options: {', '.join(presets.keys())}")
            else:
                name, model, prov, itype, iname, skills = presets[ide]
                duta = self.register_agent(name, model, prov, itype, iname, skills=skills)
                ok(f"{name} registered from {iname} (id: {duta.id})")

        elif cmd == "send" and len(parts) >= 4:
            await self._route_user_msg(parts[1], parts[2], parts[3], "vakya")

        elif cmd == "ask" and len(parts) >= 4:
            await self._route_user_msg(parts[1], parts[2], parts[3], "prasna")

        elif cmd == "task" and len(parts) >= 4:
            from_id = self._resolve_agent(parts[1])
            to_id = self._resolve_agent(parts[2])
            if from_id and to_id:
                task = Karya(
                    presaka=from_id, prapaka=to_id,
                    title=parts[3], description=parts[3],
                )
                await self.router.route(task)
            else:
                err("Agent not found. Use 'agents' to see IDs or names.")

        elif cmd in ("messages", "m"):
            if not self.messages:
                warn("No messages yet.")
            else:
                section(f"Message History ({len(self.messages)})", "msg")
                for m in self.messages[-20:]:
                    print(f"  {DIM}{m['time'][:19]}{RESET} [{m['type']}] "
                          f"{m['from']} → {m['to']}: {m['text'][:60]}")

        elif cmd == "demo":
            await self.run_demo()

        elif cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            banner()

        else:
            warn(f"Unknown command: {cmd}. Type 'help' for commands.")

        return True

    async def _route_user_msg(self, from_str: str, to_str: str, text: str, prakara: str):
        from_id = self._resolve_agent(from_str)
        to_id = self._resolve_agent(to_str)
        if not from_id or not to_id:
            err("Agent not found. Use 'agents' to see registered agents.")
            return
        if prakara == "prasna":
            msg = Prasna(presaka=from_id, prapaka=to_id, text=text)
        else:
            from vakya.message import Vakya, MessageType
            msg = Vakya(presaka=from_id, prapaka=to_id,
                        prakara=MessageType.VAKYA, sarira={"text": text})
        await self.router.route(msg)

    def _resolve_agent(self, name_or_id: str) -> str | None:
        """Find agent by ID prefix or name substring."""
        name_lower = name_or_id.lower()
        for aid, (duta, env) in self.agents.items():
            if aid == name_or_id or aid.startswith(name_or_id):
                return aid
            if name_lower in duta.name.lower():
                return aid
            if name_lower in env.ide_name.lower():
                return aid
        return None

    async def run(self, demo_mode: bool = False):
        """Main control loop."""
        banner()

        # Start bridge
        section("Starting Setu Bridge", "bridge")
        self.bridge.start()
        if self.bridge.running:
            ok(f"Setu bridge running on ws://localhost:{self.port}")
        else:
            err("Failed to start bridge")
            return

        # Set up observer
        self.router.add_observer(self.observe)

        if demo_mode:
            await self.run_demo()
            print()

        # Interactive loop
        section("Interactive Control", "gear")
        print(f"  Type {CYAN}help{RESET} for commands, {CYAN}demo{RESET} to run demo, "
              f"{CYAN}quit{RESET} to exit.\n")

        try:
            while True:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input(f"{BOLD}{YELLOW}vakya>{RESET} ")
                    )
                    if not await self.handle_command(line):
                        break
                except EOFError:
                    break
        except KeyboardInterrupt:
            pass

        # Cleanup
        section("Shutting Down", "plug")
        self.bridge.stop()

        # Cleanup discovery
        for aid in list(self.agents.keys()):
            agents = self.khoj.discover_agents(active_only=False, max_age_seconds=0)
            for a in agents:
                if a.duta_id == aid:
                    self.khoj.unregister_agent(a.id)

        ok("All stopped. नमस्ते! 🙏")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Vākya Control Center — Single-window AI bridge orchestrator",
    )
    parser.add_argument("--port", type=int, default=8765, help="Bridge port (default: 8765)")
    parser.add_argument("--demo", action="store_true", help="Auto-run the cross-IDE demo")
    args = parser.parse_args()

    cc = ControlCenter(port=args.port)
    asyncio.run(cc.run(demo_mode=args.demo))


if __name__ == "__main__":
    main()
