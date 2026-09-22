from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from core.db import db

bearer = HTTPBearer(auto_error=False)

WRITER_ROLES = {"admin", "manager"}
ALL_ROLES = {"admin", "manager", "employee", "auditor"}


def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def verify_password(pwd: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: str, role: str, days: int = 7) -> str:
    payload = {"sub": user_id, "role": role, "exp": datetime.now(timezone.utc) + timedelta(days=days)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def create_step_up_token(user_id: str, role: str, purpose: str) -> str:
    payload = {"sub": user_id, "role": role, "purpose": purpose,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


async def current_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> Dict[str, Any]:
    if not cred:
        raise HTTPException(401, "Missing token")
    try:
        payload = jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


def role_of(user: dict) -> str:
    return user.get("role", "employee")


def can_write(user: dict) -> bool:
    return role_of(user) in WRITER_ROLES


def require_roles(*roles: str):
    async def _dep(user: dict = Depends(current_user)) -> dict:
        if role_of(user) not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return user
    return _dep


def require_writer(user: dict) -> None:
    if not can_write(user):
        raise HTTPException(403, "Only admin/manager can modify data")


def filter_by_role(items: List[dict], user: dict, self_field: Optional[str] = None) -> List[dict]:
    if role_of(user) in {"admin", "auditor", "manager"} or not self_field:
        return items
    email = user.get("email")
    return [x for x in items if x.get(self_field) == email]


def require_step_up(purpose: str):
    async def _dep(x_otp_token: Optional[str] = Header(None), user: dict = Depends(current_user)) -> dict:
        if role_of(user) != "admin":
            return user
        if not x_otp_token:
            raise HTTPException(428, "Step-up (OTP) required")
        try:
            payload = jwt.decode(x_otp_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        except jwt.PyJWTError:
            raise HTTPException(428, "Invalid step-up token")
        if payload.get("purpose") != purpose or payload.get("sub") != user["id"]:
            raise HTTPException(428, "Step-up purpose mismatch")
        return user
    return _dep
