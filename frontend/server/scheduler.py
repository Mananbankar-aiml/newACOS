"""In-process scheduler for long-running hosts. On serverless, use `POST /api/internal/scheduler/tick` from a cron."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from agents.runner import record_task, run_agent
from core.audit import audit
from core.db import db, utcnow_iso
from core.guardrails import assess

logger = logging.getLogger(__name__)
SYSTEM_ACTOR = {"id": "scheduler", "email": "scheduler@acos.io", "name": "Scheduler", "role": "manager"}


async def tick() -> int:
    ran = 0
    now = datetime.now(timezone.utc)
    async for sched in db.schedules.find({"enabled": True}):
        try:
            due = datetime.fromisoformat(sched["next_run_at"])
        except (KeyError, ValueError):
            continue
        if now < due:
            continue
        agent_key = sched["agent_key"]
        goal = assess(sched.get("goal") or "Routine background check").text
        next_run = (now + timedelta(minutes=sched["cadence_minutes"])).isoformat()
        try:
            result = await asyncio.wait_for(run_agent(agent_key, goal, SYSTEM_ACTOR, None), timeout=120)
            await record_task(agent_key, goal, result, SYSTEM_ACTOR["email"], None)
            await audit(SYSTEM_ACTOR["email"], "scheduled_run", "agents", f"Scheduled {agent_key} run · conf {result['confidence']}", agent=agent_key)
            ran += 1
        except Exception:
            logger.exception("scheduled run for %s failed", agent_key)
        await db.schedules.update_one({"agent_key": agent_key}, {"$set": {"last_run_at": utcnow_iso(), "next_run_at": next_run}})
    return ran


async def loop(interval_seconds: int = 30) -> None:
    while True:
        try:
            await tick()
        except Exception:
            logger.exception("scheduler tick failed")
        await asyncio.sleep(interval_seconds)
