from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends

from core.db import db
from core.security import current_user, require_roles
from ml.anomaly import score_invoices
from ml.evaluate import evaluate

router = APIRouter(tags=["insights"])
LIVE = {"is_deleted": {"$ne": True}}


async def _sum(query: dict) -> float:
    total = 0.0
    async for inv in db.invoices.find({**query, **LIVE}, {"_id": 0, "amount": 1}):
        total += float(inv.get("amount") or 0)
    return total


@router.get("/dashboard/kpis")
async def dashboard_kpis(user: dict = Depends(current_user)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_tasks = await db.agent_tasks.find({"created_at": {"$gte": today_start}}, {"_id": 0, "confidence": 1}).to_list(500)
    if today_tasks:
        confidence_avg = round(sum(t.get("confidence", 0) for t in today_tasks) / len(today_tasks))
    else:
        confs = [a.get("last_confidence") or a.get("confidence") for a in await db.agents.find({}, {"_id": 0}).to_list(50)]
        confs = [c for c in confs if c]
        confidence_avg = round(sum(confs) / len(confs)) if confs else None
    return {
        "employees": await db.employees.count_documents(LIVE),
        "invoices": await db.invoices.count_documents(LIVE),
        "inventory_items": await db.inventory.count_documents(LIVE),
        "leads": await db.leads.count_documents(LIVE),
        "pending_approvals": await db.approvals.count_documents({"status": "pending"}),
        "active_agents": await db.agents.count_documents({"status": "active"}),
        "revenue": await _sum({"status": "paid"}),
        "cash_burn": await _sum({"status": {"$in": ["unpaid", "overdue"]}}),
        "tasks_today": len(today_tasks),
        "confidence_avg": confidence_avg,
    }


@router.get("/analytics/summary")
async def analytics_summary(user: dict = Depends(current_user)):
    now = datetime.now(timezone.utc)
    months: List[tuple] = []
    for offset in range(5, -1, -1):
        month, year = now.month - offset, now.year
        while month <= 0:
            month, year = month + 12, year - 1
        months.append((f"{year:04d}-{month:02d}", datetime(year, month, 1).strftime("%b")))
    rev: Dict[str, float] = {k: 0.0 for k, _ in months}
    appr: Dict[str, int] = {k: 0 for k, _ in months}
    runs: Dict[str, int] = {k: 0 for k, _ in months}
    async for inv in db.invoices.find({"status": "paid", **LIVE}, {"_id": 0, "amount": 1, "created_at": 1}):
        ym = (inv.get("created_at") or "")[:7]
        if ym in rev:
            rev[ym] += float(inv.get("amount") or 0)
    async for a in db.approvals.find({}, {"_id": 0, "created_at": 1}):
        ym = (a.get("created_at") or "")[:7]
        if ym in appr:
            appr[ym] += 1
    async for t in db.agent_tasks.find({}, {"_id": 0, "created_at": 1}):
        ym = (t.get("created_at") or "")[:7]
        if ym in runs:
            runs[ym] += 1

    anomalies: List[dict] = []
    for inv in await db.invoices.find({"status": "overdue", **LIVE}, {"_id": 0}).to_list(50):
        amt = float(inv.get("amount") or 0)
        anomalies.append({"module": "Finance", "severity": "high" if amt > 10000 else "medium" if amt > 2000 else "low",
                          "message": f"Invoice {inv.get('number', '?')} ({inv.get('vendor', '?')}) is overdue — ${amt:,.0f}."})
    ml_report = score_invoices(await db.invoices.find(LIVE, {"_id": 0}).to_list(500))
    for r in ml_report["results"]:
        if r["is_anomaly"] and r["severity"] != "low":
            anomalies.append({"module": "Finance/ML", "severity": r["severity"],
                              "message": f"Invoice {r['number']} ({r['vendor']}) anomaly score {r['anomaly_score']:.2f}: {'; '.join(r['reasons'][:2])}"})
    for item in await db.inventory.find(LIVE, {"_id": 0}).to_list(300):
        stock, rp = int(item.get("stock") or 0), int(item.get("reorder_at") or 0)
        if rp > 0 and stock <= rp:
            anomalies.append({"module": "Inventory", "severity": "high" if stock == 0 else "medium" if stock < rp // 2 else "low",
                              "message": f"SKU {item.get('sku', '?')} ({item.get('name', '?')}) has {stock} units — reorder threshold is {rp}."})
    for emp in await db.employees.find(LIVE, {"_id": 0}).to_list(300):
        att = int(emp.get("attendance") or 100)
        if att < 80:
            anomalies.append({"module": "HR", "severity": "high" if att < 60 else "medium", "message": f"{emp.get('name', '?')} has {att}% attendance this period."})
    order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda x: order.get(x["severity"], 3))
    for i, a in enumerate(anomalies, 1):
        a["id"] = f"a{i}"
    return {"months": [m for _, m in months], "revenue": [round(rev[k]) for k, _ in months],
            "approvals": [appr[k] for k, _ in months], "agent_runs": [runs[k] for k, _ in months], "anomalies": anomalies[:12]}


@router.get("/finance/anomalies")
async def finance_anomalies(user: dict = Depends(require_roles("admin", "manager", "auditor"))):
    return score_invoices(await db.invoices.find(LIVE, {"_id": 0}).to_list(500))


@router.get("/ml/evaluate")
async def ml_evaluate(n: int = 200, fraud_rate: float = 0.1, seed: int = 42, user: dict = Depends(require_roles("admin", "manager", "auditor"))):
    return evaluate(n=min(max(n, 30), 2000), fraud_rate=min(max(fraud_rate, 0.01), 0.5), seed=seed)
