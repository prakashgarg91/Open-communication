"""
Dūta — AI Agent Identity System
=================================

दूत (Dūta) = Messenger / Agent / Ambassador

Every AI participating in the Vākya protocol is a Dūta.
Each Dūta has an identity, capabilities, and a role in the Sabhā (assembly).

Identity Schema:
    id       — Unique identifier (e.g., "claude-opus-1")
    name     — Display name (e.g., "Claude")
    model    — Model identifier (e.g., "claude-opus-4.6")
    provider — Provider name (e.g., "anthropic")
    role     — Role in the assembly
    skills   — What this AI is good at
    bhasha   — Languages supported (भाषा = language)
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DutaRole(str, Enum):
    """
    Roles a Dūta can play in a Sabhā (assembly).

    Sanskrit-inspired role names:
        neta     (नेता)    = Leader / Coordinator — orchestrates tasks
        kartr    (कर्तृ)   = Worker / Executor — performs tasks
        samikshaka (समीक्षक) = Reviewer / Critic — reviews work
        pariksaka (परीक्षक)  = Tester / Validator — validates results
        mantri   (मन्त्री)  = Advisor — provides guidance
        srotri   (श्रोतृ)  = Observer / Listener — monitors only
        madhyastha (मध्यस्थ) = Mediator — resolves disputes
    """

    NETA = "neta"              # Leader / Coordinator
    KARTR = "kartr"            # Worker / Executor
    SAMIKSHAKA = "samikshaka"  # Reviewer
    PARIKSAKA = "pariksaka"    # Tester / Validator
    MANTRI = "mantri"          # Advisor
    SROTRI = "srotri"          # Observer
    MADHYASTHA = "madhyastha"  # Mediator


class DutaCapability(BaseModel):
    """A specific capability/skill of a Dūta."""

    name: str = Field(description="Capability name (e.g., 'code-generation')")
    level: str = Field(
        default="madhyama",
        description="Proficiency: ucca (high), madhyama (medium), nimna (low)",
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Programming/human languages for this capability",
    )


class Duta(BaseModel):
    """
    A Dūta (दूत) — an AI agent participating in the Vākya protocol.

    Example:
        claude = Duta(
            name="Claude",
            model="claude-opus-4.6",
            provider="anthropic",
            role=DutaRole.KARTR,
            skills=["code-generation", "analysis", "writing"],
        )
    """

    id: str = Field(
        default_factory=lambda: f"duta-{uuid.uuid4().hex[:8]}",
        description="Unique agent ID",
    )
    name: str = Field(description="Display name")
    model: str = Field(description="Model identifier (e.g., 'claude-opus-4.6', 'gpt-4o')")
    provider: str = Field(
        default="unknown",
        description="Provider (anthropic, openai, zhipu, meta, google, local, etc.)",
    )
    role: DutaRole = Field(
        default=DutaRole.KARTR,
        description="Role in the assembly (सभा)",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of skills/capabilities",
    )
    capabilities: list[DutaCapability] = Field(
        default_factory=list,
        description="Detailed capability descriptions",
    )
    bhasha: list[str] = Field(
        default_factory=lambda: ["en"],
        description="Supported languages (भाषा)",
    )
    max_tokens: int | None = Field(
        default=None,
        description="Maximum token context window",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    active: bool = Field(default=True, description="Whether this Dūta is currently active")

    def to_header(self) -> dict[str, str]:
        """Create a compact identity header for message routing."""
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "provider": self.provider,
            "role": self.role.value,
        }

    def has_skill(self, skill: str) -> bool:
        """Check if this Dūta has a specific skill."""
        return skill.lower() in [s.lower() for s in self.skills]

    def can_handle(self, required_skills: list[str]) -> bool:
        """Check if this Dūta can handle a task requiring certain skills."""
        my_skills = {s.lower() for s in self.skills}
        return all(s.lower() in my_skills for s in required_skills)

    def __str__(self) -> str:
        return f"दूत {self.name} ({self.model}) [{self.role.value}]"

    def __repr__(self) -> str:
        return f"Duta(id={self.id!r}, name={self.name!r}, model={self.model!r})"


# ─── Pre-built Dūta Templates ───────────────────────────────────────────────


def create_claude_duta(
    model: str = "claude-opus-4.6",
    role: DutaRole = DutaRole.KARTR,
    **kwargs: Any,
) -> Duta:
    """Create a Dūta for Anthropic Claude models."""
    return Duta(
        name="Claude",
        model=model,
        provider="anthropic",
        role=role,
        skills=["code-generation", "analysis", "writing", "reasoning", "math"],
        bhasha=["en", "fr", "de", "es", "ja", "ko", "zh", "sa"],
        **kwargs,
    )


def create_gpt_duta(
    model: str = "gpt-4o",
    role: DutaRole = DutaRole.KARTR,
    **kwargs: Any,
) -> Duta:
    """Create a Dūta for OpenAI GPT models."""
    return Duta(
        name="GPT",
        model=model,
        provider="openai",
        role=role,
        skills=["code-generation", "analysis", "writing", "reasoning", "vision"],
        bhasha=["en", "fr", "de", "es", "ja", "ko", "zh"],
        **kwargs,
    )


def create_glm_duta(
    model: str = "glm-4",
    role: DutaRole = DutaRole.KARTR,
    **kwargs: Any,
) -> Duta:
    """Create a Dūta for Zhipu GLM models."""
    return Duta(
        name="GLM",
        model=model,
        provider="zhipu",
        role=role,
        skills=["code-generation", "analysis", "writing", "chinese-nlp"],
        bhasha=["zh", "en"],
        **kwargs,
    )


def create_gemini_duta(
    model: str = "gemini-2.0-flash",
    role: DutaRole = DutaRole.KARTR,
    **kwargs: Any,
) -> Duta:
    """Create a Dūta for Google Gemini models."""
    return Duta(
        name="Gemini",
        model=model,
        provider="google",
        role=role,
        skills=["code-generation", "analysis", "vision", "reasoning", "multimodal"],
        bhasha=["en", "fr", "de", "es", "ja", "ko", "zh"],
        **kwargs,
    )


def create_local_duta(
    name: str,
    model: str,
    role: DutaRole = DutaRole.KARTR,
    **kwargs: Any,
) -> Duta:
    """Create a Dūta for locally-hosted models (Ollama, vLLM, etc.)."""
    return Duta(
        name=name,
        model=model,
        provider="local",
        role=role,
        skills=kwargs.pop("skills", ["code-generation", "analysis"]),
        **kwargs,
    )
