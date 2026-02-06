"""
Vākya Messages — Core Message Types
=====================================

Every communication in the Vākya protocol is a message (sandeśa/सन्देश).
Messages are typed by their prakāra (प्रकार = type/kind).

Message Types (प्रकार):
    vakya        (वाक्य)      = General statement / expression
    prasna       (प्रश्न)     = Question — requesting information
    uttara       (उत्तर)      = Answer / Response
    karya        (कार्य)      = Task assignment
    prativedana  (प्रतिवेदन)   = Status report / progress update
    svikriti     (स्वीकृति)    = Acknowledgment
    nirnaya      (निर्णय)     = Decision / conclusion
    vivada       (विवाद)      = Disagreement / counter-proposal
    abhivadana   (अभिवादन)    = Greeting / handshake
    visarjana    (विसर्जन)    = Farewell / disconnect

Sanskrit Body Schema:
    śarīra   (शरीर)   = body — the message content
    viṣaya   (विषय)   = subject/topic
    saṃvāda  (संवाद)  = conversation ID (thread)
    sandarbha (सन्दर्भ) = context / references
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """
    Message types in the Vākya protocol.
    Each type has a Sanskrit name and clear semantic meaning.
    """

    VAKYA = "vakya"              # General statement
    PRASNA = "prasna"            # Question
    UTTARA = "uttara"            # Answer / Response
    KARYA = "karya"              # Task assignment
    PRATIVEDANA = "prativedana"  # Status report
    SVIKRITI = "svikriti"        # Acknowledgment
    NIRNAYA = "nirnaya"          # Decision
    VIVADA = "vivada"            # Disagreement / counter-proposal
    ABHIVADANA = "abhivadana"    # Greeting / handshake
    VISARJANA = "visarjana"      # Farewell / disconnect


class Sandarbha(BaseModel):
    """
    Message context / references (सन्दर्भ).

    Allows messages to reference other messages, external resources,
    or carry additional metadata for AI consumption.
    """

    reply_to: str | None = Field(default=None, description="ID of message being replied to")
    references: list[str] = Field(default_factory=list, description="IDs of referenced messages")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    meta: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class Vakya(BaseModel):
    """
    The fundamental message unit in the Vākya protocol.

    वाक्य — A complete expression from one Dūta (AI agent) to another.

    Example JSON:
    {
        "id": "msg-550e8400-e29b-41d4-a716-446655440000",
        "samvada_id": "conv-123",
        "presaka": "claude-opus",
        "prapaka": "gpt-4",
        "samaya": "2026-02-06T12:00:00Z",
        "prakara": "prasna",
        "visaya": "code-review",
        "sarira": {
            "text": "What do you think about this algorithm's complexity?",
            "code": "def sort(arr): ...",
            "language": "python"
        },
        "sandarbha": {
            "reply_to": null,
            "tags": ["algorithms", "review"]
        }
    }
    """

    id: str = Field(default_factory=lambda: f"msg-{uuid.uuid4()}", description="Unique message ID")
    samvada_id: str | None = Field(
        default=None,
        description="Conversation/thread ID (संवाद). None = new conversation",
    )
    presaka: str = Field(description="Sender ID (प्रेषक = sender)")
    prapaka: str | list[str] | None = Field(
        default=None,
        description="Recipient ID(s) (प्रापक = receiver). None = broadcast to all",
    )
    samaya: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp ISO-8601 (समय = time)",
    )
    prakara: MessageType = Field(
        default=MessageType.VAKYA,
        description="Message type (प्रकार = type/kind)",
    )
    visaya: str | None = Field(
        default=None,
        description="Subject / topic (विषय)",
    )
    sarira: dict[str, Any] = Field(
        default_factory=dict,
        description="Message body (शरीर = body). Schema varies by prakara",
    )
    sandarbha: Sandarbha = Field(
        default_factory=Sandarbha,
        description="Context and references (सन्दर्भ)",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for wire transmission."""
        data = self.model_dump(mode="json")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vakya:
        """Deserialize from dictionary."""
        return cls.model_validate(data)

    def to_json(self, pretty: bool = True) -> str:
        """Serialize to JSON string."""
        if pretty:
            return self.model_dump_json(indent=2)
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> Vakya:
        """Deserialize from JSON string."""
        return cls.model_validate_json(raw)

    def reply(
        self,
        presaka: str,
        prakara: MessageType = MessageType.UTTARA,
        sarira: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Vakya:
        """
        Create a reply to this message.

        Automatically sets samvada_id and sandarbha.reply_to.
        """
        return Vakya(
            presaka=presaka,
            prapaka=self.presaka,  # Reply goes back to original sender
            samvada_id=self.samvada_id or self.id,
            prakara=prakara,
            visaya=self.visaya,
            sarira=sarira or {},
            sandarbha=Sandarbha(reply_to=self.id),
            **kwargs,
        )

    def __str__(self) -> str:
        direction = f"{self.presaka} → {self.prapaka or '*'}"
        text = self.sarira.get("text", "")
        preview = text[:80] + "..." if len(text) > 80 else text
        return f"[{self.prakara.value}] {direction}: {preview}"


# ─── Convenience Message Constructors ────────────────────────────────────────


def Prasna(
    presaka: str,
    text: str,
    prapaka: str | list[str] | None = None,
    visaya: str | None = None,
    **kwargs: Any,
) -> Vakya:
    """Create a question message (प्रश्न)."""
    return Vakya(
        presaka=presaka,
        prapaka=prapaka,
        prakara=MessageType.PRASNA,
        visaya=visaya,
        sarira={"text": text, **kwargs},
    )


def Uttara(
    presaka: str,
    text: str,
    reply_to: Vakya | str | None = None,
    prapaka: str | list[str] | None = None,
    **kwargs: Any,
) -> Vakya:
    """Create an answer/response message (उत्तर)."""
    reply_id = reply_to.id if isinstance(reply_to, Vakya) else reply_to
    samvada = None
    if isinstance(reply_to, Vakya):
        samvada = reply_to.samvada_id or reply_to.id
        prapaka = prapaka or reply_to.presaka

    return Vakya(
        presaka=presaka,
        prapaka=prapaka,
        prakara=MessageType.UTTARA,
        samvada_id=samvada,
        sarira={"text": text, **kwargs},
        sandarbha=Sandarbha(reply_to=reply_id) if reply_id else Sandarbha(),
    )


def Karya(
    presaka: str,
    title: str,
    description: str,
    prapaka: str | list[str] | None = None,
    priority: str = "madhyama",  # madhyama=medium, ucca=high, nimna=low
    skills: list[str] | None = None,
    **kwargs: Any,
) -> Vakya:
    """
    Create a task assignment message (कार्य).

    Priority levels (Sanskrit):
        ucca    (उच्च)   = high
        madhyama (मध्यम) = medium
        nimna   (निम्न)  = low
    """
    return Vakya(
        presaka=presaka,
        prapaka=prapaka,
        prakara=MessageType.KARYA,
        visaya=title,
        sarira={
            "title": title,
            "description": description,
            "priority": priority,
            "skills": skills or [],
            **kwargs,
        },
    )


def Prativedana(
    presaka: str,
    karya_id: str,
    sthiti: str,
    pravrtti: float = 0.0,
    vivarana: str = "",
    prapaka: str | list[str] | None = None,
    **kwargs: Any,
) -> Vakya:
    """
    Create a status report / progress update (प्रतिवेदन).

    Status values (sthiti / स्थिति):
        pratiksha  (प्रतीक्षा)  = pending/waiting
        sakriya    (सक्रिय)     = active/in-progress
        sampurna   (सम्पूर्ण)   = completed
        viphala    (विफल)      = failed

    Args:
        karya_id: Task ID being reported on
        sthiti: Current status
        pravrtti: Progress 0.0 to 1.0 (प्रवृत्ति = progress)
        vivarana: Description/details (विवरण)
    """
    return Vakya(
        presaka=presaka,
        prapaka=prapaka,
        prakara=MessageType.PRATIVEDANA,
        sarira={
            "karya_id": karya_id,
            "sthiti": sthiti,
            "pravrtti": min(1.0, max(0.0, pravrtti)),
            "vivarana": vivarana,
            **kwargs,
        },
    )


def Svikriti(
    presaka: str,
    reply_to: Vakya | str,
    accepted: bool = True,
    text: str = "",
    **kwargs: Any,
) -> Vakya:
    """Create an acknowledgment message (स्वीकृति = acceptance)."""
    reply_id = reply_to.id if isinstance(reply_to, Vakya) else reply_to
    prapaka = reply_to.presaka if isinstance(reply_to, Vakya) else None

    return Vakya(
        presaka=presaka,
        prapaka=prapaka,
        prakara=MessageType.SVIKRITI,
        sarira={"accepted": accepted, "text": text, **kwargs},
        sandarbha=Sandarbha(reply_to=reply_id),
    )


def Nirnaya(
    presaka: str,
    decision: str,
    reasoning: str = "",
    prapaka: str | list[str] | None = None,
    visaya: str | None = None,
    **kwargs: Any,
) -> Vakya:
    """Create a decision/conclusion message (निर्णय)."""
    return Vakya(
        presaka=presaka,
        prapaka=prapaka,
        prakara=MessageType.NIRNAYA,
        visaya=visaya,
        sarira={"decision": decision, "reasoning": reasoning, **kwargs},
    )
