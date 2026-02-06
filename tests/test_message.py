"""
Tests for Vakya messages — creation, serialization, replies.
"""

import json
import pytest

from vakya.message import (
    Vakya,
    MessageType,
    Sandarbha,
    Prasna,
    Uttara,
    Karya,
    Prativedana,
    Svikriti,
    Nirnaya,
)


class TestVakya:
    """Test the core Vakya message class."""

    def test_create_basic(self):
        msg = Vakya(presaka="claude-1", sarira={"text": "hello"})
        assert msg.presaka == "claude-1"
        assert msg.id.startswith("msg-")
        assert msg.prakara == MessageType.VAKYA
        assert msg.sarira["text"] == "hello"
        assert msg.samaya  # Has timestamp

    def test_create_with_all_fields(self):
        msg = Vakya(
            presaka="claude-1",
            prapaka="gpt-1",
            prakara=MessageType.PRASNA,
            visaya="algorithms",
            sarira={"text": "How does quicksort work?"},
            samvada_id="conv-123",
            sandarbha=Sandarbha(tags=["algorithms", "sorting"]),
        )
        assert msg.prapaka == "gpt-1"
        assert msg.visaya == "algorithms"
        assert "algorithms" in msg.sandarbha.tags

    def test_to_dict(self):
        msg = Vakya(presaka="test", sarira={"text": "hi"})
        data = msg.to_dict()
        assert isinstance(data, dict)
        assert data["presaka"] == "test"
        assert data["sarira"]["text"] == "hi"

    def test_from_dict(self):
        data = {
            "id": "msg-test",
            "presaka": "claude-1",
            "prapaka": "gpt-1",
            "prakara": "prasna",
            "samaya": "2026-02-06T12:00:00Z",
            "sarira": {"text": "question"},
        }
        msg = Vakya.from_dict(data)
        assert msg.id == "msg-test"
        assert msg.presaka == "claude-1"
        assert msg.prakara == MessageType.PRASNA

    def test_to_json(self):
        msg = Vakya(presaka="test", sarira={"text": "hi"})
        json_str = msg.to_json()
        data = json.loads(json_str)
        assert data["presaka"] == "test"

    def test_from_json(self):
        msg = Vakya(presaka="test", sarira={"text": "hi"})
        json_str = msg.to_json()
        restored = Vakya.from_json(json_str)
        assert restored.presaka == msg.presaka
        assert restored.sarira == msg.sarira

    def test_roundtrip(self):
        original = Vakya(
            presaka="claude",
            prapaka=["gpt", "glm"],
            prakara=MessageType.KARYA,
            visaya="code-review",
            sarira={"text": "Review this", "code": "print('hello')"},
        )
        json_str = original.to_json()
        restored = Vakya.from_json(json_str)
        assert restored.presaka == original.presaka
        assert restored.prapaka == original.prapaka
        assert restored.prakara == original.prakara

    def test_reply(self):
        original = Vakya(
            presaka="gpt-1",
            prapaka="claude-1",
            prakara=MessageType.PRASNA,
            visaya="math",
            sarira={"text": "What is 2+2?"},
        )

        reply = original.reply(
            presaka="claude-1",
            sarira={"text": "The answer is 4."},
        )

        assert reply.presaka == "claude-1"
        assert reply.prapaka == "gpt-1"
        assert reply.prakara == MessageType.UTTARA
        assert reply.sandarbha.reply_to == original.id
        assert reply.visaya == original.visaya

    def test_str_representation(self):
        msg = Vakya(presaka="claude", prapaka="gpt", sarira={"text": "hello"})
        s = str(msg)
        assert "claude" in s
        assert "gpt" in s

    def test_broadcast_prapaka(self):
        msg = Vakya(presaka="claude", prapaka=None, sarira={"text": "broadcast"})
        s = str(msg)
        assert "*" in s


class TestMessageConstructors:
    """Test convenience message constructors."""

    def test_prasna(self):
        msg = Prasna(presaka="claude", text="What is AI?", visaya="philosophy")
        assert msg.prakara == MessageType.PRASNA
        assert msg.sarira["text"] == "What is AI?"
        assert msg.visaya == "philosophy"

    def test_uttara(self):
        question = Prasna(presaka="gpt", text="What is 2+2?")
        answer = Uttara(presaka="claude", text="4", reply_to=question)
        assert answer.prakara == MessageType.UTTARA
        assert answer.prapaka == "gpt"
        assert answer.sandarbha.reply_to == question.id

    def test_uttara_with_string_reply(self):
        answer = Uttara(presaka="claude", text="4", reply_to="msg-123")
        assert answer.sandarbha.reply_to == "msg-123"

    def test_karya(self):
        msg = Karya(
            presaka="leader",
            title="Write code",
            description="Implement sorting",
            prapaka="worker",
            priority="ucca",
            skills=["python"],
        )
        assert msg.prakara == MessageType.KARYA
        assert msg.sarira["title"] == "Write code"
        assert msg.sarira["priority"] == "ucca"
        assert msg.sarira["skills"] == ["python"]

    def test_prativedana(self):
        msg = Prativedana(
            presaka="worker",
            karya_id="task-1",
            sthiti="sakriya",
            pravrtti=0.5,
            vivarana="Halfway done",
        )
        assert msg.prakara == MessageType.PRATIVEDANA
        assert msg.sarira["pravrtti"] == 0.5
        assert msg.sarira["sthiti"] == "sakriya"

    def test_prativedana_clamps_progress(self):
        msg = Prativedana(presaka="w", karya_id="t", sthiti="s", pravrtti=1.5)
        assert msg.sarira["pravrtti"] == 1.0

        msg2 = Prativedana(presaka="w", karya_id="t", sthiti="s", pravrtti=-0.5)
        assert msg2.sarira["pravrtti"] == 0.0

    def test_svikriti(self):
        original = Vakya(presaka="gpt", sarira={"text": "proposal"})
        ack = Svikriti(presaka="claude", reply_to=original, text="Agreed!")
        assert ack.prakara == MessageType.SVIKRITI
        assert ack.sarira["accepted"] is True
        assert ack.prapaka == "gpt"

    def test_nirnaya(self):
        msg = Nirnaya(
            presaka="leader",
            decision="Use Python 3.12",
            reasoning="Better performance and type hints",
            visaya="tech-stack",
        )
        assert msg.prakara == MessageType.NIRNAYA
        assert msg.sarira["decision"] == "Use Python 3.12"


class TestMessageType:
    """Test message type enum."""

    def test_all_types_exist(self):
        expected = [
            "vakya", "prasna", "uttara", "karya", "prativedana",
            "svikriti", "nirnaya", "vivada", "abhivadana", "visarjana",
        ]
        for name in expected:
            assert MessageType(name) is not None

    def test_type_values(self):
        assert MessageType.VAKYA.value == "vakya"
        assert MessageType.PRASNA.value == "prasna"
        assert MessageType.UTTARA.value == "uttara"
