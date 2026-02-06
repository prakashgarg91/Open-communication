"""
Full end-to-end workflow test — real AI models complete a project.
Uses Kimi CLI + Ollama (GLM-4.7-flash, Kimi-K2.5) to:
  1. Plan a project (leader: kimi-k2.5:cloud via Ollama)
  2. Execute tasks (workers: glm-4.7-flash, kimi CLI)
  3. Review & iterate
  4. Compile final output
"""
import asyncio
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from vakya_control import ControlCenter, section, ok, err, warn, status_line
from vakya_control import BOLD, RESET, GREEN, CYAN, YELLOW, RED, DIM, MAGENTA
from vakya.live import SelfAgent, KimiCLIAgent, discover_cli_agents, discover_ollama_models
from vakya.hierarchy import WorkflowEngine, ProjectStatus, TaskStatus


async def main():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗
║  Vākya Full Workflow Test                                    ║
║  Real AIs → Real Planning → Real Coding → Real Review        ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

    cc = ControlCenter(port=8767)
    t_start = time.monotonic()

    # ── 1. Start bridge ──
    section("Phase 0: Setup", "bridge")
    cc.bridge.start()
    assert cc.bridge.running, "Bridge failed"
    ok("Bridge running on port 8767")

    # ── 2. Self detection ──
    cc._detect_and_register_self()
    assert cc.self_agent is not None
    ok(f"Self: {cc.self_agent.duta.name}")

    # ── 3. Discover and connect all agents ──
    section("Phase 0: Connecting AI Agents", "api")

    # Ollama models
    ollama_models = await discover_ollama_models()
    print(f"  Ollama models available: {ollama_models}")

    connected_agents = []

    from vakya.live import OllamaAgent
    for model_name in ollama_models:
        agent = OllamaAgent(model=model_name)
        if await agent.connect():
            cc._register_live_agent(agent)
            connected_agents.append(agent)
            ok(f"Ollama: {agent.duta.name} ({agent.duta.model})")

    # Kimi CLI
    cli_agents = discover_cli_agents()
    print(f"  CLI agents found: {[name for name, _ in cli_agents]}")

    kimi_agent = None
    for provider, path in cli_agents:
        if provider == "kimi":
            from vakya.live import create_agent
            agent = create_agent("kimi")
            if agent and await agent.connect():
                cc._register_live_agent(agent)
                connected_agents.append(agent)
                kimi_agent = agent
                ok(f"Kimi CLI: {agent.duta.name}")
            break

    # Verify we have at least 2 agents
    workers = [a for a in cc.live_agents.values()
               if a.connected and not isinstance(a, SelfAgent)]
    print(f"\n  {BOLD}Active Workers: {len(workers)}{RESET}")
    for w in workers:
        print(f"    {GREEN}●{RESET} {w.duta.name} [{w.duta.provider}] "
              f"skills: {', '.join(w.duta.skills)}")

    if len(workers) < 2:
        err(f"Need at least 2 workers, got {len(workers)}. Aborting.")
        cc.bridge.stop()
        return

    # ── 4. Pick leader (prefer kimi-k2.5:cloud for planning) ──
    section("Phase 0: Selecting Leader", "brain")
    leader = workers[0]
    for w in workers:
        if ":cloud" in w.duta.model:
            leader = w
            break
        if isinstance(w, KimiCLIAgent):
            leader = w  # Kimi CLI is smart, good for planning

    status_line("Leader (Planner)", leader.duta.name, MAGENTA)
    status_line("Workers", ", ".join(w.duta.name for w in workers), CYAN)

    # ── 5. Run project ──
    section("Phase 1-5: Running Full Project Workflow", "bolt")
    print(f"  This will: Plan → Allocate → Execute → Review → Iterate → Compile\n")

    project_desc = (
        "Create a Python module called 'mathtools.py' with these functions:\n"
        "1. fibonacci(n) - Return the nth Fibonacci number\n"
        "2. is_prime(n) - Check if n is prime\n"
        "3. gcd(a, b) - Greatest common divisor\n"
        "4. factorial(n) - Factorial with error handling\n"
        "Include docstrings, type hints, and edge case handling."
    )

    async def workflow_event(event: str, data: dict):
        """Pretty-print workflow events."""
        ts = time.strftime("%H:%M:%S")
        if event == "phase_start":
            phase = data.get("phase", "?")
            print(f"\n  {DIM}{ts}{RESET} {BOLD}═══ {phase} ═══{RESET}")
            if "description" in data:
                print(f"  {DIM}{data['description'][:80]}{RESET}")

        elif event == "plan_ready":
            ok(f"Plan: {data['task_count']} tasks")
            for tid, title in data.get("tasks", []):
                print(f"    {CYAN}{tid}.{RESET} {title}")

        elif event == "plan_failed":
            err(f"Planning failed: {data.get('raw', '?')[:200]}")

        elif event == "task_start":
            worker = data.get("worker", "?")
            title = data.get("title", "?")
            attempt = data.get("attempt", 1)
            att_str = f" (attempt {attempt})" if attempt > 1 else ""
            print(f"\n  {DIM}{ts}{RESET} {YELLOW}▶{RESET} Task {data.get('task_id','?')}: {title}")
            print(f"           → {BOLD}{worker}{RESET}{att_str}")

        elif event == "task_done":
            elapsed = data.get("time", 0)
            worker = data.get("worker", "?")
            preview = data.get("result_preview", "")[:120].replace("\n", " ")
            print(f"  {DIM}{ts}{RESET} {GREEN}✓{RESET} {worker} done ({elapsed:.1f}s)")
            if preview:
                print(f"           {DIM}{preview}...{RESET}")

        elif event == "review_start":
            print(f"  {DIM}{ts}{RESET} 👁 Reviewing task {data.get('task_id', '?')}...",
                  end=" ", flush=True)

        elif event == "review_done":
            approved = data.get("approved", False)
            score = data.get("score", "?")
            if approved:
                print(f"{GREEN}approved{RESET} (score: {score}/10)")
            else:
                feedback = data.get("feedback", "")[:80]
                print(f"{RED}needs revision{RESET} (score: {score}/10)")
                if feedback:
                    print(f"           {DIM}Feedback: {feedback}{RESET}")

        elif event == "task_revision":
            print(f"  {DIM}{ts}{RESET} {YELLOW}↻{RESET} Revising task {data.get('task_id','?')}")

        elif event == "task_max_attempts":
            warn(f"Task {data.get('task_id','?')} max attempts reached")

        elif event == "project_done":
            done = data.get("completed", 0)
            total = data.get("total_tasks", 0)
            elapsed = data.get("total_time", 0)
            tokens = data.get("total_tokens", 0)
            print()
            ok(f"Project complete: {done}/{total} tasks in {elapsed:.1f}s, {tokens} tokens")

    engine = WorkflowEngine(planner=leader, workers=workers, on_event=workflow_event)
    result = await engine.run(project_desc)

    # ── 6. Results ──
    total_time = time.monotonic() - t_start

    section("Results Summary", "check")
    status_line("Status", result.status.value, GREEN if result.status == ProjectStatus.DONE else RED)
    status_line("Total Tasks", str(len(result.tasks)))
    status_line("Completed", str(sum(1 for t in result.tasks if t.status == TaskStatus.DONE)))
    status_line("Total Time", f"{total_time:.1f}s")
    status_line("Total Tokens", str(result.total_tokens))

    print(f"\n  {BOLD}Task Breakdown:{RESET}")
    for t in result.tasks:
        icon = {
            TaskStatus.DONE: f"{GREEN}✓{RESET}",
            TaskStatus.RUNNING: f"{YELLOW}▶{RESET}",
            TaskStatus.FAILED: f"{RED}✗{RESET}",
            TaskStatus.REVISION: f"{YELLOW}↻{RESET}",
        }.get(t.status, f"{DIM}○{RESET}")
        print(f"    {icon} {t.id}. {t.title} → {t.assigned_to} "
              f"({t.attempts} attempt(s), {t.time_taken:.1f}s)")

    if result.final_output:
        section("Final Compiled Output", "star")
        lines = result.final_output.split("\n")
        for i, line in enumerate(lines[:60]):
            print(f"  {line[:90]}")
        if len(lines) > 60:
            print(f"  {DIM}... ({len(lines) - 60} more lines){RESET}")

    # ── 7. Cleanup ──
    section("Cleanup", "plug")
    for agent in cc.live_agents.values():
        if not isinstance(agent, SelfAgent):
            await agent.disconnect()
    cc.bridge.stop()

    if result.status == ProjectStatus.DONE:
        ok(f"ALL TESTS PASSED — Full workflow completed in {total_time:.1f}s")
    else:
        err(f"Workflow ended with status: {result.status.value}")

    return result.status == ProjectStatus.DONE


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
