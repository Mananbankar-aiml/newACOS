import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, EmailStr

from core.audit import audit
from core.db import db, new_id, utcnow_iso
from core.security import current_user, filter_by_role, require_roles, require_writer, role_of

router = APIRouter(tags=["records"])

COLLECTIONS = {"employees", "leaves", "invoices", "inventory", "leads", "contracts"}
PROTECTED_KEYS = {"id", "_id", "history", "is_deleted", "deleted_at", "deleted_by", "created_at", "created_by"}
EXPORT_COLUMNS = {
    "employees": ["id", "name", "email", "department", "team", "role", "manager", "salary", "status", "attendance", "created_at"],
    "leaves": ["id", "employee", "employee_email", "type", "start", "end", "days", "status", "created_at"],
    "invoices": ["id", "number", "vendor", "amount", "due", "due_date", "status", "category", "flagged", "flag_reason", "created_at"],
    "inventory": ["id", "sku", "name", "category", "stock", "reorder_at", "unit_cost", "supplier", "created_at"],
    "leads": ["id", "name", "company", "contact", "email", "phone", "source", "stage", "value", "owner", "score", "created_at"],
    "contracts": ["id", "title", "party", "counterparty", "expires", "start", "end", "value", "status", "risk", "created_at"],
}


class EmployeeIn(BaseModel):
    name: str
    role: str = "Employee"
    team: str = "General"
    email: EmailStr
    status: str = "present"
    attendance: int = 100


class LeaveIn(BaseModel):
    employee: str
    employee_email: Optional[str] = None
    type: str = "Vacation"
    days: int = 1
    start: str
    status: str = "pending"


class InvoiceIn(BaseModel):
    number: str
    vendor: str
    amount: float
    status: str = "unpaid"
    due: str


class InventoryIn(BaseModel):
    sku: str
    name: str
    stock: int
    reorder_at: int
    supplier: str


class LeadIn(BaseModel):
    name: str
    contact: str
    score: int = 50
    stage: str = "qualification"
    value: float = 0


class ContractIn(BaseModel):
    title: str
    party: str
    expires: str
    risk: str = "low"


async def _list(collection: str) -> List[dict]:
    return await db[collection].find({"is_deleted": {"$ne": True}}, {"_id": 0, "history": 0}).to_list(500)


async def _create(collection: str, doc: dict, user: dict, label: str) -> dict:
    require_writer(user)
    doc = {**doc, "id": new_id(), "created_at": utcnow_iso(), "created_by": user["email"], "is_deleted": False}
    await db[collection].insert_one(doc)
    doc.pop("_id", None)
    await audit(user["email"], "create", collection, f"Created {label}: {doc.get('name') or doc.get('number') or doc.get('sku') or doc.get('title') or doc['id']}")
    return doc


async def _update(collection: str, id_: str, patch: dict, user: dict, label: str) -> dict:
    require_writer(user)
    prev = await db[collection].find_one({"id": id_, "is_deleted": {"$ne": True}})
    if not prev:
        raise HTTPException(404, "Not found")
    clean = {k: v for k, v in patch.items() if k not in PROTECTED_KEYS}
    if not clean:
        raise HTTPException(400, "No editable fields provided")
    snapshot = {k: v for k, v in prev.items() if k not in PROTECTED_KEYS | {"updated_at", "updated_by"}}
    snapshot.update({"_version_at": utcnow_iso(), "_version_by": user["email"]})
    clean.update({"updated_at": utcnow_iso(), "updated_by": user["email"]})
    await db[collection].update_one({"id": id_}, {"$set": clean, "$push": {"history": {"$each": [snapshot], "$slice": -10}}})
    await audit(user["email"], "update", collection, f"Updated {label}/{id_} · fields: {', '.join(clean.keys())}")
    return await db[collection].find_one({"id": id_}, {"_id": 0, "history": 0})


async def _delete(collection: str, id_: str, user: dict) -> dict:
    require_writer(user)
    res = await db[collection].update_one({"id": id_, "is_deleted": {"$ne": True}},
                                          {"$set": {"is_deleted": True, "deleted_at": utcnow_iso(), "deleted_by": user["email"]}})
    if not res.matched_count:
        raise HTTPException(404, "Not found")
    await audit(user["email"], "delete", collection, f"Soft-deleted {collection}/{id_}")
    return {"ok": True, "soft_deleted": True}


def _no_employee(user: dict, what: str) -> None:
    if role_of(user) == "employee":
        raise HTTPException(403, f"Employees cannot view {what}")


# ---- HR
@router.get("/hr/employees")
async def list_employees(user: dict = Depends(current_user)):
    return filter_by_role(await _list("employees"), user, self_field="email")


@router.get("/hr/leaves")
async def list_leaves(user: dict = Depends(current_user)):
    items = await _list("leaves")
    if role_of(user) != "employee":
        return items
    email, name = user.get("email", ""), user.get("name", "")
    return [x for x in items if (email and x.get("employee_email") == email) or (not x.get("employee_email") and name and x.get("employee") == name)]


@router.post("/hr/employees")
async def create_employee(inp: EmployeeIn, user: dict = Depends(current_user)):
    return await _create("employees", inp.model_dump(), user, "employee")


@router.put("/hr/employees/{id}")
async def update_employee(id: str, patch: Dict[str, Any], user: dict = Depends(current_user)):
    return await _update("employees", id, patch, user, "employee")


@router.delete("/hr/employees/{id}")
async def delete_employee(id: str, user: dict = Depends(current_user)):
    return await _delete("employees", id, user)


@router.post("/hr/leaves")
async def create_leave(inp: LeaveIn, user: dict = Depends(current_user)):
    return await _create("leaves", inp.model_dump(), user, "leave")


@router.put("/hr/leaves/{id}")
async def update_leave(id: str, patch: Dict[str, Any], user: dict = Depends(current_user)):
    return await _update("leaves", id, patch, user, "leave")


@router.delete("/hr/leaves/{id}")
async def delete_leave(id: str, user: dict = Depends(current_user)):
    return await _delete("leaves", id, user)


# ---- Finance
@router.get("/finance/invoices")
async def list_invoices(user: dict = Depends(current_user)):
    _no_employee(user, "invoices")
    return await _list("invoices")


@router.post("/finance/invoices")
async def create_invoice(inp: InvoiceIn, user: dict = Depends(current_user)):
    return await _create("invoices", inp.model_dump(), user, "invoice")


@router.put("/finance/invoices/{id}")
async def update_invoice(id: str, patch: Dict[str, Any], user: dict = Depends(current_user)):
    return await _update("invoices", id, patch, user, "invoice")


@router.delete("/finance/invoices/{id}")
async def delete_invoice(id: str, user: dict = Depends(current_user)):
    return await _delete("invoices", id, user)


# ---- Inventory
@router.get("/inventory")
async def list_inventory(user: dict = Depends(current_user)):
    return await _list("inventory")


@router.post("/inventory")
async def create_inventory(inp: InventoryIn, user: dict = Depends(current_user)):
    return await _create("inventory", inp.model_dump(), user, "SKU")


@router.put("/inventory/{id}")
async def update_inventory(id: str, patch: Dict[str, Any], user: dict = Depends(current_user)):
    return await _update("inventory", id, patch, user, "SKU")


@router.delete("/inventory/{id}")
async def delete_inventory(id: str, user: dict = Depends(current_user)):
    return await _delete("inventory", id, user)


# ---- Sales
@router.get("/sales/leads")
async def list_leads(user: dict = Depends(current_user)):
    _no_employee(user, "the sales pipeline")
    return await _list("leads")


@router.post("/sales/leads")
async def create_lead(inp: LeadIn, user: dict = Depends(current_user)):
    return await _create("leads", inp.model_dump(), user, "lead")


@router.put("/sales/leads/{id}")
async def update_lead(id: str, patch: Dict[str, Any], user: dict = Depends(current_user)):
    return await _update("leads", id, patch, user, "lead")


@router.delete("/sales/leads/{id}")
async def delete_lead(id: str, user: dict = Depends(current_user)):
    return await _delete("leads", id, user)


# ---- Compliance
@router.get("/compliance/contracts")
async def list_contracts(user: dict = Depends(current_user)):
    _no_employee(user, "contracts")
    return await _list("contracts")


@router.post("/compliance/contracts")
async def create_contract(inp: ContractIn, user: dict = Depends(current_user)):
    return await _create("contracts", inp.model_dump(), user, "contract")


@router.put("/compliance/contracts/{id}")
async def update_contract(id: str, patch: Dict[str, Any], user: dict = Depends(current_user)):
    return await _update("contracts", id, patch, user, "contract")


@router.delete("/compliance/contracts/{id}")
async def delete_contract(id: str, user: dict = Depends(current_user)):
    return await _delete("contracts", id, user)


# ---- Trash / history / import / export
def _check_collection(collection: str) -> None:
    if collection not in COLLECTIONS:
        raise HTTPException(404, "Unknown collection")


@router.get("/trash/{collection}")
async def list_trash(collection: str, user: dict = Depends(require_roles("admin", "manager", "auditor"))):
    _check_collection(collection)
    return await db[collection].find({"is_deleted": True}, {"_id": 0, "history": 0}).sort("deleted_at", -1).to_list(200)


@router.post("/trash/{collection}/{id}/restore")
async def restore_item(collection: str, id: str, user: dict = Depends(current_user)):
    _check_collection(collection)
    require_writer(user)
    res = await db[collection].update_one({"id": id, "is_deleted": True}, {"$set": {"is_deleted": False}, "$unset": {"deleted_at": "", "deleted_by": ""}})
    if not res.matched_count:
        raise HTTPException(404, "Not in trash")
    await audit(user["email"], "restore", collection, f"Restored {collection}/{id}")
    return {"ok": True}


@router.get("/history/{collection}/{id}")
async def get_history(collection: str, id: str, user: dict = Depends(current_user)):
    _check_collection(collection)
    doc = await db[collection].find_one({"id": id}, {"_id": 0, "history": 1})
    if not doc:
        raise HTTPException(404, "Not found")
    return {"history": doc.get("history", [])}


@router.post("/import/{collection}")
async def import_csv(collection: str, file: UploadFile = File(...), user: dict = Depends(current_user)):
    _check_collection(collection)
    require_writer(user)
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "CSV too large (max 2 MB)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    numeric = {"amount", "value", "stock", "reorder_at", "score", "attendance", "days"}
    rows, errors = [], []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        doc = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        for k in list(doc):
            if k in numeric and doc[k] not in (None, ""):
                try:
                    doc[k] = float(doc[k]) if k in {"amount", "value"} else int(float(doc[k]))
                except ValueError:
                    errors.append(f"Row {i}: '{k}' is not a number")
        doc.update({"id": new_id(), "created_at": utcnow_iso(), "created_by": user["email"], "is_deleted": False, "imported": True})
        rows.append(doc)
    if rows:
        await db[collection].insert_many(rows)
        await audit(user["email"], "import", collection, f"Imported {len(rows)} rows via CSV")
    return {"ok": True, "imported": len(rows), "errors": errors[:20]}


@router.get("/export/{collection}")
async def export_csv(collection: str, user: dict = Depends(require_roles("admin", "manager"))):
    _check_collection(collection)
    cols = EXPORT_COLUMNS[collection]
    rows = await db[collection].find({"is_deleted": {"$ne": True}}, {"_id": 0}).to_list(10000)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in cols})
    await audit(user["email"], "export", collection, f"Exported {len(rows)} rows as CSV")
    fname = f"{collection}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{fname}"'})
