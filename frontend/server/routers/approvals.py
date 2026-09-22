from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.audit import audit
from core.db import db, utcnow_iso
from core.mailer import send_email
from core.security import current_user, require_step_up, role_of

router = APIRouter(tags=["approvals"])


class ApprovalDecision(BaseModel):
    decision: str
    note: Optional[str] = ""


async def _apply_action(action: dict, decided_by: str) -> Optional[str]:
    """Execute the side effect an agent proposed, only after a human approved it."""
    kind = action.get("type")
    if kind == "pay_invoice":
        await db.invoices.update_one({"id": action["invoice_id"]}, {"$set": {"status": "paid", "paid_at": utcnow_iso(), "paid_by": decided_by}})
        return f"Invoice {action['invoice_id']} marked paid"
    if kind == "lead_stage":
        await db.leads.update_one({"id": action["lead_id"]}, {"$set": {"stage": action["stage"], "updated_at": utcnow_iso()}})
        return f"Lead {action['lead_id']} -> {action['stage']}"
    if kind == "contract_risk":
        await db.contracts.update_one({"id": action["contract_id"]}, {"$set": {"risk": action["risk"], "updated_at": utcnow_iso()}})
        return f"Contract {action['contract_id']} risk -> {action['risk']}"
    if kind == "purchase":
        await db.inventory.update_one({"id": action["item_id"]}, {"$inc": {"on_order": int(action["quantity"])}, "$set": {"updated_at": utcnow_iso()}})
        return f"{action['quantity']} units put on order for item {action['item_id']}"
    return None


@router.get("/approvals")
async def list_approvals(user: dict = Depends(current_user)):
    if role_of(user) == "employee":
        raise HTTPException(403, "Employees cannot view the approvals queue")
    return await db.approvals.find({"is_deleted": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, inp: ApprovalDecision, user: dict = Depends(require_step_up("approval"))):
    if role_of(user) not in {"admin", "manager"}:
        raise HTTPException(403, "Only admin/manager can decide")
    if inp.decision not in {"approve", "reject"}:
        raise HTTPException(400, "Invalid decision")
    approval = await db.approvals.find_one({"id": approval_id}, {"_id": 0})
    if not approval:
        raise HTTPException(404, "Approval not found")
    if approval.get("status") != "pending":
        raise HTTPException(409, "Approval already decided")
    new_status = "approved" if inp.decision == "approve" else "rejected"
    applied = None
    if new_status == "approved" and approval.get("proposed_action"):
        applied = await _apply_action(approval["proposed_action"], user["email"])
    await db.approvals.update_one({"id": approval_id}, {"$set": {
        "status": new_status, "decided_by": user["email"], "decided_at": utcnow_iso(), "note": inp.note, "applied_effect": applied}})
    if approval.get("task_id"):
        await db.agent_tasks.update_many({"conversation_id": approval["task_id"], "status": "pending_approval"}, {"$set": {"status": new_status}})
    await audit(user["email"], f"approval_{new_status}", "approvals", f"Approval '{approval.get('title')}' {new_status}" + (f" · {applied}" if applied else ""))
    requester = approval.get("requested_by") or ""
    if "@" in requester:
        html = f"<div style='font-family:Arial,sans-serif;padding:32px'><h2>Approval {new_status}</h2><p>{approval.get('title')}</p><p>Decided by {user['email']}. Note: {inp.note or '—'}</p></div>"
        await send_email(requester, f"[ACOS] Approval {new_status}", html, "approval-notice")
    return {"ok": True, "status": new_status, "applied_effect": applied}
