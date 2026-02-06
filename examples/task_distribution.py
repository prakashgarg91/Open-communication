"""
Example: Task Distribution Across Multiple AIs
================================================

Demonstrates the Kārya (task) system:
    - Creating tasks with skill requirements
    - Auto-assigning tasks to capable AIs
    - Progress tracking and completion
    - Task dependencies
"""

import asyncio
from vakya import (
    Duta,
    DutaRole,
    SabhaRouter,
    KaryaManager,
    KaryaStatus,
)
from vakya.task import KaryaPriority


async def main():
    print("═══ Vākya Example: Task Distribution ═══\n")

    # ─── 1. Create a Team of AIs ─────────────────────────────────────
    team = [
        Duta(
            id="claude-1",
            name="Claude",
            model="claude-opus-4.6",
            provider="anthropic",
            role=DutaRole.KARTR,
            skills=["python", "code-generation", "testing", "writing"],
        ),
        Duta(
            id="gpt-1",
            name="GPT-4o",
            model="gpt-4o",
            provider="openai",
            role=DutaRole.SAMIKSHAKA,  # Reviewer
            skills=["code-review", "python", "security-analysis"],
        ),
        Duta(
            id="glm-1",
            name="GLM-4",
            model="glm-4",
            provider="zhipu",
            role=DutaRole.KARTR,
            skills=["python", "data-analysis", "chinese-nlp"],
        ),
        Duta(
            id="gemini-1",
            name="Gemini",
            model="gemini-2.0-flash",
            provider="google",
            role=DutaRole.PARIKSAKA,  # Tester
            skills=["testing", "python", "documentation"],
        ),
    ]

    # Set up router
    router = SabhaRouter(name="Project Team")
    for duta in team:
        router.register_duta(duta)
        print(f"  Registered: {duta}")

    # ─── 2. Create Task Manager ──────────────────────────────────────
    manager = KaryaManager()

    # ─── 3. Create Tasks with Dependencies ───────────────────────────
    print("\n─── Creating Tasks ───\n")

    # Task 1: Write the code
    task1 = manager.create(
        title="Implement sorting algorithm",
        description="Write an efficient merge sort in Python with type hints",
        presaka="coordinator",
        priority=KaryaPriority.UCCA,
        skills_needed=["python", "code-generation"],
    )
    print(f"  📋 {task1.title} [{task1.id}]")

    # Task 2: Review the code (depends on task 1)
    task2 = manager.create(
        title="Review sorting implementation",
        description="Review the merge sort for correctness, edge cases, and performance",
        presaka="coordinator",
        priority=KaryaPriority.UCCA,
        skills_needed=["code-review", "python"],
        dependencies=[task1.id],
    )
    print(f"  📋 {task2.title} [{task2.id}] (depends on task 1)")

    # Task 3: Write tests (depends on task 1)
    task3 = manager.create(
        title="Write unit tests",
        description="Write comprehensive pytest tests for the sorting algorithm",
        presaka="coordinator",
        priority=KaryaPriority.MADHYAMA,
        skills_needed=["testing", "python"],
        dependencies=[task1.id],
    )
    print(f"  📋 {task3.title} [{task3.id}] (depends on task 1)")

    # Task 4: Write documentation (depends on task 2)
    task4 = manager.create(
        title="Write documentation",
        description="Write API documentation and usage examples",
        presaka="coordinator",
        priority=KaryaPriority.NIMNA,
        skills_needed=["writing", "python"],
        dependencies=[task2.id],
    )
    print(f"  📋 {task4.title} [{task4.id}] (depends on task 2)")

    # ─── 4. Auto-assign Tasks ────────────────────────────────────────
    print("\n─── Auto-assigning Tasks ───\n")

    # Only task 1 is unblocked, the rest depend on it
    assigned = manager.auto_assign(task1.id, team)
    if assigned:
        print(f"  ✅ '{task1.title}' → {assigned.name} ({assigned.model})")

    # Tasks 2, 3 are blocked
    print(f"  🚫 '{task2.title}' — blocked (dependency)")
    print(f"  🚫 '{task3.title}' — blocked (dependency)")
    print(f"  🚫 '{task4.title}' — blocked (dependency)")

    # ─── 5. Simulate Task Completion ─────────────────────────────────
    print("\n─── Task Execution ───\n")

    # Task 1: Progress updates
    manager.update_progress(task1.id, 0.3, "Algorithm structure defined")
    print(f"  📊 {task1.title}: 30%")

    manager.update_progress(task1.id, 0.7, "Core implementation done")
    print(f"  📊 {task1.title}: 70%")

    manager.complete(task1.id, result={
        "code": "def merge_sort(arr): ...",
        "lines": 45,
        "complexity": "O(n log n)",
    })
    print(f"  ✅ {task1.title}: COMPLETE")

    # Now tasks 2 and 3 are unblocked!
    task2_item = manager.get(task2.id)
    task3_item = manager.get(task3.id)
    print(f"\n  🔓 '{task2.title}' — unblocked! (status: {task2_item.sthiti.value})")
    print(f"  🔓 '{task3.title}' — unblocked! (status: {task3_item.sthiti.value})")

    # Auto-assign unblocked tasks
    assigned2 = manager.auto_assign(task2.id, team)
    assigned3 = manager.auto_assign(task3.id, team)
    if assigned2:
        print(f"  ✅ '{task2.title}' → {assigned2.name}")
    if assigned3:
        print(f"  ✅ '{task3.title}' → {assigned3.name}")

    # Complete remaining tasks
    manager.complete(task2.id, result={"approved": True, "comments": 3})
    manager.complete(task3.id, result={"tests_passed": 12, "coverage": "95%"})
    print(f"\n  ✅ {task2.title}: COMPLETE")
    print(f"  ✅ {task3.title}: COMPLETE")

    # Task 4 is now unblocked
    assigned4 = manager.auto_assign(task4.id, team)
    if assigned4:
        print(f"  ✅ '{task4.title}' → {assigned4.name}")
    manager.complete(task4.id, result={"pages": 3})
    print(f"  ✅ {task4.title}: COMPLETE")

    # ─── 6. Summary ──────────────────────────────────────────────────
    print("\n─── Summary ───\n")
    summary = manager.summary()
    print(f"  Total tasks: {summary['total']}")
    print(f"  By status: {summary['by_status']}")
    print(f"  Assembly: {router}")

    print("\n═══ Example Complete ═══")


if __name__ == "__main__":
    asyncio.run(main())
