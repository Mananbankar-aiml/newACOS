import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client():
    os.environ["DB_NAME"] = f"acos_test_{uuid.uuid4().hex[:8]}"
    from app import app
    from core.db import client as mongo, db
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        await mongo.drop_database(db.name)


async def _register(client: AsyncClient, email: str, role: str) -> dict:
    r = await client.post("/api/auth/register", json={"email": email, "name": "T", "password": "Str0ngPass!"})
    assert r.status_code == 200, r.text
    from core.db import db
    await db.users.update_one({"email": email}, {"$set": {"role": role}})
    r = await client.post("/api/auth/login", json={"email": email, "password": "Str0ngPass!"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_register_rejects_weak_password(client):
    r = await client.post("/api/auth/register", json={"email": "weak@t.io", "name": "W", "password": "short"})
    assert r.status_code == 400


async def test_forgot_password_never_leaks_token(client):
    await _register(client, "leak@t.io", "employee")
    r = await client.post("/api/auth/forgot", json={"email": "leak@t.io"})
    body = r.json()
    assert r.status_code == 200 and "token" not in str(body).lower().replace("instructions", "")


async def test_rbac_employee_cannot_read_invoices_or_write(client):
    emp = await _register(client, "emp@t.io", "employee")
    assert (await client.get("/api/finance/invoices", headers=emp)).status_code == 403
    r = await client.post("/api/finance/invoices", json={"number": "X", "vendor": "V", "amount": 1, "due": "2026-01-01"}, headers=emp)
    assert r.status_code == 403


async def test_manager_crud_soft_delete_and_restore(client):
    mgr = await _register(client, "mgr@t.io", "manager")
    r = await client.post("/api/finance/invoices", json={"number": "INV-T1", "vendor": "TestCo", "amount": 4990, "due": "2026-07-01"}, headers=mgr)
    assert r.status_code == 200
    inv_id = r.json()["id"]
    assert (await client.delete(f"/api/finance/invoices/{inv_id}", headers=mgr)).status_code == 200
    ids = [i["id"] for i in (await client.get("/api/finance/invoices", headers=mgr)).json()]
    assert inv_id not in ids
    assert (await client.post(f"/api/trash/invoices/{inv_id}/restore", headers=mgr)).status_code == 200


async def test_anomaly_endpoint_and_evaluation(client):
    mgr = await _register(client, "mgr2@t.io", "manager")
    r = await client.get("/api/finance/anomalies", headers=mgr)
    assert r.status_code == 200 and "benford" in r.json()
    r = await client.get("/api/ml/evaluate?n=120&seed=3", headers=mgr)
    assert r.status_code == 200 and 0 <= r.json()["f1"] <= 1


async def test_admin_step_up_required_for_approvals(client):
    adm = await _register(client, "adm@t.io", "admin")
    from core.db import db
    approval = {"id": "ap-test", "agent": "finance", "title": "t", "summary": "s", "status": "pending", "requested_by": "x", "created_at": "2026-01-01"}
    await db.approvals.insert_one(approval)
    r = await client.post("/api/approvals/ap-test/decide", json={"decision": "approve"}, headers=adm)
    assert r.status_code == 428
    otp = (await client.post("/api/auth/otp/request", json={"purpose": "approval"}, headers=adm)).json()["demo_hint"]
    step = (await client.post("/api/auth/otp/verify", json={"otp": otp, "purpose": "approval"}, headers=adm)).json()["step_up_token"]
    r = await client.post("/api/approvals/ap-test/decide", json={"decision": "approve"}, headers={**adm, "X-OTP-Token": step})
    assert r.status_code == 200 and r.json()["status"] == "approved"


async def test_chat_conversation_isolated_per_user(client):
    a = await _register(client, "a@t.io", "manager")
    b = await _register(client, "b@t.io", "manager")
    conv = (await client.post("/api/chat/conversations", json={"agent_key": "finance"}, headers=a)).json()
    assert (await client.get(f"/api/chat/conversations/{conv['id']}/messages", headers=b)).status_code == 403
    assert (await client.get(f"/api/chat/conversations/{conv['id']}/messages", headers=a)).status_code == 200


async def test_upload_indexes_text_for_retrieval(client):
    mgr = await _register(client, "up@t.io", "manager")
    text = b"Termination clause: either party may terminate with 60 days written notice. Payment terms are net 30."
    r = await client.post("/api/files/upload?attach_to=contract:c1", files={"file": ("msa.txt", text, "text/plain")}, headers=mgr)
    assert r.status_code == 200 and r.json()["indexed_chunks"] >= 1
    from rag.retrieve import search_chunks
    hits = await search_chunks("termination notice", entity="contract:c1")
    assert hits and "60 days" in hits[0]["text"]
    dl = await client.get(f"/api/files/{r.json()['id']}/download", headers=mgr)
    assert dl.status_code == 200 and dl.content == text


async def test_agent_run_without_llm_key_returns_503(client):
    mgr = await _register(client, "llm@t.io", "manager")
    from core.config import settings
    original = settings.LLM_API_KEY
    settings.LLM_API_KEY = ""
    try:
        r = await client.post("/api/agents/finance/run", json={"goal": "hi"}, headers=mgr)
        assert r.status_code == 503
    finally:
        settings.LLM_API_KEY = original
