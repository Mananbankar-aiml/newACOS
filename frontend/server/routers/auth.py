import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, ConfigDict, EmailStr

from core.audit import audit
from core.config import settings
from core.db import db, new_id, utcnow_iso
from core.mailer import otp_email, send_email
from core.security import (create_step_up_token, create_token, current_user, hash_password, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])


class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: EmailStr
    name: str
    role: str
    avatar: Optional[str] = None
    email_verified: bool = False
    auth_provider: Optional[str] = None


class TokenOut(BaseModel):
    token: str
    user: UserOut


class RegisterInput(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class GoogleInput(BaseModel):
    credential: str


class VerifyEmailInput(BaseModel):
    otp: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None


class PasswordChangeInput(BaseModel):
    current_password: str
    new_password: str


class ForgotInput(BaseModel):
    email: EmailStr


class ResetInput(BaseModel):
    token: str
    new_password: str


class OtpRequestInput(BaseModel):
    purpose: str = "approval"


class OtpVerifyInput(BaseModel):
    otp: str
    purpose: str


def _gen_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _check_password_strength(pwd: str) -> None:
    if len(pwd) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")


async def _issue_otp(user: dict, purpose: str, minutes: int) -> str:
    otp = _gen_otp()
    await db.otps.insert_one({
        "id": new_id(), "user_id": user["id"], "email": user["email"], "otp": otp, "purpose": purpose, "used": False,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(), "created_at": utcnow_iso(),
    })
    return otp


def _demo_hint(otp: str) -> Optional[str]:
    return otp if settings.DEBUG_OTP and not settings.RESEND_API_KEY else None


@router.post("/register", response_model=TokenOut)
async def register(inp: RegisterInput):
    if await db.users.find_one({"email": inp.email.lower()}):
        raise HTTPException(400, "Email already registered")
    _check_password_strength(inp.password)
    doc = {"id": new_id(), "email": inp.email.lower(), "name": inp.name, "password": hash_password(inp.password),
           "role": "pending", "avatar": None, "email_verified": False, "auth_provider": "password", "created_at": utcnow_iso()}
    await db.users.insert_one(doc)
    otp = await _issue_otp(doc, "verify_email", 15)
    await send_email(doc["email"], "ACOS · verify your email", otp_email("Verify your email", "Use this 6-digit code to verify your account:", otp, "15 minutes"), "verify_email")
    await audit(doc["email"], "register", "auth", f"New user {inp.name} registered (pending role)")
    return TokenOut(token=create_token(doc["id"], doc["role"]), user=UserOut(**doc))


@router.post("/login", response_model=TokenOut)
async def login(inp: LoginInput):
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user or not verify_password(inp.password, user.get("password", "")):
        raise HTTPException(401, "Invalid credentials")
    await audit(user["email"], "login", "auth", "User logged in")
    return TokenOut(token=create_token(user["id"], user["role"]), user=UserOut(**user))


@router.post("/google", response_model=TokenOut)
async def google_login(inp: GoogleInput):
    """Verify a Google Identity Services ID token directly with Google, then upsert the user."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google sign-in is not configured")
    try:
        info = await asyncio.to_thread(google_id_token.verify_oauth2_token, inp.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(401, "Invalid Google token")
    if info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"} or not info.get("email_verified"):
        raise HTTPException(401, "Google token not trusted")
    email = info["email"].lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.users.update_one({"id": existing["id"]}, {"$set": {
            "name": info.get("name", existing.get("name")), "avatar": info.get("picture", existing.get("avatar")),
            "email_verified": True, "google_sub": info.get("sub")}})
        user_id = existing["id"]
    else:
        user_id = new_id()
        await db.users.insert_one({
            "id": user_id, "email": email, "name": info.get("name") or email.split("@")[0], "avatar": info.get("picture"),
            "password": hash_password(secrets.token_urlsafe(32)), "role": "pending", "auth_provider": "google",
            "google_sub": info.get("sub"), "email_verified": True, "created_at": utcnow_iso()})
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    await audit(email, "google_login", "auth", "Signed in with Google")
    return TokenOut(token=create_token(user_id, user["role"]), user=UserOut(**user))


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(current_user)):
    return UserOut(**user)


@router.put("/me", response_model=UserOut)
async def update_profile(inp: ProfileUpdate, user: dict = Depends(current_user)):
    patch = {k: v for k, v in inp.model_dump(exclude_none=True).items() if v != ""}
    if not patch:
        raise HTTPException(400, "Nothing to update")
    if "email" in patch and patch["email"] != user["email"]:
        if await db.users.find_one({"email": patch["email"]}):
            raise HTTPException(400, "Email already in use")
        patch["email_verified"] = False
    await db.users.update_one({"id": user["id"]}, {"$set": patch})
    await audit(user["email"], "profile_update", "auth", f"Updated: {', '.join(patch.keys())}")
    return UserOut(**await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0}))


@router.post("/change-password")
async def change_password(inp: PasswordChangeInput, user: dict = Depends(current_user)):
    doc = await db.users.find_one({"id": user["id"]})
    if not verify_password(inp.current_password, doc["password"]):
        raise HTTPException(401, "Current password is incorrect")
    _check_password_strength(inp.new_password)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password": hash_password(inp.new_password)}})
    await audit(user["email"], "password_change", "auth", "Password changed")
    return {"ok": True}


@router.post("/verify-email")
async def verify_email(inp: VerifyEmailInput, user: dict = Depends(current_user)):
    doc = await db.otps.find_one({"email": user["email"], "otp": inp.otp, "purpose": "verify_email", "used": False})
    if not doc or datetime.now(timezone.utc) > datetime.fromisoformat(doc["expires_at"]):
        raise HTTPException(400, "Invalid or expired code")
    await db.otps.update_one({"id": doc["id"]}, {"$set": {"used": True}})
    await db.users.update_one({"id": user["id"]}, {"$set": {"email_verified": True}})
    await audit(user["email"], "verify_email", "auth", "Email verified via OTP")
    return {"ok": True, "email_verified": True}


@router.post("/verify-email/resend")
async def resend_verification(user: dict = Depends(current_user)):
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    otp = await _issue_otp(user, "verify_email", 15)
    await send_email(user["email"], "ACOS · verification code", otp_email("New verification code", "Your ACOS verification code:", otp, "15 minutes"), "verify_email")
    return {"ok": True, "demo_hint": _demo_hint(otp)}


@router.post("/forgot")
async def forgot_password(inp: ForgotInput):
    user = await db.users.find_one({"email": inp.email.lower()})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_resets.insert_one({"id": new_id(), "email": user["email"], "token": token, "used": False,
                                             "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(), "created_at": utcnow_iso()})
        link = f'<a href="{settings.FRONTEND_URL}/reset?token={token}">Reset your password</a>' if settings.FRONTEND_URL else f"Reset token: <b>{token}</b>"
        html = f"<div style='font-family:Arial,sans-serif;padding:32px'><h2>ACOS — password reset</h2><p>{link}</p><p style='font-size:12px'>Expires in 30 minutes.</p></div>"
        await send_email(user["email"], "ACOS — reset your password", html, "reset")
        await audit(user["email"], "forgot_password", "auth", "Reset requested")
    return {"ok": True, "message": "If an account exists, we've sent instructions."}


@router.post("/reset")
async def reset_password(inp: ResetInput):
    doc = await db.password_resets.find_one({"token": inp.token, "used": False})
    if not doc or datetime.now(timezone.utc) > datetime.fromisoformat(doc["expires_at"]):
        raise HTTPException(400, "Invalid or expired token")
    _check_password_strength(inp.new_password)
    await db.users.update_one({"email": doc["email"]}, {"$set": {"password": hash_password(inp.new_password)}})
    await db.password_resets.update_one({"token": inp.token}, {"$set": {"used": True, "used_at": utcnow_iso()}})
    await audit(doc["email"], "reset_password", "auth", "Password reset via email token")
    return {"ok": True}


@router.post("/otp/request")
async def request_otp(inp: OtpRequestInput, user: dict = Depends(current_user)):
    window_start = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    if await db.otps.count_documents({"email": user["email"], "purpose": inp.purpose, "created_at": {"$gt": window_start}}) >= 3:
        raise HTTPException(429, "Too many OTP requests — wait 5 minutes")
    otp = await _issue_otp(user, inp.purpose, 5)
    await send_email(user["email"], "ACOS · verification code", otp_email("Verification code", f"One-time code for <b>{inp.purpose}</b>:", otp, "5 minutes"), f"otp-{inp.purpose}")
    await audit(user["email"], "otp_requested", "auth", f"OTP requested for {inp.purpose}")
    return {"ok": True, "demo_hint": _demo_hint(otp)}


@router.post("/otp/verify")
async def verify_otp(inp: OtpVerifyInput, user: dict = Depends(current_user)):
    doc = await db.otps.find_one({"email": user["email"], "otp": inp.otp, "purpose": inp.purpose, "used": False})
    if not doc or datetime.now(timezone.utc) > datetime.fromisoformat(doc["expires_at"]):
        raise HTTPException(400, "Invalid or expired code")
    await db.otps.update_one({"id": doc["id"]}, {"$set": {"used": True}})
    await audit(user["email"], "otp_verified", "auth", f"OTP verified for {inp.purpose}")
    return {"ok": True, "step_up_token": create_step_up_token(user["id"], user["role"], inp.purpose)}
