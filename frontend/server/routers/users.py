from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.audit import audit
from core.db import db
from core.security import ALL_ROLES, current_user, require_roles

router = APIRouter(prefix="/users", tags=["users"])


class RoleChangeInput(BaseModel):
    role: str


@router.get("")
async def list_users(user: dict = Depends(require_roles("admin", "auditor"))):
    return await db.users.find({}, {"_id": 0, "password": 0}).sort("created_at", -1).to_list(500)


@router.put("/{user_id}/role")
async def set_user_role(user_id: str, inp: RoleChangeInput, user: dict = Depends(require_roles("admin"))):
    if inp.role not in ALL_ROLES:
        raise HTTPException(400, "Invalid role")
    if user_id == user["id"] and inp.role != "admin":
        raise HTTPException(400, "You cannot demote yourself")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"role": inp.role}})
    await audit(user["email"], "role_change", "auth", f"{target['email']}: {target['role']} → {inp.role}")
    return {"ok": True, "role": inp.role}


@router.delete("/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles("admin"))):
    if user_id == user["id"]:
        raise HTTPException(400, "You cannot remove yourself")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    await db.users.delete_one({"id": user_id})
    await db.otps.delete_many({"user_id": user_id})
    await db.password_resets.delete_many({"email": target["email"]})
    await audit(user["email"], "user_delete", "auth", f"Removed member {target['email']} (was {target.get('role')})")
    return {"ok": True}
