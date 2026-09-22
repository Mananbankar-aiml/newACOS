from typing import Optional
from core.db import db, new_id, utcnow_iso


async def audit(actor: str, action: str, module: str, details: str, agent: Optional[str] = None) -> None:
    await db.audit_logs.insert_one({
        "id": new_id(),
        "timestamp": utcnow_iso(),
        "actor": actor,
        "agent": agent,
        "module": module,
        "action": action,
        "details": details,
    })
