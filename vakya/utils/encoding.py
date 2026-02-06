"""
Encoding Utilities for the Vākya Protocol
===========================================

Helpers for message encoding, compression, and format conversion.
"""

from __future__ import annotations

import json
import base64
import gzip
from typing import Any


def compact_json(data: dict[str, Any]) -> str:
    """Produce compact JSON (minimal whitespace) for wire transmission."""
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def pretty_json(data: dict[str, Any]) -> str:
    """Produce human-readable JSON with Sanskrit-friendly Unicode."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def compress_message(json_str: str) -> bytes:
    """Compress a JSON message using gzip for bandwidth-constrained channels."""
    return gzip.compress(json_str.encode("utf-8"))


def decompress_message(data: bytes) -> str:
    """Decompress a gzip-compressed message."""
    return gzip.decompress(data).decode("utf-8")


def to_base64(json_str: str) -> str:
    """Encode a JSON message as base64 (for embedding in other formats)."""
    return base64.b64encode(json_str.encode("utf-8")).decode("ascii")


def from_base64(b64_str: str) -> str:
    """Decode a base64-encoded message."""
    return base64.b64decode(b64_str.encode("ascii")).decode("utf-8")


def message_size(json_str: str) -> dict[str, int]:
    """Get message size in various formats."""
    raw_bytes = json_str.encode("utf-8")
    compressed = gzip.compress(raw_bytes)
    return {
        "characters": len(json_str),
        "bytes_utf8": len(raw_bytes),
        "bytes_gzip": len(compressed),
        "compression_ratio": round(len(compressed) / len(raw_bytes), 3) if raw_bytes else 0,
    }
