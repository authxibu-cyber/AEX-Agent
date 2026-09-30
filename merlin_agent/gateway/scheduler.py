"""
Embedded Cron Scheduler for Merlin Agent.
Runs periodic automations in natural language, non-blocking tick worker,
and conversational memory injection matching Hermes Agent specifications.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from croniter import croniter
from pydantic import BaseModel, Field

from merlin_agent.agent.core import MerlinAgent
from merlin_agent.config import load_config
from merlin_agent.memory.store import SessionStore
from merlin_agent.tools.base import ToolResult, tool

logger = logging.getLogger("merlin_agent.cron")


class CronJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    expression: str
    prompt: str
    target_platform: str = "cli"
    last_run: Optional[float] = None
    next_run: float
    active: bool = True


class CronScheduler:
    _instance: Optional[CronScheduler] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.jobs = {}
            cls._instance._running = False
            cls._instance._task = None
        return cls._instance

    def add_job(self, expression: str, prompt: str, target_platform: str = "cli") -> CronJob:
        now = time.time()
        iter_cron = croniter(expression, now)
        next_run = iter_cron.get_next(float)

        job = CronJob(
            expression=expression,
            prompt=prompt,
            target_platform=target_platform,
            next_run=next_run,
        )
        self.jobs[job.job_id] = job
        logger.info(f"[Cron] Added job {job.job_id}: '{prompt}' (Expression: {expression})")
        return job

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"[Cron] Removed job {job_id}")
            return True
        return False

    def list_jobs(self) -> List[CronJob]:
        return list(self.jobs.values())

    async def start(self) -> None:
        self._running = True
        logger.info("[Cron] Scheduler worker started.")
        while self._running:
            await self._tick()
            await asyncio.sleep(5.0)

    def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        now = time.time()
        for job_id, job in list(self.jobs.items()):
            if job.active and now >= job.next_run:
                # Schedule execution in background without blocking the scheduler tick (Hermes fix)
                asyncio.create_task(self._execute_job(job))
                # Advance next run
                iter_cron = croniter(job.expression, now)
                job.last_run = now
                job.next_run = iter_cron.get_next(float)

    async def _execute_job(self, job: CronJob) -> None:
        logger.info(f"[Cron] Executing scheduled automation: '{job.prompt}'")
        cfg = load_config()
        session_id = f"cron_{job.job_id}"
        agent = MerlinAgent(config=cfg, session_id=session_id)

        try:
            res = await agent.run_conversation_async(
                user_message=f"[Automated Scheduled Task]\n{job.prompt}",
            )
            output = res.get("response", "")
            logger.info(f"[Cron] Job {job.job_id} completed successfully.")
            # Record execution in persistent session store
            store = SessionStore()
            store.add_message(session_id, "system", f"Scheduled task executed at {time.ctime()}: {output[:200]}")
        except Exception as e:
            logger.error(f"[Cron] Job {job.job_id} failed: {e}")


# Registered Tools for agent interaction with the scheduler
_scheduler = CronScheduler()


@tool(
    name="schedule_cron",
    description="Schedule an automated periodic task in natural language with a standard 5-part cron expression.",
    toolset="cronjob",
)
def schedule_cron(cron_expression: str, task_prompt: str) -> ToolResult:
    try:
        if not croniter.is_valid(cron_expression):
            return ToolResult(success=False, output="", error=f"Invalid cron expression: {cron_expression}")

        job = _scheduler.add_job(cron_expression, task_prompt)
        next_dt = time.ctime(job.next_run)
        return ToolResult(
            success=True,
            output=f"Successfully scheduled job {job.job_id}. Next execution at {next_dt}.",
            metadata={"job_id": job.job_id, "next_run": next_dt},
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to schedule cron: {e}")


@tool(name="list_cron_jobs", description="List all scheduled active automations.", toolset="cronjob")
def list_cron_jobs() -> ToolResult:
    jobs = _scheduler.list_jobs()
    if not jobs:
        return ToolResult(success=True, output="No active cron jobs scheduled.")

    lines = []
    for j in jobs:
        next_dt = time.ctime(j.next_run)
        lines.append(f"- **ID: {j.job_id}** | Cron: `{j.expression}` | Next: {next_dt}\n  Prompt: {j.prompt}")
    return ToolResult(success=True, output="\n".join(lines))


@tool(name="cancel_cron_job", description="Cancel an active cron job by its job ID.", toolset="cronjob")
def cancel_cron_job(job_id: str) -> ToolResult:
    ok = _scheduler.cancel_job(job_id)
    if ok:
        return ToolResult(success=True, output=f"Cron job {job_id} successfully cancelled.")
    return ToolResult(success=False, output="", error=f"Cron job {job_id} not found.")
