"""
Vākya Viewer — Rich Terminal Monitor for AI Communications
============================================================

A beautiful terminal-based viewer that lets humans observe
AI-to-AI communication in real-time with color-coded messages,
conversation threading, and task progress tracking.

मानव दर्शक (Mānava Darśaka) = Human Viewer
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.markdown import Markdown

from vakya.message import Vakya, MessageType

console = Console()
logger = logging.getLogger("vakya.monitor")

# Color scheme for message types
PRAKARA_COLORS = {
    "vakya": "white",
    "prasna": "cyan",
    "uttara": "green",
    "karya": "yellow",
    "prativedana": "blue",
    "svikriti": "magenta",
    "nirnaya": "red",
    "vivada": "bright_red",
    "abhivadana": "bright_green",
    "visarjana": "dim",
}

PRAKARA_ICONS = {
    "vakya": "💬",
    "prasna": "❓",
    "uttara": "✅",
    "karya": "📋",
    "prativedana": "📊",
    "svikriti": "👍",
    "nirnaya": "⚖️",
    "vivada": "⚡",
    "abhivadana": "🙏",
    "visarjana": "👋",
}


class VakyaViewer:
    """
    Rich terminal viewer for Vākya protocol messages.

    Connects to a relay server as an observer and displays
    all AI-to-AI communication in a beautiful terminal UI.

    Usage:
        viewer = VakyaViewer(server_url="ws://localhost:8765")
        await viewer.start()
    """

    def __init__(self, server_url: str = "ws://localhost:8765"):
        self.server_url = server_url
        self.messages: list[dict] = []
        self.max_messages = 200
        self._running = False

    async def start(self) -> None:
        """Connect to relay server and start displaying messages."""
        import websockets

        self._running = True

        console.print(Panel(
            "[bold green]वाक्य दर्शक — Vākya Viewer[/bold green]\n"
            f"Connecting to {self.server_url}...\n"
            "नमस्ते! Observing AI communications.",
            title="🔍 Vākya Monitor",
            border_style="green",
        ))

        try:
            async with websockets.connect(self.server_url) as ws:
                # Register as observer
                await ws.send(json.dumps({"type": "observer", "id": "terminal-viewer"}))

                # Wait for welcome
                welcome = json.loads(await ws.recv())
                self._display_welcome(welcome)

                # Message loop
                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("type") == "message":
                        self._display_message(data)
                        self.messages.append(data)
                        if len(self.messages) > self.max_messages:
                            self.messages = self.messages[-self.max_messages:]

        except ConnectionRefusedError:
            console.print("[red]❌ Cannot connect to relay server.[/red]")
            console.print(f"   Make sure the server is running at {self.server_url}")
        except KeyboardInterrupt:
            console.print("\n[yellow]Viewer stopped.[/yellow]")

    def _display_welcome(self, data: dict) -> None:
        """Display welcome message."""
        status = data.get("status", {})
        console.print(Panel(
            f"[green]{data.get('message', 'Connected')}[/green]\n\n"
            f"Dūtas: {status.get('dutas', {}).get('total', 0)} | "
            f"Channels: {status.get('sutras', {}).get('total', 0)} | "
            f"Messages: {status.get('messages', {}).get('total', 0)}",
            title="✅ Connected",
            border_style="green",
        ))

    def _display_message(self, data: dict) -> None:
        """Display a single message in the terminal."""
        prakara = data.get("prakara", "vakya")
        color = PRAKARA_COLORS.get(prakara, "white")
        icon = PRAKARA_ICONS.get(prakara, "💬")

        presaka = data.get("presaka", "unknown")
        prapaka = data.get("prapaka", "*")
        if isinstance(prapaka, list):
            prapaka = ", ".join(prapaka)

        samaya = data.get("samaya", "")
        try:
            dt = datetime.fromisoformat(samaya)
            time_str = dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            time_str = samaya[:8] if samaya else ""

        visaya = data.get("visaya", "")
        sarira = data.get("sarira", {})
        text = sarira.get("text", "")

        # Build the display
        header = f"{icon} [{color}][{prakara}][/{color}] {presaka} → {prapaka}"
        if visaya:
            header += f"  [dim]({visaya})[/dim]"

        body_parts = []
        if text:
            body_parts.append(text)

        # Show task-specific fields
        if prakara == "karya":
            if "title" in sarira:
                body_parts.append(f"📌 Task: {sarira['title']}")
            if "priority" in sarira:
                body_parts.append(f"   Priority: {sarira['priority']}")
        elif prakara == "prativedana":
            progress = sarira.get("pravrtti", 0)
            bar_len = 20
            filled = int(progress * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            body_parts.append(f"   Progress: [{bar}] {progress:.0%}")
            if "sthiti" in sarira:
                body_parts.append(f"   Status: {sarira['sthiti']}")

        body = "\n".join(body_parts) if body_parts else "[dim](no content)[/dim]"

        console.print(f"\n[dim]{time_str}[/dim] {header}")
        console.print(f"  {body}")

    def display_offline(self, messages: list[Vakya]) -> None:
        """Display a list of Vakya messages offline (no server connection needed)."""
        console.print(Panel(
            f"[bold]Displaying {len(messages)} messages[/bold]",
            title="📜 Vākya History",
            border_style="blue",
        ))
        for msg in messages:
            self._display_message({
                "prakara": msg.prakara.value,
                "presaka": msg.presaka,
                "prapaka": msg.prapaka,
                "samaya": msg.samaya,
                "visaya": msg.visaya,
                "sarira": msg.sarira,
            })

    def display_status(self, status: dict) -> None:
        """Display assembly status as a rich table."""
        table = Table(title="सभा Status (Assembly)", border_style="blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in status.items():
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    table.add_row(f"  {key}.{sub_key}", str(sub_val))
            else:
                table.add_row(key, str(value))

        console.print(table)


def main():
    """CLI entry point for the Vākya viewer."""
    import argparse

    parser = argparse.ArgumentParser(description="Vākya Viewer — AI Communication Monitor")
    parser.add_argument(
        "--server", "-s",
        default="ws://localhost:8765",
        help="Relay server URL",
    )
    args = parser.parse_args()

    viewer = VakyaViewer(server_url=args.server)
    try:
        asyncio.run(viewer.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Viewer stopped.[/yellow]")


if __name__ == "__main__":
    main()
