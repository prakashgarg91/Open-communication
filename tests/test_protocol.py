"""
Tests for VakyaProtocol — encoding, decoding, validation.
"""

import json
import pytest

from vakya.protocol import VakyaProtocol, WireMessage, PROTOCOL_VERSION
from vakya.message import Vakya, MessageType, Prasna, Uttara


class TestWireMessage:
    """Test the wire message format."""

    def test_compute_pramana(self):
        wire = WireMessage(sandesa={"id": "test", "presaka": "a"})
        pramana = wire.compute_pramana()
        assert pramana.startswith("sha256:")
        assert len(pramana) > 10

    def test_verify_pramana_no_hash(self):
        wire = WireMessage(sandesa={"test": True})
        assert wire.verify_pramana() is True

    def test_verify_pramana_correct(self):
        wire = WireMessage(sandesa={"test": True})
        wire.pramana = wire.compute_pramana()
        assert wire.verify_pramana() is True

    def test_verify_pramana_tampered(self):
        wire = WireMessage(sandesa={"test": True})
        wire.pramana = "sha256:wrong"
        assert wire.verify_pramana() is False


class TestVakyaProtocol:
    """Test the main protocol handler."""

    def setup_method(self):
        self.protocol = VakyaProtocol()

    def test_encode_decode_roundtrip(self):
        msg = Vakya(
            presaka="claude-1",
            prapaka="gpt-1",
            prakara=MessageType.PRASNA,
            visaya="testing",
            sarira={"text": "Hello, GPT!"},
        )

        encoded = self.protocol.encode(msg)
        decoded = self.protocol.decode(encoded)

        assert decoded.presaka == "claude-1"
        assert decoded.prapaka == "gpt-1"
        assert decoded.prakara == MessageType.PRASNA
        assert decoded.sarira["text"] == "Hello, GPT!"
        assert decoded.visaya == "testing"

    def test_encode_produces_valid_json(self):
        msg = Vakya(presaka="test", sarira={"text": "hello"})
        encoded = self.protocol.encode(msg)
        data = json.loads(encoded)

        assert "vakya" in data
        assert data["vakya"] == PROTOCOL_VERSION
        assert "sandesa" in data
        assert "pramana" in data

    def test_decode_rejects_tampered(self):
        msg = Vakya(presaka="test", sarira={"text": "hello"})
        encoded = self.protocol.encode(msg)

        # Tamper with the message
        data = json.loads(encoded)
        data["sandesa"]["sarira"]["text"] = "tampered!"
        tampered = json.dumps(data)

        with pytest.raises(ValueError, match="integrity"):
            self.protocol.decode(tampered)

    def test_validate_valid_message(self):
        msg = Vakya(presaka="test", sarira={"text": "hello"})
        encoded = self.protocol.encode(msg)
        is_valid, errors = self.protocol.validate(encoded)
        assert is_valid is True
        assert errors == []

    def test_validate_missing_version(self):
        raw = json.dumps({"sandesa": {"id": "x", "presaka": "a", "prakara": "vakya", "samaya": "now"}})
        is_valid, errors = self.protocol.validate(raw)
        assert is_valid is False
        assert any("vakya" in e for e in errors)

    def test_validate_missing_payload(self):
        raw = json.dumps({"vakya": "1.0"})
        is_valid, errors = self.protocol.validate(raw)
        assert is_valid is False
        assert any("sandesa" in e for e in errors)

    def test_validate_invalid_json(self):
        is_valid, errors = self.protocol.validate("not json")
        assert is_valid is False
        assert any("Invalid JSON" in e for e in errors)

    def test_validate_invalid_message_type(self):
        raw = json.dumps({
            "vakya": "1.0",
            "sandesa": {
                "id": "x",
                "presaka": "a",
                "prakara": "invalid_type",
                "samaya": "now",
            },
        })
        is_valid, errors = self.protocol.validate(raw)
        assert is_valid is False
        assert any("prakara" in e for e in errors)

    def test_create_vakya_factory(self):
        msg = self.protocol.create_vakya(
            presaka_id="claude-1",
            prakara=MessageType.PRASNA,
            sarira={"text": "What is 2+2?"},
            prapaka_id="gpt-1",
            visaya="math",
        )
        assert msg.presaka == "claude-1"
        assert msg.prapaka == "gpt-1"
        assert msg.prakara == MessageType.PRASNA

    def test_create_vakya_with_string_type(self):
        msg = self.protocol.create_vakya(
            presaka_id="test",
            prakara="prasna",
            sarira={"text": "question"},
        )
        assert msg.prakara == MessageType.PRASNA

    def test_unsigned_messages(self):
        protocol = VakyaProtocol(sign_messages=False)
        msg = Vakya(presaka="test", sarira={"text": "unsigned"})
        encoded = protocol.encode(msg)
        data = json.loads(encoded)
        assert data["pramana"] is None
