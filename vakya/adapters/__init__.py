"""
Vākya Adapters — AI Model Connectors
======================================

Adapters bridge the Vākya protocol to specific AI provider APIs.
Each adapter translates Vākya messages into provider-specific API calls
and converts responses back into Vākya messages.
"""

from vakya.adapters.base import BaseAdapter, AdapterConfig
from vakya.adapters.openai_adapter import OpenAIAdapter
from vakya.adapters.anthropic_adapter import AnthropicAdapter
from vakya.adapters.glm_adapter import GLMAdapter
from vakya.adapters.ollama_adapter import OllamaAdapter

__all__ = [
    "BaseAdapter",
    "AdapterConfig",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GLMAdapter",
    "OllamaAdapter",
]
