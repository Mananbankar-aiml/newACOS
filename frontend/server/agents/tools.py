"""
Tool definitions and dispatch for agent tool-use.

Every tool is authorised against the calling human's RBAC role (never the model's request), and
irreversible / high-value actions are converted into approval-queue items instead of executed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.audit import audit
from core.db import db, new_id, utcnow_iso
from core.security import can_write, role_of
from ml.anomaly import score_invoices
from rag.retrieve import search_chunks, search_memory

ToolFn = Callable[["ToolContext", Dict[str, Any]], Awaitable[Any]]


class ToolContext:
    def __init__(self, user: dict, agent_key: str, conversation_id: Optional[str], depth: int = 0):
        self.user = user
        self.agent_key = agent_key
        self.conversation_id = conversation_id
        self.depth = depth
        self.delegate: Optional[Callable[..., Awaitable[dict]]] = None


def _slim(docs: List[dict], keys: List[str]) -> List[dict]:
    return [{k: d.get(k) for k in keys if d.get(k) is not None} for d in docs]


async def _live(collection: str, query: Optional[dict] = None, limit: int = 300) -> List[dict]:
    q = {"is_deleted": {"$ne": True}, **(query or {})}
    return await db[collection].find(q, {"_id": 0, "history": 0}).to_list(limit)


async def _create_approval(ctx: ToolContext, title: str, summary: str, risk: str, action: Optional[dict] = None) -> dict:
    doc = {
        "id": new_id(), "task_id": ctx.conversation_id, "agent": ctx.agent_key, "title": title,
        "summary": summary[:600], "risk": risk, "proposed_action": action,
        "confidence": None, "requested_by": ctx.user["email"], "status": "pending", "created_at": utcnow_iso(),
    }
    await db.approvals.insert_one(doc)
    await audit(ctx.user["email"], "approval_requested", "approvals", f"{ctx.agent_key} proposed: {title}", agent=ctx.agent_key)
    return {"approval_id": doc["id"], "status": "pending", "message": "Queued for human decision"}


# ---------------------------------------------------------------- shared tools

async def get_company_snapshot(ctx: ToolContext, _: dict) -> dict:
    live = {"is_deleted": {"$ne": True}}
    return {
        "employees": await db.employees.count_documents(live),
        "invoices": await db.invoices.count_documents(live),
        "overdue_invoices": await db.invoices.count_documents({**live, "status": "overdue"}),
        "inventory_skus": await db.inventory.count_documents(live),
        "leads": await db.leads.count_documents(live),
        "contracts": await db.contracts.count_documents(live),
        "pending_approvals": await db.approvals.count_documents({"status": "pending"}),
        "uploaded_documents": await db.files.count_documents({"is_deleted": False}),
    }


async def search_documents(ctx: ToolContext, args: dict) -> dict:
    hits = await search_chunks(args["query"], limit=int(args.get("limit", 5)), entity=args.get("entity"))
    return {"hits": hits, "note": "BM25 retrieval over uploaded document chunks"}


async def remember(ctx: ToolContext, args: dict) -> dict:
    doc = {"id": new_id(), "agent": ctx.agent_key if not args.get("shared") else "shared", "fact": args["fact"][:500],
           "tags": args.get("tags", [])[:6], "created_by": ctx.user["email"], "created_at": utcnow_iso()}
    await db.agent_memory.insert_one(doc)
    return {"stored": True, "memory_id": doc["id"]}


async def recall(ctx: ToolContext, args: dict) -> dict:
    return {"memories": await search_memory(ctx.agent_key, args["query"], int(args.get("limit", 5)))}


async def create_approval(ctx: ToolContext, args: dict) -> dict:
    return await _create_approval(ctx, args["title"], args["summary"], args.get("risk_level", "medium"), args.get("proposed_action"))


async def list_pending_approvals(ctx: ToolContext, _: dict) -> dict:
    docs = await db.approvals.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"approvals": _slim(docs, ["id", "agent", "title", "risk", "requested_by", "created_at"])}


# ---------------------------------------------------------------- HR

async def list_employees(ctx: ToolContext, args: dict) -> dict:
    q: dict = {}
    if args.get("team"):
        q["$or"] = [{"team": args["team"]}, {"department": args["team"]}]
    if args.get("status"):
        q["status"] = args["status"]
    docs = await _live("employees", q)
    if args.get("max_attendance") is not None:
        docs = [d for d in docs if int(d.get("attendance") or 100) <= int(args["max_attendance"])]
    if role_of(ctx.user) == "employee":
        docs = [d for d in docs if d.get("email") == ctx.user["email"]]
    return {"count": len(docs), "employees": _slim(docs, ["id", "name", "email", "role", "team", "department", "status", "attendance"])}


async def list_leaves(ctx: ToolContext, args: dict) -> dict:
    q = {"status": args["status"]} if args.get("status") else {}
    docs = await _live("leaves", q)
    if role_of(ctx.user) == "employee":
        docs = [d for d in docs if d.get("employee_email") == ctx.user["email"] or d.get("employee") == ctx.user.get("name")]
    return {"count": len(docs), "leaves": _slim(docs, ["id", "employee", "type", "days", "start", "status"])}


async def decide_leave(ctx: ToolContext, args: dict) -> dict:
    if not can_write(ctx.user):
        return {"error": "forbidden", "message": "Only admin/manager may decide leave; propose it via create_approval instead."}
    decision = args["decision"]
    if decision not in {"approved", "rejected"}:
        return {"error": "decision must be approved|rejected"}
    res = await db.leaves.update_one({"id": args["leave_id"], "is_deleted": {"$ne": True}},
                                     {"$set": {"status": decision, "decided_by": f"{ctx.agent_key}-agent/{ctx.user['email']}", "updated_at": utcnow_iso()}})
    if not res.matched_count:
        return {"error": "leave not found"}
    await audit(ctx.user["email"], "leave_decided", "hr", f"Leave {args['leave_id']} -> {decision}", agent=ctx.agent_key)
    return {"leave_id": args["leave_id"], "status": decision}


# ---------------------------------------------------------------- Finance

async def list_invoices(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden", "message": "Employees cannot view invoices"}
    q: dict = {}
    if args.get("status"):
        q["status"] = args["status"]
    if args.get("vendor"):
        q["vendor"] = {"$regex": args["vendor"], "$options": "i"}
    docs = await _live("invoices", q)
    for d in docs:
        d["due_date"] = d.get("due_date") or d.get("due")
    return {"count": len(docs), "invoices": _slim(docs, ["id", "number", "vendor", "amount", "status", "due_date", "flagged", "flag_reason"])}


async def run_anomaly_scan(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden"}
    report = score_invoices(await _live("invoices"))
    top = [r for r in report["results"] if r["is_anomaly"]][: int(args.get("limit", 10))]
    return {"model": report["model"], "n": report["n"], "flagged": report["flagged"], "benford": report["benford"], "top_anomalies": top}


async def flag_invoice(ctx: ToolContext, args: dict) -> dict:
    if not can_write(ctx.user):
        return {"error": "forbidden", "message": "Only admin/manager may flag invoices"}
    res = await db.invoices.update_one({"id": args["invoice_id"], "is_deleted": {"$ne": True}}, {"$set": {
        "flagged": True, "flag_reason": args["reason"][:300], "flag_severity": args.get("severity", "medium"),
        "flagged_by": f"{ctx.agent_key}-agent/{ctx.user['email']}", "flagged_at": utcnow_iso()}})
    if not res.matched_count:
        return {"error": "invoice not found"}
    await audit(ctx.user["email"], "invoice_flagged", "finance", f"Invoice {args['invoice_id']}: {args['reason'][:120]}", agent=ctx.agent_key)
    return {"invoice_id": args["invoice_id"], "flagged": True}


async def propose_payment(ctx: ToolContext, args: dict) -> dict:
    inv = await db.invoices.find_one({"id": args["invoice_id"], "is_deleted": {"$ne": True}}, {"_id": 0})
    if not inv:
        return {"error": "invoice not found"}
    amount = float(inv.get("amount") or 0)
    risk = "high" if amount >= 5000 else "medium"
    return await _create_approval(ctx, f"Release payment {inv.get('number')} — {inv.get('vendor')} ${amount:,.2f}",
                                  args.get("justification", ""), risk, {"type": "pay_invoice", "invoice_id": inv["id"], "amount": amount})


# ---------------------------------------------------------------- Inventory

async def list_inventory(ctx: ToolContext, args: dict) -> dict:
    docs = await _live("inventory")
    if args.get("below_reorder_only"):
        docs = [d for d in docs if int(d.get("stock") or 0) <= int(d.get("reorder_at") or 0)]
    return {"count": len(docs), "items": _slim(docs, ["id", "sku", "name", "stock", "reorder_at", "supplier", "unit_cost"])}


async def compute_reorder_plan(ctx: ToolContext, args: dict) -> dict:
    lead_days = int(args.get("lead_time_days", 7))
    plan = []
    for d in await _live("inventory"):
        stock, rp = int(d.get("stock") or 0), int(d.get("reorder_at") or 0)
        if rp <= 0 or stock > rp:
            continue
        daily_demand = max(rp / 14, 0.5)
        target = int(round(rp * 2 + daily_demand * lead_days))
        qty = max(target - stock, rp)
        plan.append({"id": d["id"], "sku": d.get("sku"), "name": d.get("name"), "stock": stock, "reorder_at": rp,
                     "suggested_qty": qty, "days_of_cover": round(stock / daily_demand, 1), "supplier": d.get("supplier"),
                     "est_cost": round(qty * float(d.get("unit_cost") or 0), 2), "urgency": "critical" if stock == 0 else "high" if stock < rp / 2 else "medium"})
    plan.sort(key=lambda p: p["days_of_cover"])
    return {"method": "reorder-point: target = 2*reorder_point + demand*lead_time", "lead_time_days": lead_days, "items": plan}


async def create_purchase_request(ctx: ToolContext, args: dict) -> dict:
    item = await db.inventory.find_one({"id": args["item_id"], "is_deleted": {"$ne": True}}, {"_id": 0})
    if not item:
        return {"error": "item not found"}
    qty = int(args["quantity"])
    cost = round(qty * float(item.get("unit_cost") or 0), 2)
    risk = "high" if cost >= 5000 else "medium" if cost >= 1000 else "low"
    return await _create_approval(ctx, f"Purchase {qty} × {item.get('sku')} ({item.get('name')})", args.get("reason", ""), risk,
                                  {"type": "purchase", "item_id": item["id"], "quantity": qty, "est_cost": cost, "supplier": item.get("supplier")})


# ---------------------------------------------------------------- Sales

STAGE_PROB = {"new": 0.1, "qualification": 0.2, "discovery": 0.3, "qualified": 0.35, "proposal": 0.5, "negotiation": 0.75, "won": 1.0, "lost": 0.0}


async def list_leads(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden"}
    q = {"stage": args["stage"]} if args.get("stage") else {}
    docs = await _live("leads", q)
    return {"count": len(docs), "leads": _slim(docs, ["id", "name", "company", "contact", "score", "stage", "value", "owner"])}


async def rank_leads(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden"}
    ranked = []
    for d in await _live("leads"):
        stage = str(d.get("stage") or "new").lower()
        if stage in {"won", "lost"}:
            continue
        p = 0.6 * STAGE_PROB.get(stage, 0.2) + 0.4 * (float(d.get("score") or 0) / 100)
        ranked.append({"id": d["id"], "name": d.get("name"), "company": d.get("company"), "stage": stage, "value": float(d.get("value") or 0),
                       "win_probability": round(p, 2), "expected_value": round(p * float(d.get("value") or 0), 2)})
    ranked.sort(key=lambda r: r["expected_value"], reverse=True)
    return {"method": "expected_value = (0.6*stage_prob + 0.4*score/100) * value", "leads": ranked[: int(args.get("limit", 10))]}


async def update_lead_stage(ctx: ToolContext, args: dict) -> dict:
    if not can_write(ctx.user):
        return {"error": "forbidden"}
    stage = args["stage"].lower()
    if stage not in STAGE_PROB:
        return {"error": f"stage must be one of {sorted(STAGE_PROB)}"}
    lead = await db.leads.find_one({"id": args["lead_id"], "is_deleted": {"$ne": True}}, {"_id": 0})
    if not lead:
        return {"error": "lead not found"}
    if stage == "won" and float(lead.get("value") or 0) >= 50000:
        return await _create_approval(ctx, f"Mark {lead.get('name')} as WON (${float(lead.get('value') or 0):,.0f})", args.get("reason", ""), "high",
                                      {"type": "lead_stage", "lead_id": lead["id"], "stage": stage})
    await db.leads.update_one({"id": lead["id"]}, {"$set": {"stage": stage, "updated_at": utcnow_iso(), "updated_by": ctx.user["email"]}})
    await audit(ctx.user["email"], "lead_stage", "sales", f"{lead.get('name')}: {lead.get('stage')} -> {stage}", agent=ctx.agent_key)
    return {"lead_id": lead["id"], "stage": stage}


# ---------------------------------------------------------------- Compliance

async def list_contracts(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden"}
    docs = await _live("contracts")
    for d in docs:
        d["expires"] = d.get("expires") or d.get("end")
        d["party"] = d.get("party") or d.get("counterparty")
    return {"count": len(docs), "contracts": _slim(docs, ["id", "title", "party", "expires", "risk", "status", "value", "attachments"])}


async def contract_expiry_report(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden"}
    horizon = int(args.get("days", 90))
    today = datetime.now(timezone.utc).date()
    out = []
    for d in await _live("contracts"):
        raw = d.get("expires") or d.get("end")
        try:
            exp = datetime.fromisoformat(str(raw)).date()
        except (TypeError, ValueError):
            continue
        delta = (exp - today).days
        if delta <= horizon:
            out.append({"id": d["id"], "title": d.get("title"), "party": d.get("party") or d.get("counterparty"), "expires": str(exp),
                        "days_left": delta, "risk": d.get("risk"), "state": "expired" if delta < 0 else "expiring"})
    out.sort(key=lambda x: x["days_left"])
    return {"horizon_days": horizon, "today": str(today), "contracts": out}


async def search_contract_text(ctx: ToolContext, args: dict) -> dict:
    if role_of(ctx.user) == "employee":
        return {"error": "forbidden"}
    entity = f"contract:{args['contract_id']}" if args.get("contract_id") else None
    hits = await search_chunks(args["query"], limit=int(args.get("limit", 4)), entity=entity)
    if not hits and entity is None:
        hits = await search_chunks(args["query"], limit=int(args.get("limit", 4)))
    return {"hits": hits, "note": "Quote these passages verbatim; if empty, no uploaded document covers this."}


async def flag_contract_risk(ctx: ToolContext, args: dict) -> dict:
    risk = args["risk"].lower()
    if risk not in {"low", "medium", "high"}:
        return {"error": "risk must be low|medium|high"}
    contract = await db.contracts.find_one({"id": args["contract_id"], "is_deleted": {"$ne": True}}, {"_id": 0})
    if not contract:
        return {"error": "contract not found"}
    if risk == "high" or not can_write(ctx.user):
        return await _create_approval(ctx, f"Set risk of '{contract.get('title')}' to {risk}", args["reason"], risk,
                                      {"type": "contract_risk", "contract_id": contract["id"], "risk": risk})
    await db.contracts.update_one({"id": contract["id"]}, {"$set": {"risk": risk, "risk_reason": args["reason"][:300], "updated_at": utcnow_iso()}})
    await audit(ctx.user["email"], "contract_risk", "compliance", f"{contract.get('title')} -> {risk}", agent=ctx.agent_key)
    return {"contract_id": contract["id"], "risk": risk}


# ---------------------------------------------------------------- Orchestrator

async def delegate_to_agent(ctx: ToolContext, args: dict) -> dict:
    if ctx.depth >= 1 or ctx.delegate is None:
        return {"error": "delegation depth exceeded"}
    target = args["agent_key"]
    if target not in {"hr", "finance", "inventory", "sales", "compliance"}:
        return {"error": "unknown agent"}
    result = await ctx.delegate(target, args["task"], ctx.user, ctx.conversation_id, ctx.depth + 1)
    return {"agent": target, "summary": result["text"][:2500], "tools_used": [t["name"] for t in result["tool_calls"]],
            "confidence": result.get("confidence"), "requires_human_review": result.get("escalate")}


# ---------------------------------------------------------------- Registry

def _tool(name: str, description: str, properties: dict, required: Optional[List[str]] = None) -> dict:
    return {"name": name, "description": description,
            "input_schema": {"type": "object", "properties": properties, "required": required or []}}


COMMON_TOOLS = [
    (_tool("get_company_snapshot", "High-level record counts across all modules.", {}), get_company_snapshot),
    (_tool("search_documents", "Full-text (BM25) search over uploaded documents (contracts, invoices, policies).",
           {"query": {"type": "string"}, "limit": {"type": "integer"}, "entity": {"type": "string", "description": "optional 'contract:<id>' or 'invoice:<id>' filter"}}, ["query"]), search_documents),
    (_tool("recall", "Retrieve durable facts this agent stored in earlier runs.", {"query": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]), recall),
    (_tool("remember", "Store a durable fact for future runs (decisions, thresholds, recurring issues).",
           {"fact": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "shared": {"type": "boolean", "description": "visible to all agents"}}, ["fact"]), remember),
    (_tool("create_approval", "Queue a proposed action for a human decision. Use for anything irreversible or high-impact.",
           {"title": {"type": "string"}, "summary": {"type": "string"}, "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "proposed_action": {"type": "object"}}, ["title", "summary"]), create_approval),
    (_tool("list_pending_approvals", "List approval requests still waiting for a human.", {}), list_pending_approvals),
    (_tool("report_outcome", "Call exactly once at the end with your structured verdict.",
           {"confidence": {"type": "integer", "minimum": 0, "maximum": 100}, "requires_human_review": {"type": "boolean"},
            "next_action": {"type": "string"}}, ["confidence", "requires_human_review", "next_action"]), None),
]

AGENT_TOOLS: Dict[str, List[tuple]] = {
    "hr": [
        (_tool("list_employees", "List employees, optionally filtered.", {"team": {"type": "string"}, "status": {"type": "string"}, "max_attendance": {"type": "integer"}}), list_employees),
        (_tool("list_leaves", "List leave requests.", {"status": {"type": "string", "enum": ["pending", "approved", "rejected"]}}), list_leaves),
        (_tool("decide_leave", "Approve or reject a routine leave request (manager/admin only).", {"leave_id": {"type": "string"}, "decision": {"type": "string", "enum": ["approved", "rejected"]}}, ["leave_id", "decision"]), decide_leave),
    ],
    "finance": [
        (_tool("list_invoices", "List invoices with optional status / vendor filter.", {"status": {"type": "string"}, "vendor": {"type": "string"}}), list_invoices),
        (_tool("run_anomaly_scan", "Run the Isolation-Forest + Benford + robust z-score anomaly model over all invoices.", {"limit": {"type": "integer"}}), run_anomaly_scan),
        (_tool("flag_invoice", "Mark an invoice as suspicious with a reason.", {"invoice_id": {"type": "string"}, "reason": {"type": "string"}, "severity": {"type": "string", "enum": ["low", "medium", "high"]}}, ["invoice_id", "reason"]), flag_invoice),
        (_tool("propose_payment", "Propose releasing payment for an invoice (always goes to human approval).", {"invoice_id": {"type": "string"}, "justification": {"type": "string"}}, ["invoice_id"]), propose_payment),
    ],
    "inventory": [
        (_tool("list_inventory", "List SKUs.", {"below_reorder_only": {"type": "boolean"}}), list_inventory),
        (_tool("compute_reorder_plan", "Deterministic reorder-point calculation for every SKU at/below threshold.", {"lead_time_days": {"type": "integer"}}), compute_reorder_plan),
        (_tool("create_purchase_request", "Raise a purchase request for approval.", {"item_id": {"type": "string"}, "quantity": {"type": "integer"}, "reason": {"type": "string"}}, ["item_id", "quantity"]), create_purchase_request),
    ],
    "sales": [
        (_tool("list_leads", "List pipeline leads.", {"stage": {"type": "string"}}), list_leads),
        (_tool("rank_leads", "Rank open leads by expected value.", {"limit": {"type": "integer"}}), rank_leads),
        (_tool("update_lead_stage", "Move a lead to a new stage (big wins go to approval).", {"lead_id": {"type": "string"}, "stage": {"type": "string"}, "reason": {"type": "string"}}, ["lead_id", "stage"]), update_lead_stage),
    ],
    "compliance": [
        (_tool("list_contracts", "List contracts with metadata.", {}), list_contracts),
        (_tool("contract_expiry_report", "Contracts expiring within N days.", {"days": {"type": "integer"}}), contract_expiry_report),
        (_tool("search_contract_text", "Retrieve clause text from uploaded contract documents.", {"query": {"type": "string"}, "contract_id": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]), search_contract_text),
        (_tool("flag_contract_risk", "Change a contract's risk rating (high risk goes to approval).", {"contract_id": {"type": "string"}, "risk": {"type": "string", "enum": ["low", "medium", "high"]}, "reason": {"type": "string"}}, ["contract_id", "risk", "reason"]), flag_contract_risk),
    ],
    "orchestrator": [
        (_tool("delegate_to_agent", "Hand a sub-task to a specialist agent and get its findings back.",
               {"agent_key": {"type": "string", "enum": ["hr", "finance", "inventory", "sales", "compliance"]}, "task": {"type": "string"}}, ["agent_key", "task"]), delegate_to_agent),
    ],
}


def tools_for(agent_key: str) -> List[dict]:
    return [schema for schema, _ in COMMON_TOOLS + AGENT_TOOLS.get(agent_key, [])]


def handler_for(agent_key: str, name: str) -> Optional[ToolFn]:
    for schema, fn in COMMON_TOOLS + AGENT_TOOLS.get(agent_key, []):
        if schema["name"] == name:
            return fn
    return None
