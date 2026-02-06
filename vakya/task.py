"""
Kārya Manager — Task Distribution & Tracking
==============================================

कार्य (Kārya) = Task / Work / Action

The KaryaManager handles:
    - Task creation and assignment
    - Automatic skill-based distribution
    - Progress tracking
    - Task dependencies and workflows
    - Result aggregation

Task Lifecycle (कार्य जीवनचक्र):
    pratiksha (प्रतीक्षा)  → sakriya (सक्रिय)  → sampurna (सम्पूर्ण)
    (pending)              → (active)           → (completed)
                                                → viphala (विफल / failed)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from vakya.identity import Duta
from vakya.message import Vakya, MessageType, Karya as KaryaMessage, Prativedana


class KaryaStatus(str, Enum):
    """
    Task status values (स्थिति = status/state).
    """

    PRATIKSHA = "pratiksha"    # Pending / waiting
    SAKRIYA = "sakriya"        # Active / in-progress
    SAMPURNA = "sampurna"      # Completed successfully
    VIPHALA = "viphala"        # Failed
    NIRASTHA = "nirastha"      # Cancelled
    AVARODHIT = "avarodhit"    # Blocked (dependency not met)


class KaryaPriority(str, Enum):
    """Task priority levels."""

    UCCA = "ucca"          # High
    MADHYAMA = "madhyama"  # Medium
    NIMNA = "nimna"        # Low
    ATYAVASHYAKA = "atyavashyaka"  # Critical / urgent


class KaryaItem(BaseModel):
    """
    A single task (कार्य) in the system.

    Tracks assignment, progress, dependencies, and results.
    """

    id: str = Field(
        default_factory=lambda: f"karya-{uuid.uuid4().hex[:8]}",
        description="Unique task ID",
    )
    title: str = Field(description="Task title")
    description: str = Field(default="", description="Detailed description")
    presaka: str = Field(description="Creator/assigner Dūta ID (प्रेषक)")
    prapaka: str | None = Field(
        default=None,
        description="Assigned Dūta ID (प्रापक). None = unassigned",
    )
    sthiti: KaryaStatus = Field(
        default=KaryaStatus.PRATIKSHA,
        description="Current status (स्थिति)",
    )
    pravrtti: float = Field(
        default=0.0,
        description="Progress 0.0-1.0 (प्रवृत्ति)",
    )
    prathama: KaryaPriority = Field(
        default=KaryaPriority.MADHYAMA,
        description="Priority (प्राथमिकता)",
    )
    skills_needed: list[str] = Field(
        default_factory=list,
        description="Skills required to complete this task",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of tasks that must complete first",
    )
    created: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    deadline: str | None = Field(default=None, description="Optional deadline")
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="Task result/output (फल = result/fruit)",
    )
    phala: dict[str, Any] = Field(
        default_factory=dict,
        description="Alias for result (फल = fruit/result)",
    )
    meta: dict[str, Any] = Field(default_factory=dict)

    def is_complete(self) -> bool:
        return self.sthiti == KaryaStatus.SAMPURNA

    def is_active(self) -> bool:
        return self.sthiti == KaryaStatus.SAKRIYA

    def is_blocked(self) -> bool:
        return self.sthiti == KaryaStatus.AVARODHIT


class KaryaManager:
    """
    Task Manager — creates, assigns, tracks, and completes tasks.

    Works with the SabhaRouter to distribute tasks to capable Dūtas
    and track their progress through message exchange.

    Usage:
        manager = KaryaManager()

        # Create a task
        task = manager.create(
            title="Review Python code",
            description="Review the sorting algorithm for correctness",
            presaka="claude-1",
            skills_needed=["code-review", "python"],
        )

        # Auto-assign based on skills
        manager.auto_assign(task.id, available_dutas)

        # Update progress
        manager.update_progress(task.id, 0.5, "Halfway through review")

        # Complete
        manager.complete(task.id, result={"approved": True, "comments": [...]})
    """

    def __init__(self):
        self.tasks: dict[str, KaryaItem] = {}
        self._history: list[dict[str, Any]] = []

    def create(
        self,
        title: str,
        presaka: str,
        description: str = "",
        prapaka: str | None = None,
        priority: KaryaPriority = KaryaPriority.MADHYAMA,
        skills_needed: list[str] | None = None,
        dependencies: list[str] | None = None,
        **kwargs: Any,
    ) -> KaryaItem:
        """Create a new task."""
        task = KaryaItem(
            title=title,
            description=description,
            presaka=presaka,
            prapaka=prapaka,
            prathama=priority,
            skills_needed=skills_needed or [],
            dependencies=dependencies or [],
            **kwargs,
        )

        # Check if dependencies are met
        if task.dependencies:
            all_met = all(
                self.tasks.get(dep_id, KaryaItem(title="", presaka="")).is_complete()
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )
            if not all_met:
                task.sthiti = KaryaStatus.AVARODHIT

        self.tasks[task.id] = task
        self._log("created", task)
        return task

    def assign(self, karya_id: str, duta_id: str) -> KaryaItem:
        """Assign a task to a specific Dūta."""
        task = self._get_task(karya_id)
        task.prapaka = duta_id
        task.sthiti = KaryaStatus.SAKRIYA
        task.updated = datetime.now(timezone.utc).isoformat()
        self._log("assigned", task, {"duta_id": duta_id})
        return task

    def auto_assign(self, karya_id: str, dutas: list[Duta]) -> Duta | None:
        """
        Auto-assign a task to the best available Dūta based on skills.

        Returns the assigned Dūta or None if no capable Dūta found.
        """
        task = self._get_task(karya_id)

        # Find capable Dūtas
        capable = [d for d in dutas if d.can_handle(task.skills_needed) and d.active]

        if not capable:
            return None

        # Prefer Dūtas with fewer active tasks (simple load balancing)
        active_counts = {}
        for t in self.tasks.values():
            if t.is_active() and t.prapaka:
                active_counts[t.prapaka] = active_counts.get(t.prapaka, 0) + 1

        # Sort by fewest active tasks
        capable.sort(key=lambda d: active_counts.get(d.id, 0))

        chosen = capable[0]
        self.assign(karya_id, chosen.id)
        return chosen

    def update_progress(
        self,
        karya_id: str,
        pravrtti: float,
        vivarana: str = "",
    ) -> KaryaItem:
        """Update task progress (प्रवृत्ति)."""
        task = self._get_task(karya_id)
        task.pravrtti = min(1.0, max(0.0, pravrtti))
        task.updated = datetime.now(timezone.utc).isoformat()
        self._log("progress", task, {"pravrtti": pravrtti, "vivarana": vivarana})
        return task

    def complete(self, karya_id: str, result: dict[str, Any] | None = None) -> KaryaItem:
        """Mark a task as completed (सम्पूर्ण)."""
        task = self._get_task(karya_id)
        task.sthiti = KaryaStatus.SAMPURNA
        task.pravrtti = 1.0
        task.result = result or {}
        task.phala = task.result  # Sanskrit alias
        task.updated = datetime.now(timezone.utc).isoformat()
        self._log("completed", task)

        # Check if this unblocks other tasks
        self._check_unblock(karya_id)
        return task

    def fail(self, karya_id: str, reason: str = "") -> KaryaItem:
        """Mark a task as failed (विफल)."""
        task = self._get_task(karya_id)
        task.sthiti = KaryaStatus.VIPHALA
        task.result = {"error": reason}
        task.updated = datetime.now(timezone.utc).isoformat()
        self._log("failed", task, {"reason": reason})
        return task

    def cancel(self, karya_id: str) -> KaryaItem:
        """Cancel a task (निरस्थ)."""
        task = self._get_task(karya_id)
        task.sthiti = KaryaStatus.NIRASTHA
        task.updated = datetime.now(timezone.utc).isoformat()
        self._log("cancelled", task)
        return task

    # ─── Task Queries ───────────────────────────────────────────────────────

    def get(self, karya_id: str) -> KaryaItem | None:
        """Get a task by ID."""
        return self.tasks.get(karya_id)

    def list_tasks(
        self,
        sthiti: KaryaStatus | None = None,
        duta_id: str | None = None,
        priority: KaryaPriority | None = None,
    ) -> list[KaryaItem]:
        """List tasks with optional filters."""
        tasks = list(self.tasks.values())
        if sthiti:
            tasks = [t for t in tasks if t.sthiti == sthiti]
        if duta_id:
            tasks = [t for t in tasks if t.prapaka == duta_id or t.presaka == duta_id]
        if priority:
            tasks = [t for t in tasks if t.prathama == priority]
        return tasks

    def pending_tasks(self) -> list[KaryaItem]:
        """Get all pending tasks."""
        return self.list_tasks(sthiti=KaryaStatus.PRATIKSHA)

    def active_tasks(self) -> list[KaryaItem]:
        """Get all active tasks."""
        return self.list_tasks(sthiti=KaryaStatus.SAKRIYA)

    # ─── Message Integration ────────────────────────────────────────────────

    def create_karya_message(self, karya_id: str) -> Vakya:
        """Create a Kārya (task assignment) message for a task."""
        task = self._get_task(karya_id)
        return KaryaMessage(
            presaka=task.presaka,
            title=task.title,
            description=task.description,
            prapaka=task.prapaka,
            priority=task.prathama.value,
            skills=task.skills_needed,
            karya_id=task.id,
        )

    def create_prativedana_message(self, karya_id: str, vivarana: str = "") -> Vakya:
        """Create a progress report message for a task."""
        task = self._get_task(karya_id)
        return Prativedana(
            presaka=task.prapaka or task.presaka,
            karya_id=task.id,
            sthiti=task.sthiti.value,
            pravrtti=task.pravrtti,
            vivarana=vivarana,
            prapaka=task.presaka,
        )

    # ─── Status Summary ─────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Get task manager summary."""
        return {
            "total": len(self.tasks),
            "by_status": {
                status.value: len([t for t in self.tasks.values() if t.sthiti == status])
                for status in KaryaStatus
            },
            "by_priority": {
                pri.value: len([t for t in self.tasks.values() if t.prathama == pri])
                for pri in KaryaPriority
            },
        }

    # ─── Internal ───────────────────────────────────────────────────────────

    def _get_task(self, karya_id: str) -> KaryaItem:
        if karya_id not in self.tasks:
            raise KeyError(f"Task not found: {karya_id}")
        return self.tasks[karya_id]

    def _check_unblock(self, completed_id: str) -> None:
        """Check if completing a task unblocks others."""
        for task in self.tasks.values():
            if task.sthiti == KaryaStatus.AVARODHIT and completed_id in task.dependencies:
                # Check if all dependencies are now met
                all_met = all(
                    self.tasks.get(dep_id, KaryaItem(title="", presaka="")).is_complete()
                    for dep_id in task.dependencies
                    if dep_id in self.tasks
                )
                if all_met:
                    task.sthiti = KaryaStatus.PRATIKSHA
                    task.updated = datetime.now(timezone.utc).isoformat()
                    self._log("unblocked", task)

    def _log(self, action: str, task: KaryaItem, extra: dict[str, Any] | None = None) -> None:
        self._history.append({
            "action": action,
            "karya_id": task.id,
            "title": task.title,
            "samaya": datetime.now(timezone.utc).isoformat(),
            **(extra or {}),
        })
