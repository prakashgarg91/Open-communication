"""Quick test script for vakya_control.py — runs commands non-interactively."""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Force UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from vakya_control import ControlCenter, banner, section, ok, err, warn

async def test():
    cc = ControlCenter(port=8766)  # Use different port to avoid conflicts
    banner()

    # 1. Start bridge
    section("Starting Setu Bridge", "bridge")
    cc.bridge.start()
    assert cc.bridge.running, "Bridge failed to start"
    ok("Bridge running")

    # 2. Self detection
    cc._detect_and_register_self()
    assert cc.self_agent is not None, "Self not detected"
    assert "VS Code" in cc.self_agent.environment.ide_name, "IDE not detected"
    ok(f"Self: {cc.self_agent.duta.name} in {cc.self_agent.environment.ide_name}")

    # 3. API keys
    cc._detect_api_keys()

    # 4. Auto-connect ALL Ollama models
    await cc._auto_connect_apis()
    live = [a for a in cc.live_agents.values() if not isinstance(a, type(cc.self_agent))]
    ok(f"Connected {len(live)} live agents")
    for a in live:
        ok(f"  {a.duta.name} ({a.duta.model}) — {'connected' if a.connected else 'DISCONNECTED'}")

    # 5. Test chat resolution
    section("Testing Agent Resolution", "search")
    for name in ["kimi", "glm", "lfm", "ollama"]:
        agent = cc._resolve_live_agent(name)
        if agent:
            ok(f"'{name}' → {agent.duta.name}")
        else:
            warn(f"'{name}' → not found")

    # 6. Test actual chat with GLM (local, should be fast)
    section("Testing Live Chat", "chat")
    print("  Chatting with GLM 4.7...")
    result = await cc.chat_with("glm", "Say hello in exactly 5 words. No more.")
    assert result is not None, "Chat returned None"
    ok(f"GLM replied: {result[:80]}...")

    # 7. Test chat with Kimi (cloud)
    print("\n  Chatting with Kimi K2.5...")
    result2 = await cc.chat_with("kimi", "Say hello in exactly 5 words. No more.")
    assert result2 is not None, "Kimi chat returned None"
    ok(f"Kimi replied: {result2[:80]}...")

    # 8. Test project workflow (just planning phase, to save time)
    section("Testing Project Planning", "brain")
    from vakya.hierarchy import WorkflowEngine
    from vakya.live import SelfAgent

    workers = [a for a in cc.live_agents.values()
               if a.connected and not isinstance(a, SelfAgent)]
    
    planner = workers[0]
    for w in workers:
        if ":cloud" in w.duta.model:
            planner = w
            break

    print(f"  Planner: {planner.duta.name}")
    print(f"  Workers: {len(workers)}")

    async def log_event(event, data):
        print(f"    [{event}] {str(data)[:100]}")

    engine = WorkflowEngine(planner=planner, workers=workers, on_event=log_event)
    plan = await engine.plan("Create a simple Python calculator with add, subtract, multiply, divide functions")
    
    ok(f"Plan created: {len(plan.tasks)} tasks")
    for t in plan.tasks:
        ok(f"  {t.id}. {t.title}")

    # 9. Run full project (execute + review)
    if plan.tasks:
        section("Executing Project Tasks", "bolt")
        result = await engine.execute(plan)
        ok(f"Project status: {result.status.value}")
        ok(f"Tasks done: {sum(1 for t in result.tasks if t.status.value == 'done')}/{len(result.tasks)}")
        if result.final_output:
            print(f"\n  Final output preview:")
            for line in result.final_output.split("\n")[:10]:
                print(f"  | {line[:80]}")

    # Cleanup
    section("Cleanup", "plug")
    for agent in cc.live_agents.values():
        if not isinstance(agent, SelfAgent):
            await agent.disconnect()
    cc.bridge.stop()
    ok("All tests passed!")

if __name__ == "__main__":
    asyncio.run(test())
