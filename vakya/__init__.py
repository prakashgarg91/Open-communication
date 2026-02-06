"""
Vākya (वाक्य) — Open Protocol for AI-to-AI Communication
=========================================================

A Sanskrit-inspired, JSON-based protocol enabling seamless communication
between any AI/LLM models — Claude, GPT, GLM, Gemini, LLaMA, and beyond.

Sanskrit Glossary (संस्कृत शब्दकोश):
    Vākya   (वाक्य)   = Expression / Message — the fundamental communication unit
    Saṃvāda (संवाद)   = Dialogue — a threaded conversation between AIs
    Kārya   (कार्य)   = Task — a unit of work to be distributed or completed
    Sabhā   (सभा)     = Assembly — a group/council of collaborating AIs
    Sūtra   (सूत्र)   = Thread / Connection — a communication channel
    Dūta    (दूत)     = Messenger / Agent — an AI participant
    Pramāṇa (प्रमाण)  = Proof / Validation — message integrity
"""

__version__ = "0.1.0"
__protocol_version__ = "1.0"
__project__ = "Open-communication"

from vakya.protocol import VakyaProtocol
from vakya.message import (
    Vakya,
    Prasna,
    Uttara,
    Karya,
    Prativedana,
    Svikriti,
    Nirnaya,
    MessageType,
)
from vakya.identity import Duta, DutaRole
from vakya.channel import Sutra
from vakya.router import SabhaRouter
from vakya.task import KaryaManager, KaryaStatus

# Bridge — Cross-IDE AI Communication
from vakya.bridge import Setu, SetuConfig, Khoj, WebSocketYojaka, StdioYojaka

__all__ = [
    # Protocol
    "VakyaProtocol",
    # Messages
    "Vakya",
    "Prasna",
    "Uttara",
    "Karya",
    "Prativedana",
    "Svikriti",
    "Nirnaya",
    "MessageType",
    # Identity
    "Duta",
    "DutaRole",
    # Channel
    "Sutra",
    # Router
    "SabhaRouter",
    # Task
    "KaryaManager",
    "KaryaStatus",
    # Bridge — Cross-IDE
    "Setu",
    "SetuConfig",
    "Khoj",
    "WebSocketYojaka",
    "StdioYojaka",
]
