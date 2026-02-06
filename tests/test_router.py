"""
Tests for SabhaRouter — message routing and assembly management.
"""

import asyncio
import pytest

from vakya.router import SabhaRouter
from vakya.identity import Duta, DutaRole
from vakya.message import Vakya, MessageType, Prasna, Uttara
from vakya.channel import Sutra, SutraType


@pytest.fixture
def router():
    return SabhaRouter(name="Test Assembly")


@pytest.fixture
def claude():
    return Duta(
        id="claude-1",
        name="Claude",
        model="claude-opus-4.6",
        provider="anthropic",
        role=DutaRole.KARTR,
        skills=["python", "analysis"],
    )


@pytest.fixture
def gpt():
    return Duta(
        id="gpt-1",
        name="GPT",
        model="gpt-4o",
        provider="openai",
        role=DutaRole.SAMIKSHAKA,
        skills=["python", "code-review"],
    )


class TestDutaManagement:
    """Test Dūta registration and lookup."""

    def test_register(self, router, claude):
        router.register_duta(claude)
        assert router.get_duta("claude-1") is claude

    def test_unregister(self, router, claude):
        router.register_duta(claude)
        router.unregister_duta("claude-1")
        assert router.get_duta("claude-1") is None

    def test_list_dutas(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)
        assert len(router.list_dutas()) == 2

    def test_list_by_role(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)
        workers = router.list_dutas(role="kartr")
        assert len(workers) == 1
        assert workers[0].id == "claude-1"

    def test_list_by_skill(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)
        reviewers = router.list_dutas(skill="code-review")
        assert len(reviewers) == 1
        assert reviewers[0].id == "gpt-1"

    def test_find_capable(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)
        capable = router.find_capable_dutas(["python", "analysis"])
        assert len(capable) == 1
        assert capable[0].id == "claude-1"


class TestChannelManagement:
    """Test channel creation and management."""

    def test_create_sabha(self, router):
        channel = router.create_sabha("test-channel", ["a", "b"])
        assert channel.name == "test-channel"
        assert "a" in channel.members

    def test_create_direct(self, router):
        channel = router.create_direct("a", "b")
        assert channel.sutra_type == SutraType.DIRECT
        assert set(channel.members) == {"a", "b"}

    def test_create_direct_dedup(self, router):
        ch1 = router.create_direct("a", "b")
        ch2 = router.create_direct("a", "b")
        assert ch1.id == ch2.id  # Same channel returned

    def test_get_sutra(self, router):
        channel = router.create_sabha("test")
        retrieved = router.get_sutra(channel.id)
        assert retrieved is channel

    def test_find_by_name(self, router):
        router.create_sabha("my-channel")
        found = router.find_sutra_by_name("my-channel")
        assert found is not None
        assert found.name == "my-channel"


class TestMessageRouting:
    """Test message routing."""

    @pytest.mark.asyncio
    async def test_broadcast(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)

        msg = Vakya(presaka="claude-1", sarira={"text": "broadcast"})
        await router.route(msg)

        assert router.get_message(msg.id) is msg

    @pytest.mark.asyncio
    async def test_directed_message(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)

        msg = Vakya(
            presaka="claude-1",
            prapaka="gpt-1",
            sarira={"text": "direct"},
        )
        await router.route(msg)

        assert router.get_message(msg.id) is msg

    @pytest.mark.asyncio
    async def test_conversation_tracking(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)

        q = Prasna(presaka="claude-1", text="Question?", prapaka="gpt-1")
        a = Uttara(presaka="gpt-1", text="Answer!", reply_to=q)

        await router.route(q)
        await router.route(a)

        # Check conversation
        conv = router.get_samvada(a.samvada_id)
        assert len(conv) >= 1

    @pytest.mark.asyncio
    async def test_observer_notification(self, router, claude):
        router.register_duta(claude)

        observed = []

        async def observer(msg, ch):
            observed.append(msg)

        router.add_observer(observer)

        msg = Vakya(presaka="claude-1", sarira={"text": "observed"})
        await router.route(msg)

        assert len(observed) == 1
        assert observed[0].sarira["text"] == "observed"

    @pytest.mark.asyncio
    async def test_remove_observer(self, router, claude):
        router.register_duta(claude)

        observed = []

        async def observer(msg, ch):
            observed.append(msg)

        router.add_observer(observer)
        router.remove_observer(observer)

        msg = Vakya(presaka="claude-1", sarira={"text": "not observed"})
        await router.route(msg)

        assert len(observed) == 0


class TestStatus:
    """Test assembly status reporting."""

    def test_status(self, router, claude, gpt):
        router.register_duta(claude)
        router.register_duta(gpt)

        status = router.status()
        assert status["dutas"]["total"] == 2
        assert status["dutas"]["active"] == 2
        assert status["messages"]["total"] == 0

    def test_str(self, router, claude):
        router.register_duta(claude)
        s = str(router)
        assert "सभा" in s
        assert "1" in s
