"""Vākya Server — Relay & Web API."""

from vakya.server.relay import VakyaRelay, main
from vakya.server.web import create_app

__all__ = ["VakyaRelay", "create_app", "main"]
