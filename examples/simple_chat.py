"""
Example: Simple Chat Between Two AIs
======================================

Demonstrates basic Vākya protocol usage:
    - Creating AI identities (Dūtas)
    - Setting up a communication channel
    - Exchanging messages
    - Human monitoring
"""

import asyncio
from vakya import (
    VakyaProtocol,
    Vakya,
    Prasna,
    Uttara,
    Svikriti,
    Duta,
    DutaRole,
    SabhaRouter,
)
from vakya.channel import create_direct_sutra
from vakya.monitor.viewer import VakyaViewer


async def main():
    # ─── 1. Create AI Identities ─────────────────────────────────────
    print("═══ Vākya Example: Simple Chat ═══\n")

    claude = Duta(
        id="claude-1",
        name="Claude",
        model="claude-opus-4.6",
        provider="anthropic",
        role=DutaRole.KARTR,
        skills=["code-generation", "analysis", "writing"],
    )

    gpt = Duta(
        id="gpt-1",
        name="GPT",
        model="gpt-4o",
        provider="openai",
        role=DutaRole.KARTR,
        skills=["code-generation", "analysis", "vision"],
    )

    print(f"Created: {claude}")
    print(f"Created: {gpt}")

    # ─── 2. Set Up Router ────────────────────────────────────────────
    router = SabhaRouter(name="Demo Assembly")
    router.register_duta(claude)
    router.register_duta(gpt)

    # Add human observer
    messages_seen = []

    async def human_observer(message: Vakya, channel: str):
        messages_seen.append(message)
        print(f"\n  👁 [Observer] {message}")

    router.add_observer(human_observer)

    # ─── 3. Exchange Messages ────────────────────────────────────────
    print("\n─── Conversation Start ───\n")

    # Claude asks GPT a question
    question = Prasna(
        presaka="claude-1",
        prapaka="gpt-1",
        text="What's your approach to solving the traveling salesman problem?",
        visaya="algorithms",
    )
    await router.route(question)

    # GPT responds
    answer = Uttara(
        presaka="gpt-1",
        text=(
            "For TSP, I'd recommend a hybrid approach: start with nearest-neighbor "
            "heuristic for a good initial solution, then optimize with 2-opt local "
            "search. For exact solutions on small instances, dynamic programming "
            "with bitmask (Held-Karp) works well. What's your take?"
        ),
        reply_to=question,
    )
    await router.route(answer)

    # Claude acknowledges and adds insight
    followup = Uttara(
        presaka="claude-1",
        text=(
            "Good approach! I'd add that for larger instances (>1000 cities), "
            "metaheuristics like simulated annealing or genetic algorithms "
            "provide near-optimal solutions in reasonable time. We could "
            "benchmark different approaches together."
        ),
        reply_to=answer,
    )
    await router.route(followup)

    # GPT acknowledges
    ack = Svikriti(
        presaka="gpt-1",
        reply_to=followup,
        accepted=True,
        text="Great idea! Let's collaborate on a benchmark suite.",
    )
    await router.route(ack)

    # ─── 4. Show Protocol Wire Format ───────────────────────────────
    print("\n─── Wire Format Example ───\n")

    protocol = VakyaProtocol()
    wire = protocol.encode(question)
    print(wire)

    # ─── 5. Validate ────────────────────────────────────────────────
    print("\n─── Validation ───\n")

    is_valid, errors = protocol.validate(wire)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")

    # ─── 6. Assembly Status ─────────────────────────────────────────
    print("\n─── Assembly Status ───\n")
    status = router.status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print(f"\n✅ Human observed {len(messages_seen)} messages")
    print("═══ Example Complete ═══")


if __name__ == "__main__":
    asyncio.run(main())
