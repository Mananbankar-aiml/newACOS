"""Idempotent bootstrap: agents/schedules are upserted by key, demo records only on an empty DB."""
import logging
import secrets

from agents.prompts import AGENTS
from core.audit import audit
from core.config import settings
from core.db import db, new_id, utcnow_iso
from core.security import hash_password
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def ensure_agents_and_schedules() -> None:
    for key, meta in AGENTS.items():
        await db.agents.update_one({"key": key}, {
            "$set": {"name": meta["name"], "specialty": meta["specialty"]},
            "$setOnInsert": {"id": new_id(), "status": "active", "confidence": 80, "last_run": None},
        }, upsert=True)
        await db.schedules.update_one({"agent_key": key}, {"$setOnInsert": {
            "enabled": False, "cadence_minutes": 60, "goal": "Perform routine background check and produce digest.",
            "next_run_at": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(), "updated_by": "system", "updated_at": utcnow_iso(),
        }}, upsert=True)


async def seed_demo_records() -> None:
    if await db.users.count_documents({}) > 0:
        return
    creds = {f"{role}@acos.io": secrets.token_urlsafe(16) for role in ["admin", "manager", "employee", "auditor"]}
    names = {"admin": "Ava Reyes", "manager": "Marcus Nolan", "employee": "Elena Park", "auditor": "Kenji Ito"}
    users = [{"id": new_id(), "email": email, "name": names[email.split("@")[0]], "role": email.split("@")[0],
              "password": hash_password(pwd), "email_verified": True, "auth_provider": "password", "created_at": utcnow_iso()}
             for email, pwd in creds.items()]
    await db.users.insert_many(users)
    logger.info("=" * 60)
    logger.info("SEED USER CREDENTIALS (first run only — save these now):")
    for email, pwd in creds.items():
        logger.info("  %s  ->  %s", email, pwd)
    logger.info("=" * 60)

    base = {"created_at": utcnow_iso(), "created_by": "system", "is_deleted": False}
    await db.employees.insert_many([
        {**base, "id": new_id(), "name": "Elena Park", "role": "Ops Engineer", "team": "Ops", "status": "present", "attendance": 96, "email": "employee@acos.io"},
        {**base, "id": new_id(), "name": "Rohan Batra", "role": "Backend Dev", "team": "Engineering", "status": "on_leave", "attendance": 87, "email": "rohan@acos.io"},
        {**base, "id": new_id(), "name": "Sara Aziz", "role": "Recruiter", "team": "HR", "status": "present", "attendance": 99, "email": "sara@acos.io"},
        {**base, "id": new_id(), "name": "Diego Ramos", "role": "Sales Rep", "team": "Sales", "status": "present", "attendance": 74, "email": "diego@acos.io"},
        {**base, "id": new_id(), "name": "Yuki Tanaka", "role": "Designer", "team": "Product", "status": "remote", "attendance": 92, "email": "yuki@acos.io"},
    ])
    await db.leaves.insert_many([
        {**base, "id": new_id(), "employee": "Rohan Batra", "employee_email": "rohan@acos.io", "type": "Sick leave", "days": 3, "status": "approved", "start": "2026-06-10"},
        {**base, "id": new_id(), "employee": "Diego Ramos", "employee_email": "diego@acos.io", "type": "Personal", "days": 2, "status": "pending", "start": "2026-06-22"},
        {**base, "id": new_id(), "employee": "Yuki Tanaka", "employee_email": "yuki@acos.io", "type": "Vacation", "days": 7, "status": "pending", "start": "2026-07-04"},
    ])
    await db.invoices.insert_many([
        {**base, "id": new_id(), "number": "INV-2041", "vendor": "CloudNet Systems", "amount": 8420, "status": "paid", "due": "2026-05-15"},
        {**base, "id": new_id(), "number": "INV-2042", "vendor": "PixelPress Print", "amount": 1250, "status": "paid", "due": "2026-05-22"},
        {**base, "id": new_id(), "number": "INV-2043", "vendor": "Northwind Logistics", "amount": 15600, "status": "unpaid", "due": "2026-06-28"},
        {**base, "id": new_id(), "number": "INV-2044", "vendor": "Aurora Design Studio", "amount": 6300, "status": "overdue", "due": "2026-05-08"},
        {**base, "id": new_id(), "number": "INV-2045", "vendor": "Silverline Legal", "amount": 22400, "status": "paid", "due": "2026-06-01"},
        {**base, "id": new_id(), "number": "INV-2046", "vendor": "Silverline Legal", "amount": 4990, "status": "unpaid", "due": "2026-06-20"},
        {**base, "id": new_id(), "number": "INV-2047", "vendor": "Aurora Design Studio", "amount": 6300, "status": "unpaid", "due": "2026-06-30"},
    ])
    await db.inventory.insert_many([
        {**base, "id": new_id(), "sku": "CBL-USB-C", "name": "USB-C Cable 1m", "stock": 42, "reorder_at": 60, "supplier": "CableWorks", "unit_cost": 4.2},
        {**base, "id": new_id(), "sku": "MON-27-4K", "name": '27" 4K Monitor', "stock": 6, "reorder_at": 8, "supplier": "PixelHouse", "unit_cost": 410},
        {**base, "id": new_id(), "sku": "CHR-LTP-65", "name": "Laptop Charger 65W", "stock": 24, "reorder_at": 20, "supplier": "PowerPlus", "unit_cost": 29},
        {**base, "id": new_id(), "sku": "PEN-BLU-01", "name": "Blue Pen (pack of 12)", "stock": 130, "reorder_at": 50, "supplier": "OfficePro", "unit_cost": 3.1},
        {**base, "id": new_id(), "sku": "CHR-USB-45", "name": "USB-C Charger 45W", "stock": 3, "reorder_at": 10, "supplier": "PowerPlus", "unit_cost": 22},
    ])
    await db.leads.insert_many([
        {**base, "id": new_id(), "name": "Northstar Robotics", "contact": "Priya Menon", "score": 92, "stage": "proposal", "value": 84000},
        {**base, "id": new_id(), "name": "Meridian Bank", "contact": "Alan Cho", "score": 74, "stage": "discovery", "value": 220000},
        {**base, "id": new_id(), "name": "Verdant Labs", "contact": "Chloe Green", "score": 61, "stage": "qualification", "value": 45000},
        {**base, "id": new_id(), "name": "Orbital Health", "contact": "Sunil Rao", "score": 88, "stage": "negotiation", "value": 132000},
    ])
    await db.contracts.insert_many([
        {**base, "id": new_id(), "title": "SaaS Master Agreement — CloudNet", "party": "CloudNet Systems", "expires": "2026-06-30", "risk": "low"},
        {**base, "id": new_id(), "title": "NDA — Meridian Bank", "party": "Meridian Bank", "expires": "2026-07-15", "risk": "medium"},
        {**base, "id": new_id(), "title": "Supply Contract — Northwind", "party": "Northwind Logistics", "expires": "2026-06-28", "risk": "high"},
        {**base, "id": new_id(), "title": "Employment Contract — Y. Tanaka", "party": "Internal", "expires": "2027-01-01", "risk": "low"},
    ])
    await audit("system", "seed", "system", "Initial demo data seeded")


async def bootstrap_admin() -> None:
    email = settings.BOOTSTRAP_ADMIN_EMAIL
    if not email or not settings.BOOTSTRAP_ADMIN_PASSWORD:
        return
    existing = await db.users.find_one({"email": email})
    if existing:
        if existing.get("role") != "admin":
            await db.users.update_one({"id": existing["id"]}, {"$set": {"role": "admin", "email_verified": True}})
            await audit("system", "bootstrap_admin", "auth", f"Promoted {email} to admin")
        return
    await db.users.insert_one({"id": new_id(), "email": email, "name": settings.BOOTSTRAP_ADMIN_NAME or email.split("@")[0],
                               "password": hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD), "role": "admin", "avatar": None,
                               "email_verified": True, "auth_provider": "password", "created_at": utcnow_iso()})
    await audit("system", "user_create", "auth", f"Bootstrap: created admin {email}")
