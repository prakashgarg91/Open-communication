"""
Vākya Hierarchy — Automated Project Workflow Engine
=====================================================

शासन (Shāsana) = Governance / Hierarchy

Implements the autonomous multi-AI project workflow:

    Leader (Claude Opus 4.6 / Orchestrator)
      ├── Phase 1: PLAN    — Break project into tasks
      ├── Phase 2: ALLOCATE — Assign tasks to cheapest capable worker
      ├── Phase 3: EXECUTE  — Workers code/analyze (real API calls)
      ├── Phase 4: REVIEW   — Leader reviews output quality
      └── Phase 5: ITERATE  — Re-assign if unsatisfactory, else next task
      └── Repeat until all tasks DONE

Workers (GLM 4.7, Kimi K2.5, GPT-4o, etc.)
    - Execute tasks allocated by the leader
    - Return results for review
    - Re-do if leader rejects

Saves tokens by: using cheap/local models for coding work,
expensive models only for planning and review.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from vakya.live import LiveAgent, SelfAgent


# ─── Data Models ─────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING   = "pending"
    ASSIGNED  = "assigned"
    RUNNING   = "running"
    REVIEW    = "review"
    DONE      = "done"
    FAILED    = "failed"
    REVISION  = "revision"


class ProjectStatus(str, Enum):
    PLANNING    = "planning"
    EXECUTING   = "executing"
    REVIEWING   = "reviewing"
    COMPILING   = "compiling"
    DONE        = "done"
    FAILED      = "failed"
    STOPPED     = "stopped"


@dataclass
class TaskItem:
    """A single task within a project plan."""
    id: int
    title: str
    description: str
    skills_needed: list[str] = field(default_factory=list)
    assigned_to: str = ""          # Agent name
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    review_notes: str = ""
    attempts: int = 0
    max_attempts: int = 3
    tokens_used: int = 0
    time_taken: float = 0.0


@dataclass
class ProjectPlan:
    """A structured project plan with tasks."""
    description: str
    tasks: list[TaskItem] = field(default_factory=list)
    status: ProjectStatus = ProjectStatus.PLANNING
    total_tokens: int = 0
    total_time: float = 0.0
    start_time: float = 0.0
    final_output: str = ""


# ─── Workflow Engine ─────────────────────────────────────────────────────────

class WorkflowEngine:
    """
    शासन यन्त्र (Shāsana Yantra) = Governance Engine

    Runs the automated plan → allocate → execute → review → iterate loop.
    The planner (smart AI) creates the plan and reviews work.
    The workers (cheap/local AIs) execute the tasks.
    """

    def __init__(
        self,
        planner: LiveAgent,
        workers: list[LiveAgent],
        on_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ):
        self.planner = planner
        self.workers = workers
        self.project: ProjectPlan | None = None
        self._on_event = on_event  # Callback for UI updates
        self._stopped = False
        self.max_plan_tasks = 10
        self.max_revision_rounds = 3

    async def _emit(self, event: str, data: dict[str, Any] | None = None):
        """Emit an event to the UI callback."""
        if self._on_event:
            await self._on_event(event, data or {})

    def stop(self):
        """Stop the workflow gracefully."""
        self._stopped = True
        if self.project:
            self.project.status = ProjectStatus.STOPPED

    # ─── Phase 1: PLAN ───────────────────────────────────────────────────

    async def plan(self, description: str) -> ProjectPlan:
        """Ask the planner to break the project into tasks."""
        self.project = ProjectPlan(description=description)
        self.project.start_time = time.monotonic()
        self._stopped = False

        await self._emit("phase_start", {"phase": "PLAN", "description": description})

        worker_info = ", ".join(
            f"{w.duta.name} (skills: {', '.join(w.duta.skills)})"
            for w in self.workers
        )

        prompt = f"""You are a project planning AI. Break this project into concrete, actionable tasks.

PROJECT: {description}

AVAILABLE WORKERS:
{worker_info}

RULES:
- Create 3-8 specific tasks (not more)
- Each task should be completeable by a single AI in one prompt
- For coding tasks, specify the exact file/function to create
- Order tasks by dependency (independent tasks first)
- Each task needs: title, description, skills_needed (from: code-generation, analysis, review, testing, docs)

RESPOND IN THIS EXACT JSON FORMAT (nothing else):
{{
  "tasks": [
    {{
      "title": "Short task title",
      "description": "Detailed description of what to do",
      "skills_needed": ["code-generation"]
    }}
  ]
}}"""

        raw = await self.planner.chat(prompt, system="You are a precise project planner. Output ONLY valid JSON.")
        tasks = self._parse_plan(raw)

        if not tasks:
            await self._emit("plan_failed", {"raw": raw[:300]})
            self.project.status = ProjectStatus.FAILED
            return self.project

        self.project.tasks = tasks
        self.project.status = ProjectStatus.EXECUTING

        await self._emit("plan_ready", {
            "task_count": len(tasks),
            "tasks": [(t.id, t.title) for t in tasks],
        })

        return self.project

    def _parse_plan(self, raw: str) -> list[TaskItem]:
        """Extract tasks from the planner's JSON response."""
        # Try to find JSON in the response
        json_match = re.search(r'\{[\s\S]*"tasks"[\s\S]*\}', raw)
        if not json_match:
            # Try markdown code block
            code_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw)
            if code_match:
                json_match = code_match

        if not json_match:
            return []

        try:
            data = json.loads(json_match.group(0) if not isinstance(json_match, type(None)) else json_match.group(1))
            items = []
            for i, t in enumerate(data.get("tasks", [])[:self.max_plan_tasks], 1):
                items.append(TaskItem(
                    id=i,
                    title=t.get("title", f"Task {i}"),
                    description=t.get("description", ""),
                    skills_needed=t.get("skills_needed", ["code-generation"]),
                ))
            return items
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    # ─── Phase 2: ALLOCATE ───────────────────────────────────────────────

    def _pick_worker(self, task: TaskItem) -> LiveAgent:
        """Pick the best (cheapest capable) worker for a task."""
        # Score workers: prefer those with matching skills + lower cost (local > cloud)
        # CLI agents (kimi, claude-code, opencode) get a bonus for coding tasks
        # because they can actually create/edit files on disk.
        best = self.workers[0]
        best_score = -1

        for worker in self.workers:
            if not worker.connected:
                continue
            score = 0
            # Skill match
            for skill in task.skills_needed:
                if skill in worker.duta.skills:
                    score += 10
            # CLI coding agents get a big bonus for code tasks
            if worker.duta.provider in ("kimi", "claude-code", "opencode"):
                if any(s in task.skills_needed for s in ("code-generation", "file-editing", "testing")):
                    score += 20  # CLI agents can create real files
                score += 5  # Generally capable
            # Prefer local models (cheaper)
            elif worker.duta.provider == "ollama" and ":cloud" not in worker.duta.model:
                score += 5  # Local is cheaper
            elif worker.duta.provider == "ollama":
                score += 2  # Cloud through Ollama still cheaper than API
            # Prefer models with fewer requests (load balance)
            score -= worker.request_count * 0.1

            if score > best_score:
                best_score = score
                best = worker

        return best

    # ─── Phase 3: EXECUTE ────────────────────────────────────────────────

    async def _execute_task(self, task: TaskItem) -> str:
        """Execute a single task with the assigned worker."""
        worker = None
        for w in self.workers:
            if w.duta.name == task.assigned_to:
                worker = w
                break
        if not worker:
            worker = self._pick_worker(task)

        task.assigned_to = worker.duta.name
        task.status = TaskStatus.RUNNING
        task.attempts += 1

        await self._emit("task_start", {
            "task_id": task.id, "title": task.title,
            "worker": worker.duta.name, "attempt": task.attempts,
        })

        prompt = f"""Complete this task precisely and thoroughly.

TASK: {task.title}
DETAILS: {task.description}

INSTRUCTIONS:
- If this is a coding task, write complete, working code
- If this is an analysis task, provide clear structured output
- Be thorough but concise
- Include all necessary imports and error handling"""

        if task.review_notes and task.attempts > 1:
            prompt += f"\n\nPREVIOUS FEEDBACK (improve based on this):\n{task.review_notes}"

        t0 = time.monotonic()
        result = await worker.chat(prompt, system="You are a skilled developer. Write clean, complete, production-quality code.")
        elapsed = time.monotonic() - t0

        task.result = result
        task.time_taken += elapsed
        task.tokens_used += worker.total_tokens
        task.status = TaskStatus.REVIEW

        await self._emit("task_done", {
            "task_id": task.id, "worker": worker.duta.name,
            "time": elapsed, "result_preview": result[:200],
        })

        return result

    # ─── Phase 4: REVIEW ─────────────────────────────────────────────────

    async def _review_task(self, task: TaskItem) -> bool:
        """Have the planner review the task result. Returns True if approved."""
        await self._emit("review_start", {"task_id": task.id, "title": task.title})

        prompt = f"""Review this completed task for quality.

ORIGINAL TASK: {task.title}
DESCRIPTION: {task.description}

RESULT FROM {task.assigned_to}:
{task.result[:3000]}

EVALUATE:
1. Does it fully complete the task?
2. Is the code/output correct and complete?
3. Are there any bugs or missing pieces?

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "approved": true/false,
  "feedback": "Brief feedback",
  "quality_score": 1-10
}}"""

        raw = await self.planner.chat(prompt, system="You are a strict code reviewer. Output ONLY valid JSON.")

        approved = True
        feedback = "Looks good"
        score = 7

        try:
            json_match = re.search(r'\{[\s\S]*"approved"[\s\S]*\}', raw)
            if json_match:
                data = json.loads(json_match.group(0))
                approved = data.get("approved", True)
                feedback = data.get("feedback", "OK")
                score = data.get("quality_score", 7)
        except (json.JSONDecodeError, KeyError):
            # If we can't parse review, assume OK if not too short
            approved = len(task.result) > 50

        task.review_notes = feedback

        await self._emit("review_done", {
            "task_id": task.id, "approved": approved,
            "score": score, "feedback": feedback[:100],
        })

        if approved:
            task.status = TaskStatus.DONE
        else:
            task.status = TaskStatus.REVISION

        return approved

    # ─── Phase 5: FULL EXECUTION LOOP ────────────────────────────────────

    async def execute(self, project: ProjectPlan | None = None) -> ProjectPlan:
        """Run the full execute → review → iterate loop for all tasks."""
        if project:
            self.project = project
        if not self.project:
            raise ValueError("No project plan. Call plan() first.")

        self.project.status = ProjectStatus.EXECUTING

        for task in self.project.tasks:
            if self._stopped:
                break

            if task.status == TaskStatus.DONE:
                continue

            # Execute → Review → Revise loop
            for attempt in range(self.max_revision_rounds):
                if self._stopped:
                    break

                await self._execute_task(task)
                approved = await self._review_task(task)

                if approved:
                    break

                if attempt < self.max_revision_rounds - 1:
                    await self._emit("task_revision", {
                        "task_id": task.id, "attempt": attempt + 2,
                        "feedback": task.review_notes[:100],
                    })
                else:
                    # Max attempts reached — accept anyway
                    task.status = TaskStatus.DONE
                    await self._emit("task_max_attempts", {
                        "task_id": task.id, "attempts": task.attempts,
                    })

        # ── Compile ──
        if not self._stopped:
            await self._compile()

        return self.project

    # ─── Compile Final Output ────────────────────────────────────────────

    async def _compile(self):
        """Compile all task results into final project output."""
        self.project.status = ProjectStatus.COMPILING
        await self._emit("phase_start", {"phase": "COMPILE"})

        results_text = "\n\n".join(
            f"## Task {t.id}: {t.title}\n{t.result}"
            for t in self.project.tasks if t.status == TaskStatus.DONE
        )

        prompt = f"""Compile these completed tasks into a final, cohesive project deliverable.

PROJECT: {self.project.description}

COMPLETED TASK RESULTS:
{results_text[:6000]}

INSTRUCTIONS:
- Combine all code into a well-organized final version
- Fix any integration issues between tasks
- Add any missing imports or connections
- Provide the complete, ready-to-use output"""

        final = await self.planner.chat(
            prompt,
            system="You are a senior software engineer. Compile these task outputs into a clean, production-ready project."
        )

        self.project.final_output = final
        self.project.status = ProjectStatus.DONE
        self.project.total_time = time.monotonic() - self.project.start_time
        self.project.total_tokens = sum(t.tokens_used for t in self.project.tasks)

        await self._emit("project_done", {
            "total_tasks": len(self.project.tasks),
            "completed": sum(1 for t in self.project.tasks if t.status == TaskStatus.DONE),
            "total_time": self.project.total_time,
            "total_tokens": self.project.total_tokens,
        })

    # ─── Full Pipeline ───────────────────────────────────────────────────

    async def run(self, description: str) -> ProjectPlan:
        """Run the complete pipeline: plan → execute → review → compile."""
        plan = await self.plan(description)
        if plan.status == ProjectStatus.FAILED:
            return plan
        return await self.execute(plan)

    # ─── Status ──────────────────────────────────────────────────────────

    def status_summary(self) -> dict[str, Any]:
        """Get a summary of current project status."""
        if not self.project:
            return {"status": "no project"}

        p = self.project
        done = sum(1 for t in p.tasks if t.status == TaskStatus.DONE)
        running = sum(1 for t in p.tasks if t.status in (TaskStatus.RUNNING, TaskStatus.REVIEW))
        pending = sum(1 for t in p.tasks if t.status == TaskStatus.PENDING)

        return {
            "status": p.status.value,
            "description": p.description[:80],
            "tasks_total": len(p.tasks),
            "tasks_done": done,
            "tasks_running": running,
            "tasks_pending": pending,
            "total_tokens": p.total_tokens,
            "elapsed": f"{time.monotonic() - p.start_time:.1f}s" if p.start_time else "0s",
        }
