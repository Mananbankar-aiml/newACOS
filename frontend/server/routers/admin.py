import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.prompts import AGENTS
from core.audit import audit
from core.db import db, new_id, utcnow_iso
from core.security import current_user, require_roles

router = APIRouter(tags=["admin"])


class ScheduleInput(BaseModel):
    enabled: bool
    cadence_minutes: int
    goal: Optional[str] = None


@router.get("/audit-logs")
async def list_audit(user: dict = Depends(require_roles("admin", "manager"))):
    return await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(200)


@router.get("/emails")
async def list_emails(user: dict = Depends(require_roles("admin", "auditor"))):
    return await db.emails.find({}, {"_id": 0, "html": 0}).sort("sent_at", -1).to_list(100)


@router.get("/schedules")
async def list_schedules(user: dict = Depends(current_user)):
    return await db.schedules.find({}, {"_id": 0}).to_list(50)


@router.put("/schedules/{agent_key}")
async def update_schedule(agent_key: str, inp: ScheduleInput, user: dict = Depends(require_roles("admin"))):
    if agent_key not in AGENTS:
        raise HTTPException(404, "Unknown agent")
    if not 1 <= inp.cadence_minutes <= 1440:
        raise HTTPException(400, "cadence_minutes must be 1..1440")
    doc = {"agent_key": agent_key, "enabled": inp.enabled, "cadence_minutes": inp.cadence_minutes,
           "goal": inp.goal or "Perform routine background check and produce digest.",
           "next_run_at": (datetime.now(timezone.utc) + timedelta(minutes=inp.cadence_minutes)).isoformat(),
           "updated_by": user["email"], "updated_at": utcnow_iso()}
    await db.schedules.update_one({"agent_key": agent_key}, {"$set": doc}, upsert=True)
    await audit(user["email"], "schedule_update", "settings", f"Schedule for {agent_key}: enabled={inp.enabled}, cadence={inp.cadence_minutes}m")
    return doc


@router.post("/admin/seed-demo")
async def seed_demo(user: dict = Depends(require_roles("admin"))):
    now = utcnow_iso()
    base = {"created_at": now, "created_by": user["email"], "is_deleted": False, "seeded": True}
    first = ["Sarah", "Raj", "Emma", "Lin", "Marcus", "Priya", "Diego", "Yuki", "Aisha", "Tom", "Fatima", "Noah", "Zara", "Ivan", "Chloe", "Jamal"]
    last = ["Chen", "Patel", "Watson", "Wu", "Silva", "Kim", "Garcia", "Tanaka", "Khan", "Reed"]
    vendors = ["AWS", "Google Workspace", "Slack", "Notion", "Figma", "Datadog", "Cloudflare", "Acme Corp", "Office Supplies Inc", "Legal LLP"]
    companies = ["Acme Corp", "Globex", "Initech", "Umbrella", "Wayne Ent", "Stark Ind", "Cyberdyne", "Hooli", "Pied Piper"]
    employees = []
    for _ in range(30):
        n = f"{random.choice(first)} {random.choice(last)}"
        employees.append({**base, "id": new_id(), "name": n, "email": f"{n.lower().replace(' ', '.')}@yourco.com",
                          "department": random.choice(["Engineering", "Sales", "Finance", "HR", "Operations"]), "team": random.choice(["Engineering", "Sales", "Finance", "HR", "Operations"]),
                          "role": random.choice(["Engineer", "Manager", "Analyst", "Lead"]), "manager": random.choice(first), "salary": random.randint(55, 190) * 1000,
                          "status": random.choices(["present", "on_leave"], weights=[9, 1])[0], "attendance": random.randint(70, 100)})
    invoices = []
    for i in range(50):
        v = random.choice(vendors)
        invoices.append({**base, "id": new_id(), "number": f"INV-{2000 + i}", "vendor": v, "amount": round(random.lognormvariate(7.2, 0.6), 2),
                         "due": f"2026-{random.randint(1, 6):02d}-{random.randint(1, 28):02d}", "status": random.choices(["unpaid", "paid", "overdue"], weights=[5, 4, 1])[0],
                         "category": random.choice(["cloud", "saas", "legal", "office"])})
    # Planted anomalies so the ML scan has something real to find
    dup = random.choice(invoices)
    invoices.append({**dup, "id": new_id(), "number": "INV-2090"})
    invoices.append({**base, "id": new_id(), "number": "INV-2091", "vendor": "Legal LLP", "amount": 4985.00, "due": "2026-05-30", "status": "unpaid", "category": "legal"})
    invoices.append({**base, "id": new_id(), "number": "INV-2092", "vendor": "NewShell Consulting", "amount": 38000.00, "due": "2026-06-10", "status": "unpaid", "category": "consulting"})
    inventory = [{**base, "id": new_id(), "sku": f"SKU-{1000 + i}", "name": f"{random.choice(['Widget', 'Cable', 'Sensor', 'Bracket'])} {chr(65 + i % 26)}",
                  "category": random.choice(["Hardware", "Electronics", "Packaging"]), "stock": random.randint(0, 200), "reorder_at": random.randint(15, 40),
                  "unit_cost": round(random.uniform(0.5, 85), 2), "supplier": random.choice(["Acme", "GlobalParts", "Nova Supplies"])} for i in range(60)]
    leads = []
    for _ in range(25):
        n = f"{random.choice(first)} {random.choice(last)}"
        leads.append({**base, "id": new_id(), "name": random.choice(companies), "contact": n, "company": random.choice(companies),
                      "stage": random.choice(["new", "qualified", "proposal", "negotiation", "won", "lost"]), "value": random.randint(2, 250) * 1000,
                      "owner": random.choice(first), "score": random.randint(20, 100)})
    contracts = [{**base, "id": new_id(), "title": f"MSA {random.choice(companies)}", "party": random.choice(companies),
                  "expires": f"2026-{random.randint(6, 12):02d}-{random.randint(1, 28):02d}", "value": random.randint(15, 500) * 1000,
                  "status": random.choice(["active", "expiring", "review"]), "risk": random.choice(["low", "medium", "high"])} for _ in range(8)]
    counts = {}
    for name, docs in [("employees", employees), ("invoices", invoices), ("inventory", inventory), ("leads", leads), ("contracts", contracts)]:
        await db[name].insert_many(docs)
        counts[name] = len(docs)
    await audit(user["email"], "seed_demo", "system", f"Seeded demo data: {counts}")
    return {"ok": True, "counts": counts}


@router.post("/admin/wipe-demo")
async def wipe_demo(user: dict = Depends(require_roles("admin"))):
    counts = {}
    for name in ["employees", "invoices", "inventory", "leads", "contracts"]:
        counts[name] = (await db[name].delete_many({"seeded": True})).deleted_count
    await audit(user["email"], "wipe_demo", "system", f"Wiped demo data: {counts}")
    return {"ok": True, "counts": counts}
