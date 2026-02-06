"""
Full project workflow test using Kimi CLI as the coding agent.
Kimi CLI is a real coding agent (like Claude Code) — it can create files,
write code, run tests, all from the command line.

Workflow:
  1. Kimi-K2.5 (via Ollama) plans the project
  2. Kimi CLI executes each task (creates real files)
  3. Kimi-K2.5 reviews the output
  4. Iterate until done
"""
import asyncio
import sys
import os
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from vakya.live import (
    LiveAgent, SelfAgent, KimiCLIAgent, OllamaAgent,
    discover_cli_agents, discover_ollama_models, create_agent,
)
from vakya.hierarchy import WorkflowEngine, ProjectStatus, TaskStatus

# Colors
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
os.system("")


def section(title):
    print(f"\n{BOLD}{BLUE}{'─' * 60}{RESET}")
    print(f"  {BOLD}{WHITE}{title}{RESET}")
    print(f"{BLUE}{'─' * 60}{RESET}")


def ok(msg):
    print(f"  ✅ {GREEN}{msg}{RESET}")


def err(msg):
    print(f"  ❌ {RED}{msg}{RESET}")


def warn(msg):
    print(f"  ⚠️ {YELLOW}{msg}{RESET}")


async def main():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║  Vākya Workflow: Kimi CLI as Coding Agent                    ║
║  Plan (kimi-k2.5) → Code (kimi CLI) → Review → Ship         ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    t_start = time.monotonic()

    # Create a temp workspace for the project
    work_dir = Path(__file__).parent / "_test_project"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir()
    print(f"  Workspace: {work_dir}")

    # ── 1. Connect agents ──
    section("Connecting Agents")

    # Kimi CLI as the worker
    kimi_cli = KimiCLIAgent(work_dir=str(work_dir))
    if await kimi_cli.connect():
        ok(f"Kimi CLI: {kimi_cli.duta.name}")
    else:
        err("Kimi CLI not available. Install: pip install kimi-cli")
        return False

    # Kimi K2.5 via Ollama as the planner/reviewer
    planner = OllamaAgent(model="kimi-k2.5")
    if await planner.connect():
        ok(f"Planner: {planner.duta.name} ({planner.duta.model})")
    else:
        # Fallback: use kimi CLI for everything
        warn("Ollama kimi-k2.5 not available, using Kimi CLI for planning too")
        planner = kimi_cli

    workers = [kimi_cli]

    # Optionally add GLM as a second worker if available
    glm = OllamaAgent(model="glm-4.7-flash")
    if await glm.connect():
        workers.append(glm)
        ok(f"Extra worker: {glm.duta.name} ({glm.duta.model})")

    print(f"\n  {BOLD}Leader:{RESET}  {MAGENTA}{planner.duta.name}{RESET} (plans & reviews)")
    print(f"  {BOLD}Workers:{RESET} {CYAN}{', '.join(w.duta.name for w in workers)}{RESET} (execute tasks)")

    # ── 2. Define project ──
    section("Project Definition")
    project_desc = (
        "Create a Python module 'mathtools.py' in the current directory with:\n"
        "1. fibonacci(n: int) -> int  - nth Fibonacci number (handle n<0)\n"
        "2. is_prime(n: int) -> bool  - primality check (handle n<2)\n"
        "3. gcd(a: int, b: int) -> int - greatest common divisor (Euclidean)\n"
        "4. factorial(n: int) -> int  - factorial with ValueError for negative\n"
        "All functions must have docstrings and type hints.\n"
        "Then create 'test_mathtools.py' with at least 10 pytest tests covering edge cases."
    )
    print(f"  {project_desc}")

    # ── 3. Run workflow ──
    section("Running Workflow (Plan → Execute → Review → Compile)")

    events_log = []

    async def on_event(event: str, data: dict):
        ts = time.strftime("%H:%M:%S")
        events_log.append((event, data))

        if event == "phase_start":
            phase = data.get("phase", "?")
            print(f"\n  {DIM}{ts}{RESET} {BOLD}═══ {phase} ═══{RESET}")

        elif event == "plan_ready":
            ok(f"Plan: {data['task_count']} tasks")
            for tid, title in data.get("tasks", []):
                print(f"    {CYAN}{tid}.{RESET} {title}")

        elif event == "plan_failed":
            err(f"Planning failed: {data.get('raw', '')[:200]}")

        elif event == "task_start":
            print(f"\n  {DIM}{ts}{RESET} {YELLOW}▶{RESET} Task {data.get('task_id','?')}: "
                  f"{data.get('title','?')}")
            att = data.get("attempt", 1)
            print(f"           → {BOLD}{data.get('worker','?')}{RESET}"
                  + (f" (attempt {att})" if att > 1 else ""))

        elif event == "task_done":
            elapsed = data.get("time", 0)
            preview = data.get("result_preview", "")[:150].replace("\n", " ")
            print(f"  {DIM}{ts}{RESET} {GREEN}✓{RESET} Done ({elapsed:.1f}s)")
            if preview:
                print(f"           {DIM}{preview}...{RESET}")

        elif event == "review_start":
            print(f"  {DIM}{ts}{RESET} 👁 Reviewing...", end=" ", flush=True)

        elif event == "review_done":
            approved = data.get("approved", False)
            score = data.get("score", "?")
            fb = data.get("feedback", "")[:80]
            if approved:
                print(f"{GREEN}approved{RESET} ({score}/10)")
            else:
                print(f"{RED}revision needed{RESET} ({score}/10) — {fb}")

        elif event == "task_revision":
            print(f"  {DIM}{ts}{RESET} {YELLOW}↻{RESET} Revising task {data.get('task_id','?')}")

        elif event == "project_done":
            ok(f"Complete: {data.get('completed',0)}/{data.get('total_tasks',0)} tasks, "
               f"{data.get('total_time',0):.1f}s, {data.get('total_tokens',0)} tokens")

    engine = WorkflowEngine(planner=planner, workers=workers, on_event=on_event)
    result = await engine.run(project_desc)

    # ── 4. Results ──
    total_time = time.monotonic() - t_start

    section("Results")
    status_color = GREEN if result.status == ProjectStatus.DONE else RED
    print(f"  Status: {status_color}{BOLD}{result.status.value}{RESET}")
    print(f"  Time:   {total_time:.1f}s")
    print(f"  Tokens: {result.total_tokens}")

    print(f"\n  {BOLD}Tasks:{RESET}")
    for t in result.tasks:
        icon = "✓" if t.status == TaskStatus.DONE else "✗"
        color = GREEN if t.status == TaskStatus.DONE else RED
        print(f"    {color}{icon}{RESET} {t.id}. {t.title} → {t.assigned_to} "
              f"({t.attempts}x, {t.time_taken:.1f}s)")

    # Check what files were actually created
    section("Files Created")
    created_files = list(work_dir.glob("*.py"))
    if created_files:
        for f in created_files:
            size = f.stat().st_size
            print(f"    {GREEN}●{RESET} {f.name} ({size} bytes)")
            # Show first few lines
            content = f.read_text(encoding="utf-8", errors="replace")
            for line in content.split("\n")[:5]:
                print(f"      {DIM}{line[:80]}{RESET}")
            if content.count("\n") > 5:
                print(f"      {DIM}... ({content.count(chr(10))} total lines){RESET}")
    else:
        warn("No .py files created in workspace")

    # Show final compiled output
    if result.final_output:
        section("Final Compiled Output (first 40 lines)")
        for i, line in enumerate(result.final_output.split("\n")[:40]):
            print(f"  {line[:90]}")

    # Cleanup
    for agent in [kimi_cli, planner, glm]:
        await agent.disconnect()

    if result.status == ProjectStatus.DONE:
        ok(f"WORKFLOW COMPLETE — {total_time:.1f}s total")
        return True
    else:
        err(f"Workflow ended: {result.status.value}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
