"""
Vākya Protocol Core — Message Format & Validation
===================================================

Defines the Vākya protocol specification: message schema, serialization,
validation, and the canonical JSON wire format.

Protocol Design Principles (सिद्धान्त):
    1. Sarala (सरल)     — Simple: JSON-based, no binary encoding needed
    2. Vyāpaka (व्यापक)  — Universal: any AI model can participate
    3. Spashta (स्पष्ट)  — Clear: human-readable at every layer
    4. Vistārya (विस्तार्य) — Extensible: custom fields without breaking compat
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from vakya.message import MessageType, Vakya


# ─── Protocol Constants ──────────────────────────────────────────────────────

PROTOCOL_NAME = "Vākya"
PROTOCOL_VERSION = "1.0"
MAGIC_HEADER = "वाक्य"  # Sanskrit header for identification


class ProtocolMeta(BaseModel):
    """
    Protocol metadata included in every wire message.

    Fields use Sanskrit-inspired names with English aliases:
        vakya    = protocol version marker
        pramana  = integrity hash (प्रमाण = proof)
    """

    vakya: str = Field(default=PROTOCOL_VERSION, description="Protocol version")
    pramana: str | None = Field(default=None, description="Message integrity hash (SHA-256)")


class WireMessage(BaseModel):
    """
    The canonical wire format for Vākya protocol messages.

    This is what goes over the network — a thin envelope around
    the actual Vakya message, adding protocol version and integrity.

    Wire Format (JSON):
    {
        "vakya": "1.0",
        "pramana": "sha256:abcdef...",
        "sandesa": { ... the actual message ... }
    }

    Sanskrit:
        sandeśa (सन्देश) = message payload
    """

    vakya: str = Field(default=PROTOCOL_VERSION, description="Protocol version")
    pramana: str | None = Field(default=None, description="Integrity hash")
    sandesa: dict[str, Any] = Field(description="Message payload (serialized Vakya)")

    def compute_pramana(self) -> str:
        """Compute SHA-256 integrity hash of the message payload."""
        payload = json.dumps(self.sandesa, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def verify_pramana(self) -> bool:
        """Verify message integrity. Returns True if hash matches or no hash set."""
        if self.pramana is None:
            return True
        return self.pramana == self.compute_pramana()


class VakyaProtocol:
    """
    Main protocol handler — encodes, decodes, validates, and routes messages.

    Usage:
        protocol = VakyaProtocol()

        # Encode a message for the wire
        wire_json = protocol.encode(message)

        # Decode a wire message back
        message = protocol.decode(wire_json)

        # Validate a raw JSON string
        is_valid, errors = protocol.validate(raw_json)
    """

    def __init__(self, version: str = PROTOCOL_VERSION, sign_messages: bool = True):
        self.version = version
        self.sign_messages = sign_messages

    def encode(self, message: Vakya) -> str:
        """
        Encode a Vakya message into the wire format (JSON string).

        Args:
            message: A Vakya message object

        Returns:
            JSON string ready to send over the network
        """
        payload = message.to_dict()
        wire = WireMessage(vakya=self.version, sandesa=payload)

        if self.sign_messages:
            wire.pramana = wire.compute_pramana()

        return wire.model_dump_json(indent=2)

    def decode(self, raw: str) -> Vakya:
        """
        Decode a wire-format JSON string back into a Vakya message.

        Args:
            raw: JSON string received from the network

        Returns:
            Vakya message object

        Raises:
            ValueError: If integrity check fails or format is invalid
        """
        wire = WireMessage.model_validate_json(raw)

        # Verify integrity
        if not wire.verify_pramana():
            raise ValueError(
                f"प्रमाण verification failed (Pramāṇa / integrity check failed). "
                f"Message may have been tampered with."
            )

        return Vakya.from_dict(wire.sandesa)

    def validate(self, raw: str) -> tuple[bool, list[str]]:
        """
        Validate a raw JSON string against the Vākya protocol.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors: list[str] = []

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]

        # Check protocol version
        if "vakya" not in data:
            errors.append("Missing 'vakya' protocol version field")
        elif data["vakya"] != self.version:
            errors.append(
                f"Protocol version mismatch: expected {self.version}, got {data['vakya']}"
            )

        # Check payload
        if "sandesa" not in data:
            errors.append("Missing 'sandesa' (message payload) field")
        else:
            sandesa = data["sandesa"]
            required_fields = ["id", "presaka", "prakara", "samaya"]
            for field in required_fields:
                if field not in sandesa:
                    errors.append(f"Missing required field in sandesa: '{field}'")

            # Validate message type
            if "prakara" in sandesa:
                valid_types = [t.value for t in MessageType]
                if sandesa["prakara"] not in valid_types:
                    errors.append(
                        f"Invalid prakara (message type): '{sandesa['prakara']}'. "
                        f"Valid types: {valid_types}"
                    )

        # Verify integrity if present
        if "pramana" in data and data["pramana"] is not None:
            try:
                wire = WireMessage.model_validate(data)
                if not wire.verify_pramana():
                    errors.append("Pramāṇa (integrity hash) verification failed")
            except Exception as e:
                errors.append(f"Integrity verification error: {e}")

        return len(errors) == 0, errors

    def create_vakya(
        self,
        presaka_id: str,
        prakara: MessageType | str,
        sarira: dict[str, Any],
        prapaka_id: str | list[str] | None = None,
        visaya: str | None = None,
        samvada_id: str | None = None,
        **kwargs: Any,
    ) -> Vakya:
        """
        Convenience factory to create a new Vakya message.

        Args:
            presaka_id: Sender ID (प्रेषक)
            prakara: Message type (प्रकार)
            sarira: Message body (शरीर)
            prapaka_id: Recipient ID(s) (प्रापक), None = broadcast
            visaya: Subject/topic (विषय)
            samvada_id: Conversation thread ID (संवाद)

        Returns:
            New Vakya message
        """
        if isinstance(prakara, str):
            prakara = MessageType(prakara)

        return Vakya(
            presaka=presaka_id,
            prapaka=prapaka_id,
            prakara=prakara,
            sarira=sarira,
            visaya=visaya,
            samvada_id=samvada_id,
            **kwargs,
        )

    @staticmethod
    def now_samaya() -> str:
        """Get current timestamp in ISO format (samaya = समय = time)."""
        return datetime.now(timezone.utc).isoformat()
