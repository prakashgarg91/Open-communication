"""
Example: Multi-Model Collaboration
====================================

Demonstrates a realistic scenario where multiple AI models
collaborate on a complex project through the Vākya protocol.

Scenario: Building a web API
    - Claude (नेता/Leader): Coordinates the project
    - GPT-4o (कर्तृ/Worker): Writes the backend code
    - GLM-4 (कर्तृ/Worker): Writes data processing
    - Gemini (समीक्षक/Reviewer): Reviews all code
"""

import asyncio
from vakya import (
    VakyaProtocol,
    Vakya,
    Prasna,
    Uttara,
    Nirnaya,
    Svikriti,
    Duta,
    DutaRole,
    SabhaRouter,
    KaryaManager,
)
from vakya.message import Karya as KaryaMsg, Prativedana, MessageType
from vakya.task import KaryaPriority


async def main():
    print("═══ Vākya: Multi-Model Collaboration ═══\n")
    print("Scenario: Building a REST API together\n")

    # ─── Setup Team ──────────────────────────────────────────────────
    leader = Duta(
        id="claude-lead",
        name="Claude",
        model="claude-opus-4.6",
        provider="anthropic",
        role=DutaRole.NETA,  # Leader
        skills=["architecture", "python", "project-management"],
    )

    backend_dev = Duta(
        id="gpt-backend",
        name="GPT-4o",
        model="gpt-4o",
        provider="openai",
        role=DutaRole.KARTR,
        skills=["python", "fastapi", "databases", "code-generation"],
    )

    data_dev = Duta(
        id="glm-data",
        name="GLM-4",
        model="glm-4",
        provider="zhipu",
        role=DutaRole.KARTR,
        skills=["python", "data-processing", "pandas", "code-generation"],
    )

    reviewer = Duta(
        id="gemini-review",
        name="Gemini",
        model="gemini-2.0-flash",
        provider="google",
        role=DutaRole.SAMIKSHAKA,
        skills=["code-review", "security-analysis", "python", "testing"],
    )

    # Router with human observation
    router = SabhaRouter(name="API Project")
    for duta in [leader, backend_dev, data_dev, reviewer]:
        router.register_duta(duta)

    # Track all messages for display
    all_messages: list[Vakya] = []

    async def track(msg: Vakya, ch: str):
        all_messages.append(msg)
        icon = {"vakya": "💬", "prasna": "❓", "uttara": "✅", "karya": "📋",
                "nirnaya": "⚖️", "svikriti": "👍", "prativedana": "📊"}.get(
            msg.prakara.value, "💬"
        )
        text = msg.sarira.get("text", msg.sarira.get("title", ""))[:80]
        print(f"  {icon} {msg.presaka} → {msg.prapaka or '*'}: {text}")

    router.add_observer(track)

    # ─── Phase 1: Planning ───────────────────────────────────────────
    print("── Phase 1: Planning ──\n")

    # Leader proposes architecture
    plan = Vakya(
        presaka="claude-lead",
        prakara=MessageType.NIRNAYA,
        visaya="architecture",
        sarira={
            "text": "Architecture decision: We'll build a FastAPI REST API with SQLite. "
                    "GPT handles routes & models, GLM handles data processing pipeline, "
                    "Gemini reviews everything. Let's use Pydantic for validation.",
            "components": ["api-routes", "data-models", "data-pipeline", "tests"],
        },
    )
    await router.route(plan)

    # Team acknowledges
    for duta_id in ["gpt-backend", "glm-data", "gemini-review"]:
        ack = Svikriti(presaka=duta_id, reply_to=plan, text="Acknowledged, ready to start.")
        await router.route(ack)

    # ─── Phase 2: Task Distribution ──────────────────────────────────
    print("\n── Phase 2: Task Distribution ──\n")

    manager = KaryaManager()

    task_api = manager.create(
        title="Build API routes & models",
        description="Create FastAPI routes for CRUD operations with Pydantic models",
        presaka="claude-lead",
        prapaka="gpt-backend",
        priority=KaryaPriority.UCCA,
        skills_needed=["python", "fastapi"],
    )

    task_data = manager.create(
        title="Build data processing pipeline",
        description="Create data ingestion and transformation pipeline with pandas",
        presaka="claude-lead",
        prapaka="glm-data",
        priority=KaryaPriority.UCCA,
        skills_needed=["python", "data-processing"],
    )

    # Send task assignment messages
    for task, target in [(task_api, "gpt-backend"), (task_data, "glm-data")]:
        msg = KaryaMsg(
            presaka="claude-lead",
            title=task.title,
            description=task.description,
            prapaka=target,
            priority=task.prathama.value,
            skills=task.skills_needed,
        )
        await router.route(msg)

    # ─── Phase 3: Execution & Progress ───────────────────────────────
    print("\n── Phase 3: Execution ──\n")

    # GPT reports progress
    progress1 = Prativedana(
        presaka="gpt-backend",
        karya_id=task_api.id,
        sthiti="sakriya",
        pravrtti=0.5,
        vivarana="API routes for users and items complete. Working on auth.",
        prapaka="claude-lead",
    )
    await router.route(progress1)

    # GLM reports progress
    progress2 = Prativedana(
        presaka="glm-data",
        karya_id=task_data.id,
        sthiti="sakriya",
        pravrtti=0.6,
        vivarana="Data ingestion pipeline complete. Working on transformations.",
        prapaka="claude-lead",
    )
    await router.route(progress2)

    # GPT asks GLM a question (AI-to-AI collaboration!)
    collab_q = Prasna(
        presaka="gpt-backend",
        prapaka="glm-data",
        text="What format will your data pipeline output? I need to design the API response schema.",
        visaya="data-format",
    )
    await router.route(collab_q)

    # GLM responds
    collab_a = Uttara(
        presaka="glm-data",
        text='Output will be JSON with schema: {"items": [{"id": int, "name": str, '
             '"processed_at": datetime, "metrics": dict}]}. I can add any fields you need.',
        reply_to=collab_q,
    )
    await router.route(collab_a)

    # Both complete
    manager.complete(task_api.id, result={"endpoints": 8, "models": 4})
    manager.complete(task_data.id, result={"pipelines": 3, "transformations": 12})

    for task_id, name in [(task_api.id, "gpt-backend"), (task_data.id, "glm-data")]:
        done = Prativedana(
            presaka=name,
            karya_id=task_id,
            sthiti="sampurna",
            pravrtti=1.0,
            vivarana="Task complete!",
            prapaka="claude-lead",
        )
        await router.route(done)

    # ─── Phase 4: Review ─────────────────────────────────────────────
    print("\n── Phase 4: Review ──\n")

    review_task = manager.create(
        title="Security & code review",
        description="Review all code for security issues, best practices, and correctness",
        presaka="claude-lead",
        prapaka="gemini-review",
        priority=KaryaPriority.UCCA,
        skills_needed=["code-review", "security-analysis"],
    )

    review_msg = KaryaMsg(
        presaka="claude-lead",
        title=review_task.title,
        description=review_task.description,
        prapaka="gemini-review",
    )
    await router.route(review_msg)

    # Gemini provides review
    review_result = Uttara(
        presaka="gemini-review",
        text="Code review complete. Findings: 1) Add rate limiting to API routes. "
             "2) Sanitize data pipeline inputs. 3) Add request validation middleware. "
             "Overall quality: Good. Recommend proceeding after fixes.",
        reply_to=review_msg,
        findings=3,
        approved_with_changes=True,
    )
    await router.route(review_result)

    # ─── Phase 5: Final Decision ─────────────────────────────────────
    print("\n── Phase 5: Conclusion ──\n")

    conclusion = Nirnaya(
        presaka="claude-lead",
        decision="Project approved for deployment after applying Gemini's security recommendations.",
        reasoning="All tasks completed successfully. Code review passed with minor fixes needed. "
                  "Team collaboration was excellent.",
        visaya="project-status",
    )
    await router.route(conclusion)

    # ─── Summary ─────────────────────────────────────────────────────
    print(f"\n── Summary ──")
    print(f"\n  Total messages exchanged: {len(all_messages)}")
    print(f"  Tasks completed: {len(manager.list_tasks(sthiti=KaryaStatus.SAMPURNA))}"
          if hasattr(KaryaStatus, 'SAMPURNA') else "")
    print(f"  {router}")

    # Show wire format of the final decision
    print("\n── Wire Format (final decision) ──\n")
    protocol = VakyaProtocol()
    print(protocol.encode(conclusion))

    print("\n═══ Collaboration Complete ═══")


# Import at end to avoid circular
from vakya.task import KaryaStatus

if __name__ == "__main__":
    asyncio.run(main())
