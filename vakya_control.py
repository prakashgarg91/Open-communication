"""
Vākya Control Center v2 — Unified AI Orchestrator
====================================================

वाक्य नियन्त्रण केन्द्र (Vākya Niyantrana Kendra) = Vākya Control Center

Single window to:
    - Auto-detect your current AI + IDE (e.g., Claude 4.6 in VS Code Copilot)
    - Connect to real AI APIs (OpenAI, Anthropic, Ollama, Gemini)
    - Chat with any connected AI — get real responses
    - Run multi-AI discussions — all AIs collaborate on a topic
    - Bridge across IDEs (VS Code, Claude Code, OpenCode, Zed, etc.)
    - Monitor all AI-to-AI communication live

Usage:
    python vakya_control.py              # Interactive mode
    python vakya_control.py --demo       # Run demo with simulated agents
    python vakya_control.py --auto       # Auto-connect all available APIs
    vakya.bat                            # Double-click on Windows
"""

import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from vakya import (
    Duta, DutaRole, Prasna, Uttara, Karya, Prativedana,
    VakyaProtocol, SabhaRouter,
)
from vakya.bridge.khoj import Khoj, IDEEnvironment, IDEType
from vakya.bridge.setu import Setu, SetuConfig
from vakya.live import (
    LiveAgent, SelfAgent, OpenAIAgent, AnthropicAgent,
    OllamaAgent, GeminiAgent, KimiCLIAgent, OpenCodeCLIAgent,
    detect_self, detect_api_keys, create_agent, discover_ollama_models,
    discover_cli_agents,
)
from vakya.hierarchy import (
    WorkflowEngine, ProjectPlan, TaskItem, TaskStatus, ProjectStatus,
)

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

ICONS = {
    "bridge": "🌉", "agent": "🤖", "search": "🔍", "msg": "💬",
    "task": "📋", "eye": "👁", "check": "✅", "cross": "❌",
    "warn": "⚠️", "bolt": "⚡", "star": "⭐", "gear": "⚙️",
    "plug": "🔌", "bell": "🔔", "brain": "🧠", "key": "🔑",
    "chat": "💭", "globe": "🌐", "self": "👤", "api": "🔗",
}

PROVIDER_COLORS = {
    "anthropic": MAGENTA, "openai": GREEN, "google": BLUE,
    "ollama": YELLOW, "unknown": DIM,
}


def banner():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     {YELLOW}वाक्य नियन्त्रण केन्द्र{CYAN}                                  ║
║     {WHITE}Vākya Control Center v2.0{CYAN}                                 ║
║                                                              ║
║     {DIM}{WHITE}Live AI APIs • Cross-IDE • Multi-Model Chat{CYAN}              ║
║     {DIM}{WHITE}OpenAI • Anthropic • Ollama • Gemini{CYAN}                    ║
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


def ai_response(agent_name: str, provider: str, text: str, latency: float = 0):
    """Display an AI response with formatting."""
    color = PROVIDER_COLORS.get(provider, WHITE)
    timestamp = datetime.now().strftime("%H:%M:%S")
    lat_str = f" {DIM}({latency:.1f}s){RESET}" if latency > 0 else ""
    print(f"\n  {DIM}{timestamp}{RESET} {color}{BOLD}{agent_name}{RESET}{lat_str}")
    # Word-wrap at ~70 chars
    for line in text.split("\n"):
        while len(line) > 70:
            # Find a good break point
            idx = line[:70].rfind(" ")
            if idx < 20:
                idx = 70
            print(f"  {color}│{RESET} {line[:idx]}")
            line = line[idx:].lstrip()
        if line:
            print(f"  {color}│{RESET} {line}")


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
        self.running = False

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(1)
        self.running = True

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        config = SetuConfig(host=self.host, port=self.port)
        setu = Setu(config)
        try:
            self._loop.run_until_complete(setu.start())
        except Exception:
            pass

    def stop(self):
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)


# ─── Main Control Center ────────────────────────────────────────────────────

class ControlCenter:
    """Single-window command center for Vākya with live AI integration."""

    def __init__(self, port: int = 8765):
        self.port = port
        self.bridge = BridgeRunner(port=port)
        self.khoj = Khoj()
        self.protocol = VakyaProtocol()
        self.router = SabhaRouter(name="Control Center Assembly")

        # Agent registries
        self.agents: dict[str, tuple[Duta, IDEEnvironment]] = {}
        self.live_agents: dict[str, LiveAgent] = {}  # duta_id -> LiveAgent (API-connected)
        self.self_agent: SelfAgent | None = None
        self.messages: list[dict] = []
        self._api_keys: dict[str, str] = {}

        # Workflow engine
        self.workflow: WorkflowEngine | None = None
        self._workflow_task: asyncio.Task | None = None

    # ─── Self Detection ──────────────────────────────────────────────────

    def _detect_and_register_self(self):
        """Auto-detect the current AI + IDE and register as visible agent."""
        section("Detecting Current Environment", "self")

        self.self_agent = detect_self()
        duta = self.self_agent.duta
        env = self.self_agent.environment

        # Register with router and discovery
        self.router.register_duta(duta)
        self.khoj.register_agent(
            duta_id=duta.id, duta_name=duta.name,
            transport="local", endpoint="self",
            capabilities=duta.skills, environment=env,
        )
        self.agents[duta.id] = (duta, env)
        self.live_agents[duta.id] = self.self_agent

        status_line("IDE", f"{env.ide_name}", CYAN)
        status_line("AI", f"{duta.name} ({duta.model})", MAGENTA)
        status_line("Role", "Orchestrator (नेता)", GREEN)
        status_line("PID", str(env.pid), DIM)
        status_line("Workspace", str(env.workspace), DIM)
        ok(f"Registered as visible agent: {duta.name}")

    # ─── API Key Management ──────────────────────────────────────────────

    def _detect_api_keys(self):
        """Detect API keys from environment."""
        self._api_keys = detect_api_keys()
        if self._api_keys:
            section("API Keys Detected", "key")
            for provider, key in self._api_keys.items():
                masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
                color = PROVIDER_COLORS.get(provider, WHITE)
                status_line(provider.title(), f"{color}{masked}{RESET}")
        else:
            section("No API Keys Found", "key")
            print(f"  Set environment variables to connect live AIs:")
            print(f"    {CYAN}OPENAI_API_KEY{RESET}    → GPT-4o, o1, etc.")
            print(f"    {CYAN}ANTHROPIC_API_KEY{RESET} → Claude Opus, Sonnet, Haiku")
            print(f"    {CYAN}GOOGLE_API_KEY{RESET}    → Gemini 2.0 Flash, Pro")
            print(f"    {CYAN}(no key needed){RESET}   → Ollama (local models)")

    async def _auto_connect_apis(self):
        """Auto-connect to all available APIs."""
        section("Connecting Live AI APIs", "api")

        connected = 0
        for provider, key in self._api_keys.items():
            agent = create_agent(provider, api_key=key)
            if agent:
                print(f"  {ICONS['globe']} Connecting to {provider.title()}...", end=" ", flush=True)
                if await agent.connect():
                    self._register_live_agent(agent)
                    print(f"{GREEN}connected{RESET} ({agent.duta.model})")
                    connected += 1
                else:
                    print(f"{RED}failed{RESET}")

        # Always try Ollama — connect ALL available chat models
        print(f"  {ICONS['globe']} Checking Ollama (local)...", end=" ", flush=True)
        ollama_models = await discover_ollama_models()
        if ollama_models:
            print(f"{GREEN}{len(ollama_models)} model(s) found{RESET}")
            for model_name in ollama_models:
                agent = OllamaAgent(model=model_name)
                if await agent.connect():
                    self._register_live_agent(agent)
                    display = model_name.replace(':latest', '')
                    print(f"    {GREEN}●{RESET} {YELLOW}{display}{RESET}")
                    connected += 1
        else:
            print(f"{DIM}not running{RESET}")

        if connected > 0:
            ok(f"{connected} live AI(s) connected")
        else:
            warn("No live AIs connected. Use 'connect <provider>' to add one.")

        # Also discover CLI agents (kimi, claude-code, opencode)
        cli_agents = discover_cli_agents()
        for provider_name, path in cli_agents:
            # Skip if already connected via Ollama
            already = any(provider_name in a.duta.provider for a in self.live_agents.values())
            if already:
                continue
            print(f"  {ICONS['globe']} Found CLI agent: {provider_name} at {path}...", end=" ", flush=True)
            agent = create_agent(provider_name)
            if agent and await agent.connect():
                self._register_live_agent(agent)
                print(f"{GREEN}connected{RESET} ({agent.duta.name})")
                connected += 1
            else:
                print(f"{DIM}skipped{RESET}")

    def _register_live_agent(self, agent: LiveAgent):
        """Register a live API agent with the system."""
        duta = agent.duta
        env = agent.environment

        self.router.register_duta(duta)
        self.khoj.register_agent(
            duta_id=duta.id, duta_name=duta.name,
            transport="api", endpoint=duta.provider,
            capabilities=duta.skills, environment=env,
        )
        self.agents[duta.id] = (duta, env)
        self.live_agents[duta.id] = agent

    # ─── Observer ────────────────────────────────────────────────────────

    async def observe(self, msg, channel):
        source_ide = "Unknown"
        sender_name = msg.presaka
        for aid, (duta, env) in self.agents.items():
            if duta.id == msg.presaka:
                source_ide = env.ide_name
                sender_name = duta.name
                break

        receiver = msg.prapaka or "*"
        if isinstance(receiver, list):
            receiver = ", ".join(receiver)

        text = msg.sarira.get("text", "")
        if not text and msg.sarira.get("title"):
            text = f"Task: {msg.sarira['title']}"
        if not text and msg.sarira.get("vivarana"):
            text = msg.sarira["vivarana"]

        msg_display(source_ide, sender_name, receiver, text, msg.prakara.value)
        self.messages.append({
            "time": datetime.now().isoformat(),
            "from": sender_name, "to": receiver,
            "type": msg.prakara.value, "text": text,
        })

    # ─── Agent Registration (simulated) ──────────────────────────────────

    def register_sim_agent(self, name: str, model: str, provider: str,
                            ide_type: IDEType, ide_name: str,
                            role: DutaRole = DutaRole.KARTR,
                            skills: list[str] | None = None) -> Duta:
        duta = Duta(name=name, model=model, provider=provider,
                    role=role, skills=skills or [])
        env = IDEEnvironment(ide_type=ide_type, ide_name=ide_name)
        self.router.register_duta(duta)
        self.khoj.register_agent(
            duta_id=duta.id, duta_name=name,
            transport="websocket", endpoint=f"ws://localhost:{self.port}",
            capabilities=duta.skills, environment=env,
        )
        self.agents[duta.id] = (duta, env)
        return duta

    # ─── Live Chat ───────────────────────────────────────────────────────

    async def chat_with(self, agent_name: str, message: str) -> str | None:
        """Send a message to a live AI agent and get a real response."""
        agent = self._resolve_live_agent(agent_name)
        if not agent:
            err(f"No live agent found matching '{agent_name}'.")
            print(f"  Connected APIs: {', '.join(a.duta.name for a in self.live_agents.values() if a.connected and not isinstance(a, SelfAgent))}")
            return None

        if isinstance(agent, SelfAgent):
            warn("That's you! Use 'chat' with another agent (openai, anthropic, ollama, gemini).")
            return None

        if not agent.connected:
            err(f"{agent.duta.name} is not connected.")
            return None

        print(f"\n  {ICONS['chat']} Asking {BOLD}{agent.duta.name}{RESET}...", flush=True)

        response = await agent.chat(message)
        ai_response(agent.duta.name, agent.duta.provider, response, agent.last_latency)

        # Route as Vākya message for observability
        assert self.self_agent is not None
        q = Prasna(presaka=self.self_agent.duta.id, prapaka=agent.duta.id, text=message)
        a = Uttara(presaka=agent.duta.id, prapaka=self.self_agent.duta.id, text=response, reply_to=q)
        # Don't route through observer to avoid double-display
        self.messages.append({"time": datetime.now().isoformat(), "from": self.self_agent.duta.name,
                             "to": agent.duta.name, "type": "prasna", "text": message})
        self.messages.append({"time": datetime.now().isoformat(), "from": agent.duta.name,
                             "to": self.self_agent.duta.name, "type": "uttara", "text": response[:200]})
        return response

    async def discuss(self, topic: str, rounds: int = 2):
        """Run a multi-AI roundtable discussion on a topic."""
        live = [a for a in self.live_agents.values()
                if a.connected and not isinstance(a, SelfAgent)]

        if len(live) < 2:
            err(f"Need at least 2 live AIs for a discussion. Connected: {len(live)}")
            warn("Use 'connect openai', 'connect anthropic', or 'connect ollama' first.")
            return

        section(f"Multi-AI Discussion: {topic}", "brain")
        print(f"  Participants: {', '.join(a.duta.name for a in live)}")
        print(f"  Rounds: {rounds}")
        print()

        context = f"Topic for collaborative discussion: {topic}\n\n"
        context += "You are in a multi-AI roundtable. Build on what others said. Be concise (2-3 paragraphs max)."

        for rnd in range(rounds):
            print(f"  {BOLD}── Round {rnd + 1}/{rounds} ──{RESET}")
            for agent in live:
                prompt = context if rnd == 0 else f"Continue the discussion. Previous context:\n{context}\n\nAdd your perspective concisely."
                response = await agent.chat(prompt)
                ai_response(agent.duta.name, agent.duta.provider, response, agent.last_latency)
                context += f"\n\n{agent.duta.name}: {response}"

                self.messages.append({
                    "time": datetime.now().isoformat(),
                    "from": agent.duta.name, "to": "roundtable",
                    "type": "discuss", "text": response[:200],
                })
            print()

        section("Discussion Complete", "check")
        status_line("Rounds", str(rounds))
        status_line("Participants", str(len(live)))
        total_tokens = sum(a.total_tokens for a in live)
        status_line("Total Tokens", str(total_tokens))

    # ─── Project Workflow ────────────────────────────────────────────────

    async def _workflow_event(self, event: str, data: dict):
        """Handle events from the WorkflowEngine for live display."""
        ts = datetime.now().strftime("%H:%M:%S")

        if event == "phase_start":
            phase = data.get("phase", "?")
            section(f"Workflow Phase: {phase}", "brain")
            if "description" in data:
                print(f"  {DIM}{data['description'][:80]}{RESET}")

        elif event == "plan_ready":
            ok(f"Plan created with {data['task_count']} tasks:")
            for tid, title in data.get("tasks", []):
                print(f"    {CYAN}{tid}.{RESET} {title}")

        elif event == "plan_failed":
            err(f"Planning failed. Raw output: {data.get('raw', '?')[:200]}")

        elif event == "task_start":
            worker = data.get("worker", "?")
            title = data.get("title", "?")
            attempt = data.get("attempt", 1)
            color = YELLOW if attempt == 1 else RED
            attempt_str = f" (attempt {attempt})" if attempt > 1 else ""
            print(f"\n  {DIM}{ts}{RESET} {ICONS['task']} "
                  f"{color}Task {data.get('task_id', '?')}{RESET}: {title}")
            print(f"           {DIM}→ assigned to{RESET} {BOLD}{worker}{RESET}{attempt_str}")

        elif event == "task_done":
            worker = data.get("worker", "?")
            elapsed = data.get("time", 0)
            preview = data.get("result_preview", "")[:100].replace("\n", " ")
            print(f"  {DIM}{ts}{RESET} {GREEN}✓{RESET} {worker} completed "
                  f"{DIM}({elapsed:.1f}s){RESET}")
            if preview:
                print(f"           {DIM}{preview}...{RESET}")

        elif event == "review_start":
            print(f"  {DIM}{ts}{RESET} {ICONS['eye']} Reviewing task {data.get('task_id', '?')}...",
                  end=" ", flush=True)

        elif event == "review_done":
            approved = data.get("approved", False)
            score = data.get("score", "?")
            feedback = data.get("feedback", "")[:80]
            if approved:
                print(f"{GREEN}approved{RESET} (score: {score}/10)")
            else:
                print(f"{RED}needs revision{RESET} (score: {score}/10)")
                if feedback:
                    print(f"           {DIM}Feedback: {feedback}{RESET}")

        elif event == "task_revision":
            print(f"  {DIM}{ts}{RESET} {YELLOW}↻{RESET} Revising task {data.get('task_id', '?')} "
                  f"(attempt {data.get('attempt', '?')})")

        elif event == "task_max_attempts":
            warn(f"Task {data.get('task_id', '?')} accepted after {data.get('attempts', '?')} attempts")

        elif event == "project_done":
            done = data.get("completed", 0)
            total = data.get("total_tasks", 0)
            elapsed = data.get("total_time", 0)
            tokens = data.get("total_tokens", 0)
            print()
            section("Project Complete", "check")
            status_line("Tasks completed", f"{done}/{total}")
            status_line("Total time", f"{elapsed:.1f}s")
            status_line("Total tokens", str(tokens))

    async def run_project(self, description: str):
        """Run a full automated AI project workflow."""
        # Get worker agents (all live, non-self)
        workers = [a for a in self.live_agents.values()
                   if a.connected and not isinstance(a, SelfAgent)]

        if not workers:
            err("No worker AIs connected. Use 'connect ollama' first.")
            return

        # Pick planner: prefer cloud/powerful model, fallback to first worker
        planner = workers[0]
        for w in workers:
            # Prefer cloud models (more powerful) for planning
            if ":cloud" in w.duta.model:
                planner = w
                break
            # Or models with "review" skill
            if "review" in w.duta.skills or "analysis" in w.duta.skills:
                planner = w

        section("Starting Automated Project", "brain")
        status_line("Project", description[:60])
        status_line("Planner (Leader)", planner.duta.name, MAGENTA)
        status_line("Workers", ", ".join(w.duta.name for w in workers), CYAN)
        print()

        self.workflow = WorkflowEngine(
            planner=planner,
            workers=workers,
            on_event=self._workflow_event,
        )

        result = await self.workflow.run(description)

        if result.status == ProjectStatus.DONE and result.final_output:
            section("Final Deliverable", "star")
            # Print final output with word wrap
            for line in result.final_output.split("\n"):
                if len(line) > 80:
                    while len(line) > 80:
                        idx = line[:80].rfind(" ")
                        if idx < 20:
                            idx = 80
                        print(f"  {line[:idx]}")
                        line = line[idx:].lstrip()
                    if line:
                        print(f"  {line}")
                else:
                    print(f"  {line}")
        elif result.status == ProjectStatus.FAILED:
            err("Project workflow failed. Check above for details.")
        elif result.status == ProjectStatus.STOPPED:
            warn("Project was stopped by user.")

    def show_project_status(self):
        """Display current project status."""
        if not self.workflow or not self.workflow.project:
            warn("No active project. Use 'project <description>' to start one.")
            return

        s = self.workflow.status_summary()
        section(f"Project Status: {s['status'].upper()}", "task")
        status_line("Description", s["description"])
        status_line("Tasks", f"{s['tasks_done']}/{s['tasks_total']} done, "
                    f"{s['tasks_running']} running, {s['tasks_pending']} pending")
        status_line("Tokens", str(s["total_tokens"]))
        status_line("Elapsed", s["elapsed"])

        if self.workflow.project:
            print()
            for t in self.workflow.project.tasks:
                icon = {
                    TaskStatus.DONE: f"{GREEN}✓{RESET}",
                    TaskStatus.RUNNING: f"{YELLOW}▶{RESET}",
                    TaskStatus.REVIEW: f"{CYAN}◉{RESET}",
                    TaskStatus.PENDING: f"{DIM}○{RESET}",
                    TaskStatus.FAILED: f"{RED}✗{RESET}",
                    TaskStatus.REVISION: f"{YELLOW}↻{RESET}",
                    TaskStatus.ASSIGNED: f"{BLUE}◆{RESET}",
                }.get(t.status, "?")
                assigned = f" → {t.assigned_to}" if t.assigned_to else ""
                print(f"  {icon} {t.id}. {t.title}{DIM}{assigned}{RESET}")

    # ─── Dashboard ───────────────────────────────────────────────────────

    def show_dashboard(self):
        section("Dashboard", "search")

        status = self.khoj.status()
        status_line("Setu Bridge",
                     f"ws://localhost:{self.port}" if self.bridge.running else "STOPPED",
                     GREEN if self.bridge.running else RED)
        status_line("Total Agents", str(len(self.agents)))
        status_line("Live APIs", str(sum(1 for a in self.live_agents.values()
                                          if a.connected and not isinstance(a, SelfAgent))))
        status_line("Messages", str(len(self.messages)))

        # Self agent
        if self.self_agent:
            d = self.self_agent.duta
            e = self.self_agent.environment
            print(f"\n  {ICONS['self']} {BOLD}You:{RESET} {MAGENTA}{d.name}{RESET} "
                  f"in {CYAN}{e.ide_name}{RESET}")

        # Live AIs
        live = [a for a in self.live_agents.values() if not isinstance(a, SelfAgent)]
        if live:
            print(f"\n  {BOLD}Live AI APIs:{RESET}")
            for agent in live:
                color = PROVIDER_COLORS.get(agent.duta.provider, WHITE)
                status_icon = f"{GREEN}●{RESET}" if agent.connected else f"{RED}●{RESET}"
                info = f"  reqs={agent.request_count} tokens={agent.total_tokens}" if agent.request_count else ""
                print(f"    {status_icon} {color}{BOLD}{agent.duta.name}{RESET} "
                      f"{DIM}({agent.duta.model}){RESET}{info}")

        # Simulated agents
        sim = [(aid, d, e) for aid, (d, e) in self.agents.items()
               if aid not in self.live_agents]
        if sim:
            print(f"\n  {BOLD}Simulated Agents:{RESET}")
            for aid, duta, env in sim:
                print(f"    {ICONS['agent']} {BOLD}{duta.name}{RESET} "
                      f"in {CYAN}{env.ide_name}{RESET} [{duta.role.value}]")

    def show_apis(self):
        """Show detailed status of all connected APIs."""
        section("Connected APIs", "api")

        live = [a for a in self.live_agents.values() if not isinstance(a, SelfAgent)]
        if not live:
            warn("No APIs connected. Use 'connect <provider>' to add one.")
            return

        for agent in live:
            color = PROVIDER_COLORS.get(agent.duta.provider, WHITE)
            status_icon = f"{GREEN}●{RESET}" if agent.connected else f"{RED}●{RESET}"
            print(f"\n  {status_icon} {color}{BOLD}{agent.duta.name}{RESET}")
            s = agent.status()
            for k, v in s.items():
                if k not in ("name", "connected"):
                    status_line(f"  {k}", str(v), DIM)

    # ─── Help ────────────────────────────────────────────────────────────

    def show_help(self):
        section("Commands", "star")

        print(f"\n  {BOLD}{YELLOW}── Project Workflow (auto-loop) ──{RESET}")
        cmds_project = [
            ("project <description>",   "Start automated project (plan→execute→review→iterate)"),
            ("project status",          "Show current project progress"),
            ("project stop",            "Stop running project workflow"),
        ]
        for cmd, desc in cmds_project:
            print(f"    {CYAN}{cmd:<32}{RESET} {desc}")

        print(f"\n  {BOLD}{YELLOW}── Live AI Chat ──{RESET}")
        cmds_chat = [
            ("chat <agent> <message>",   "Chat with a live AI (e.g., chat kimi explain async)"),
            ("discuss <topic> [rounds]",  "Multi-AI roundtable discussion"),
            ("connect <provider> [model]","Connect an API (openai/anthropic/ollama/gemini/kimi/opencode)"),
            ("disconnect <agent>",        "Disconnect a live API agent"),
            ("apis",                      "Show all connected APIs and stats"),
            ("keys",                      "Show detected API keys"),
        ]
        for cmd, desc in cmds_chat:
            print(f"    {CYAN}{cmd:<32}{RESET} {desc}")

        print(f"\n  {BOLD}{YELLOW}── Bridge & Agents ──{RESET}")
        cmds_bridge = [
            ("dashboard / d",               "Show full status dashboard"),
            ("agents / a",                   "List all agents (live + simulated)"),
            ("discover",                     "Run discovery scan"),
            ("add <ide>",                    "Add simulated agent (vscode/opencode/claude/zed/cursor)"),
            ("send <from> <to> <msg>",       "Send a message between agents"),
            ("demo",                         "Run the cross-IDE demo"),
            ("messages / m",                 "Show message history"),
        ]
        for cmd, desc in cmds_bridge:
            print(f"    {CYAN}{cmd:<32}{RESET} {desc}")

        print(f"\n  {BOLD}{YELLOW}── General ──{RESET}")
        cmds_gen = [
            ("clear",            "Clear screen"),
            ("help / h / ?",     "Show this help"),
            ("quit / q / exit",  "Stop everything"),
        ]
        for cmd, desc in cmds_gen:
            print(f"    {CYAN}{cmd:<32}{RESET} {desc}")

        print(f"\n  {BOLD}Examples:{RESET}")
        print(f"    {DIM}vakya>{RESET} project Build a REST API for todo app with FastAPI")
        print(f"    {DIM}vakya>{RESET} chat kimi Write a Python fibonacci function")
        print(f"    {DIM}vakya>{RESET} chat glm Review this approach for auth")
        print(f"    {DIM}vakya>{RESET} connect kimi"
              f"\n    {DIM}vakya>{RESET} connect opencode zai-coding-plan/glm-4.7")
        print(f"    {DIM}vakya>{RESET} discuss \"Best approach for microservices\" 3")

    # ─── Command Handler ─────────────────────────────────────────────────

    async def handle_command(self, line: str) -> bool:
        """Process a user command. Returns False to quit."""
        parts = line.strip().split(maxsplit=3)
        if not parts:
            return True
        cmd = parts[0].lower()

        # ── Quit ──
        if cmd in ("quit", "q", "exit"):
            return False

        # ── Help ──
        elif cmd in ("help", "h", "?"):
            self.show_help()

        # ── Dashboard / Status ──
        elif cmd in ("dashboard", "d", "status"):
            self.show_dashboard()

        # ── Project Workflow ──
        elif cmd == "project":
            if len(parts) < 2:
                warn("Usage: project <description> | project status | project stop")
                return True
            subcmd = parts[1].lower()
            if subcmd == "status":
                self.show_project_status()
            elif subcmd == "stop":
                if self.workflow:
                    self.workflow.stop()
                    ok("Project workflow stop requested.")
                else:
                    warn("No active project.")
            else:
                # Everything after 'project' is the description
                desc = line.strip()[len("project"):].strip().strip('"').strip("'")
                await self.run_project(desc)

        # ── Chat with live AI ──
        elif cmd == "chat":
            if len(parts) < 3:
                warn("Usage: chat <agent> <message>")
                print(f"  Agents: {', '.join(self._list_live_names())}")
                return True
            agent_name = parts[1]
            message = parts[2] if len(parts) == 3 else parts[2] + " " + parts[3] if len(parts) > 3 else parts[2]
            # Rejoin everything after agent name
            raw_msg = line.strip()
            idx = raw_msg.lower().find(agent_name.lower())
            if idx >= 0:
                message = raw_msg[idx + len(agent_name):].strip()
            await self.chat_with(agent_name, message)

        # ── Multi-AI Discussion ──
        elif cmd == "discuss":
            if len(parts) < 2:
                warn("Usage: discuss <topic> [rounds]")
                return True
            # Extract topic (may be in quotes)
            rest = line.strip()[len("discuss"):].strip()
            rounds = 2
            # Check if last word is a number
            last_parts = rest.rsplit(maxsplit=1)
            if len(last_parts) == 2 and last_parts[1].isdigit():
                rounds = int(last_parts[1])
                rest = last_parts[0]
            topic = rest.strip('"').strip("'")
            await self.discuss(topic, rounds)

        # ── Connect API ──
        elif cmd == "connect":
            if len(parts) < 2:
                warn("Usage: connect <provider> [model]")
                print(f"  Providers: openai, anthropic, ollama, gemini, kimi")
                return True
            await self._handle_connect(parts[1], parts[2] if len(parts) > 2 else "")

        # ── Disconnect API ──
        elif cmd == "disconnect":
            if len(parts) < 2:
                warn("Usage: disconnect <agent>")
                return True
            self._handle_disconnect(parts[1])

        # ── APIs Status ──
        elif cmd == "apis":
            self.show_apis()

        # ── Keys ──
        elif cmd == "keys":
            section("API Keys", "key")
            for provider, key in self._api_keys.items():
                masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
                color = PROVIDER_COLORS.get(provider, WHITE)
                status_line(provider.title(), f"{color}{masked}{RESET}")
            if not self._api_keys:
                warn("No API keys found in environment.")

        # ── Agents List ──
        elif cmd in ("agents", "a"):
            self._show_agents()

        # ── Discover ──
        elif cmd == "discover":
            agents = self.khoj.discover_agents(active_only=False, max_age_seconds=0)
            if not agents:
                warn("No agents discovered.")
            else:
                section(f"Discovered {len(agents)} Agent(s)", "search")
                for a in agents:
                    print(f"  {ICONS['plug']} {a.duta_name} in {a.environment.ide_name} "
                          f"via {a.transport}")

        # ── Add Simulated Agent ──
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
                duta = self.register_sim_agent(name, model, prov, itype, iname, skills=skills)
                ok(f"{name} registered from {iname} (id: {duta.id})")

        # ── Send Message ──
        elif cmd == "send" and len(parts) >= 4:
            await self._route_user_msg(parts[1], parts[2], parts[3], "vakya")

        elif cmd == "ask" and len(parts) >= 4:
            await self._route_user_msg(parts[1], parts[2], parts[3], "prasna")

        elif cmd == "task" and len(parts) >= 4:
            from_id = self._resolve_agent(parts[1])
            to_id = self._resolve_agent(parts[2])
            if from_id and to_id:
                task = Karya(presaka=from_id, prapaka=to_id,
                             title=parts[3], description=parts[3])
                await self.router.route(task)
            else:
                err("Agent not found. Use 'agents' to see IDs or names.")

        # ── Messages History ──
        elif cmd in ("messages", "m"):
            if not self.messages:
                warn("No messages yet.")
            else:
                section(f"Message History ({len(self.messages)})", "msg")
                for m in self.messages[-20:]:
                    print(f"  {DIM}{m['time'][:19]}{RESET} [{m['type']}] "
                          f"{m['from']} → {m['to']}: {m['text'][:60]}")

        # ── Demo ──
        elif cmd == "demo":
            await self.run_demo()

        # ── Clear ──
        elif cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            banner()

        else:
            warn(f"Unknown command: {cmd}. Type 'help' for commands.")

        return True

    # ─── Connect/Disconnect Handlers ─────────────────────────────────────

    async def _handle_connect(self, provider: str, model: str = ""):
        provider = provider.lower()
        valid = {"openai", "anthropic", "ollama", "gemini", "kimi", "opencode"}
        if provider not in valid:
            warn(f"Unknown provider: {provider}. Options: {', '.join(valid)}")
            return

        # Check for API key (not needed for ollama, kimi, opencode)
        key = ""
        if provider not in ("ollama", "kimi", "opencode"):
            env_map = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                       "gemini": "GOOGLE_API_KEY"}
            env_var = env_map.get(provider, "")
            key = self._api_keys.get(provider, "") or os.environ.get(env_var, "")
            if not key:
                print(f"  {ICONS['key']} Enter {provider.title()} API key: ", end="", flush=True)
                try:
                    key = await asyncio.get_event_loop().run_in_executor(None, input)
                    key = key.strip()
                except EOFError:
                    return
                if not key:
                    err("No API key provided.")
                    return
                self._api_keys[provider] = key

        agent = create_agent(provider, api_key=key, model=model)
        if not agent:
            err(f"Failed to create {provider} agent.")
            return

        print(f"  {ICONS['globe']} Connecting to {provider.title()} ({agent.duta.model})...", end=" ", flush=True)
        if await agent.connect():
            self._register_live_agent(agent)
            print(f"{GREEN}connected!{RESET}")
            ok(f"{agent.duta.name} is now live and ready to chat")
        else:
            print(f"{RED}failed{RESET}")
            err(f"Could not connect to {provider.title()}. Check your API key / network.")

    def _handle_disconnect(self, name: str):
        agent = self._resolve_live_agent(name)
        if not agent:
            err(f"No live agent matching '{name}'.")
            return
        if isinstance(agent, SelfAgent):
            warn("Can't disconnect yourself!")
            return
        agent.connected = False
        ok(f"{agent.duta.name} disconnected")

    # ─── Resolution Helpers ──────────────────────────────────────────────

    def _resolve_agent(self, name_or_id: str) -> str | None:
        name_lower = name_or_id.lower()
        for aid, (duta, env) in self.agents.items():
            if aid == name_or_id or aid.startswith(name_or_id):
                return aid
            if name_lower in duta.name.lower():
                return aid
            if name_lower in env.ide_name.lower():
                return aid
            if name_lower == duta.provider.lower():
                return aid
        return None

    def _resolve_live_agent(self, name: str) -> LiveAgent | None:
        name_lower = name.lower()
        for aid, agent in self.live_agents.items():
            if isinstance(agent, SelfAgent):
                continue
            # Match against name, provider, model (with and without tag)
            model_base = agent.duta.model.split(":")[0].lower()
            if name_lower in agent.duta.name.lower():
                return agent
            if name_lower in agent.duta.provider.lower():
                return agent
            if name_lower in agent.duta.model.lower():
                return agent
            if name_lower in model_base:
                return agent
            # Partial match: "kimi" matches "kimi-k2.5", "glm" matches "glm-4.7-flash"
            if model_base.startswith(name_lower):
                return agent
            if aid.startswith(name):
                return agent
        return None

    def _list_live_names(self) -> list[str]:
        names = []
        for a in self.live_agents.values():
            if a.connected and not isinstance(a, SelfAgent):
                model_short = a.duta.model.split(":")[0].replace(":latest", "")
                names.append(model_short)
        return names

    def _show_agents(self):
        if not self.agents:
            warn("No agents registered.")
            return

        section(f"All Agents ({len(self.agents)})", "agent")

        # Self first
        if self.self_agent:
            d = self.self_agent.duta
            e = self.self_agent.environment
            print(f"  {ICONS['self']} {BOLD}{d.name}{RESET} "
                  f"{DIM}(you){RESET} in {CYAN}{e.ide_name}{RESET} "
                  f"[{d.role.value}] {GREEN}● live{RESET}")

        # Live APIs
        for aid, agent in self.live_agents.items():
            if isinstance(agent, SelfAgent):
                continue
            d = agent.duta
            color = PROVIDER_COLORS.get(d.provider, WHITE)
            status = f"{GREEN}● live{RESET}" if agent.connected else f"{RED}● offline{RESET}"
            print(f"  {ICONS['api']} {color}{BOLD}{d.name}{RESET} "
                  f"{DIM}({d.model}){RESET} "
                  f"[{d.provider}] {status}")

        # Simulated
        for aid, (duta, env) in self.agents.items():
            if aid in self.live_agents:
                continue
            print(f"  {ICONS['agent']} {BOLD}{duta.name}{RESET} "
                  f"in {CYAN}{env.ide_name}{RESET} "
                  f"[{duta.role.value}] {DIM}simulated{RESET}")

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

    # ─── Demo ────────────────────────────────────────────────────────────

    async def run_demo(self):
        section("Cross-IDE Demo", "bolt")
        print(f"  Simulating 4 AI agents across 4 different IDEs...\n")

        claude_vscode = self.register_sim_agent(
            "Claude Sonnet", "claude-sonnet-4-20250514", "anthropic",
            IDEType.VSCODE, "VS Code", DutaRole.NETA,
            ["architecture", "code-generation", "review"],
        )
        ok("Claude Sonnet registered from VS Code")

        gpt_opencode = self.register_sim_agent(
            "GPT-4o", "gpt-4o", "openai",
            IDEType.OPENCODE, "OpenCode", DutaRole.KARTR,
            ["code-generation", "testing", "docs"],
        )
        ok("GPT-4o registered from OpenCode")

        claude_cc = self.register_sim_agent(
            "Claude Opus", "claude-opus-4-20250514", "anthropic",
            IDEType.CLAUDE_CODE, "Claude Code", DutaRole.SAMIKSHAKA,
            ["review", "security", "testing"],
        )
        ok("Claude Opus registered from Claude Code")

        llama_zed = self.register_sim_agent(
            "LLaMA 3.1", "llama-3.1-70b", "ollama",
            IDEType.ZED, "Zed", DutaRole.PARIKSAKA,
            ["testing", "benchmarking"],
        )
        ok("LLaMA 3.1 registered from Zed")

        print()
        section("Live Message Feed", "msg")
        print()

        task = Karya(presaka=claude_vscode.id, prapaka=gpt_opencode.id,
                     title="Write auth module tests", description="Write unit tests for authentication",
                     visaya="testing", priority="ucca")
        await self.router.route(task)
        await asyncio.sleep(0.3)

        report = Prativedana(presaka=gpt_opencode.id, prapaka=claude_vscode.id,
                             karya_id=task.id, sthiti="sampurna", pravrtti=1.0,
                             vivarana="15 tests written: login, signup, token refresh. Coverage 87%.")
        await self.router.route(report)
        await asyncio.sleep(0.3)

        review_q = Prasna(presaka=claude_cc.id, prapaka=gpt_opencode.id,
                          text="Tests look solid. Did you cover expired tokens and rate limiting?",
                          visaya="review")
        await self.router.route(review_q)
        await asyncio.sleep(0.3)

        answer = Uttara(presaka=gpt_opencode.id,
                        text="Yes — added 3 more tests for token expiry and 2 for rate limiting. Coverage now 94%.",
                        reply_to=review_q)
        await self.router.route(answer)
        await asyncio.sleep(0.3)

        benchmark = Uttara(presaka=llama_zed.id,
                           text="Benchmark complete: all 20 tests pass in 0.28s, zero memory leaks, CPU peak 12%.",
                           visaya="benchmarking")
        await self.router.route(benchmark)
        await asyncio.sleep(0.2)

        print()
        section("Demo Complete", "check")
        status_line("Messages exchanged", str(len(self.messages)))
        status_line("IDEs involved", "VS Code, OpenCode, Claude Code, Zed")

    # ─── Main Run Loop ───────────────────────────────────────────────────

    async def run(self, demo_mode: bool = False, auto_connect: bool = False):
        banner()

        # 1. Start bridge
        section("Starting Setu Bridge", "bridge")
        self.bridge.start()
        if self.bridge.running:
            ok(f"Setu bridge running on ws://localhost:{self.port}")
        else:
            err("Failed to start bridge")
            return

        # 2. Detect self
        self._detect_and_register_self()

        # 3. Detect API keys
        self._detect_api_keys()

        # 4. Auto-connect APIs
        if auto_connect or self._api_keys:
            await self._auto_connect_apis()

        # 5. Set up observer
        self.router.add_observer(self.observe)

        # 6. Run demo if requested
        if demo_mode:
            await self.run_demo()
            print()

        # 7. Interactive loop
        section("Interactive Control", "gear")
        live_count = sum(1 for a in self.live_agents.values()
                         if a.connected and not isinstance(a, SelfAgent))
        live_names = self._list_live_names()
        if live_count > 0:
            names_str = ", ".join(live_names[:3])
            print(f"  {GREEN}{live_count} live AI(s) ready:{RESET} {names_str}")
            print(f"  Try: {CYAN}chat {live_names[0]} hello{RESET} or "
                  f"{CYAN}project Build a todo app{RESET}")
        else:
            print(f"  No live AIs yet. Use {CYAN}connect ollama{RESET} or {CYAN}connect openai{RESET}")
        print(f"  Type {CYAN}help{RESET} for all commands, {CYAN}quit{RESET} to exit.\n")

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
        for agent in self.live_agents.values():
            if not isinstance(agent, SelfAgent):
                await agent.disconnect()
        self.bridge.stop()
        ok("All stopped. नमस्ते! 🙏")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Vākya Control Center — Unified AI Orchestrator",
    )
    parser.add_argument("--port", type=int, default=8765, help="Bridge port (default: 8765)")
    parser.add_argument("--demo", action="store_true", help="Auto-run the cross-IDE demo")
    parser.add_argument("--auto", action="store_true", help="Auto-connect all available APIs")
    args = parser.parse_args()

    cc = ControlCenter(port=args.port)
    asyncio.run(cc.run(demo_mode=args.demo, auto_connect=args.auto))


if __name__ == "__main__":
    main()
