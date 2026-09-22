from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.prompts import AGENTS
from agents.runner import record_task, run_agent
from agents.tools import tools_for
from core.audit import audit
from core.db import db, new_id, utcnow_iso
from core.guardrails import assess
from core.security import current_user, role_of

router = APIRouter(tags=["agents"])


class ConversationIn(BaseModel):
    agent_key: str = "orchestrator"
    title: Optional[str] = None


class ConversationPatch(BaseModel):
    title: Optional[str] = None
    agent_key: Optional[str] = None


class MessageIn(BaseModel):
    content: str
    agent_key: Optional[str] = None


class LegacyRunInput(BaseModel):
    goal: Optional[str] = None


def _check_agent(key: str) -> None:
    if key not in AGENTS:
        raise HTTPException(404, "Unknown agent")


@router.get("/agents")
async def list_agents(user: dict = Depends(current_user)):
    docs = await db.agents.find({}, {"_id": 0}).to_list(50)
    for d in docs:
        d["tools"] = [t["name"] for t in tools_for(d["key"])]
    return docs


@router.get("/agents/{agent_key}/tasks")
async def agent_tasks(agent_key: str, user: dict = Depends(current_user)):
    _check_agent(agent_key)
    return await db.agent_tasks.find({"agent": agent_key}, {"_id": 0}).sort("created_at", -1).to_list(50)


@router.post("/agents/{agent_key}/run")
async def legacy_run(agent_key: str, inp: LegacyRunInput, user: dict = Depends(current_user)):
    """One-shot run without a conversation (kept for the scheduler and API clients)."""
    _check_agent(agent_key)
    goal = assess(inp.goal or "Perform a routine check for anomalies and produce a short digest.")
    result = await run_agent(agent_key, goal.text, user, None)
    task = await record_task(agent_key, goal.text, result, user["email"], None)
    await audit(user["email"], "agent_run", "agents", f"Ran {agent_key} · conf {result['confidence']} · tools {len(result['tool_calls'])}", agent=agent_key)
    return {**task, "tool_calls": result["tool_calls"]}


# ---------------------------------------------------------------- Chat (ChatGPT-style conversations)

async def _own_conversation(conv_id: str, user: dict) -> dict:
    conv = await db.chat_conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversation not found")
    if conv["owner"] != user["id"] and role_of(user) != "admin":
        raise HTTPException(403, "Not your conversation")
    return conv


@router.get("/chat/conversations")
async def list_conversations(user: dict = Depends(current_user)):
    return await db.chat_conversations.find({"owner": user["id"]}, {"_id": 0}).sort("updated_at", -1).to_list(100)


@router.post("/chat/conversations")
async def create_conversation(inp: ConversationIn, user: dict = Depends(current_user)):
    _check_agent(inp.agent_key)
    doc = {"id": new_id(), "owner": user["id"], "agent_key": inp.agent_key, "title": inp.title or "New conversation",
           "message_count": 0, "created_at": utcnow_iso(), "updated_at": utcnow_iso()}
    await db.chat_conversations.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/chat/conversations/{conv_id}")
async def patch_conversation(conv_id: str, inp: ConversationPatch, user: dict = Depends(current_user)):
    await _own_conversation(conv_id, user)
    patch = {k: v for k, v in inp.model_dump(exclude_none=True).items()}
    if "agent_key" in patch:
        _check_agent(patch["agent_key"])
    if patch:
        await db.chat_conversations.update_one({"id": conv_id}, {"$set": {**patch, "updated_at": utcnow_iso()}})
    return await db.chat_conversations.find_one({"id": conv_id}, {"_id": 0})


@router.delete("/chat/conversations/{conv_id}")
async def delete_conversation(conv_id: str, user: dict = Depends(current_user)):
    await _own_conversation(conv_id, user)
    await db.chat_messages.delete_many({"conversation_id": conv_id})
    await db.chat_conversations.delete_one({"id": conv_id})
    return {"ok": True}


@router.get("/chat/conversations/{conv_id}/messages")
async def list_messages(conv_id: str, user: dict = Depends(current_user)):
    await _own_conversation(conv_id, user)
    return await db.chat_messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("created_at", 1).to_list(500)


@router.post("/chat/conversations/{conv_id}/messages")
async def send_message(conv_id: str, inp: MessageIn, user: dict = Depends(current_user)):
    conv = await _own_conversation(conv_id, user)
    agent_key = inp.agent_key or conv["agent_key"]
    _check_agent(agent_key)
    risk = assess(inp.content)
    if not risk.text:
        raise HTTPException(400, "Message is empty")
    user_msg = {"id": new_id(), "conversation_id": conv_id, "role": "user", "content": risk.text, "agent_key": agent_key,
                "author": user["email"], "guardrail": risk.as_dict(), "created_at": utcnow_iso()}
    await db.chat_messages.insert_one(user_msg)
    if risk.high_risk:
        await audit(user["email"], "injection_suspected", "agents", f"score={risk.score:.2f} signals={','.join(risk.signals)}", agent=agent_key)

    result = await run_agent(agent_key, risk.text, user, conv_id)
    task = await record_task(agent_key, risk.text, result, user["email"], conv_id)
    assistant_msg = {
        "id": new_id(), "conversation_id": conv_id, "role": "assistant", "agent_key": agent_key, "content": result["text"],
        "tool_calls": result["tool_calls"], "confidence": result["confidence"], "escalate": result["escalate"],
        "next_action": result["next_action"], "approvals": result["approvals"], "usage": result["usage"], "model": result["model"],
        "task_id": task["id"], "created_at": utcnow_iso(),
    }
    await db.chat_messages.insert_one(assistant_msg)
    title_patch = {"title": risk.text[:60]} if conv.get("message_count", 0) == 0 else {}
    await db.chat_conversations.update_one({"id": conv_id}, {"$set": {**title_patch, "agent_key": agent_key, "updated_at": utcnow_iso()}, "$inc": {"message_count": 2}})
    await audit(user["email"], "agent_chat", "agents", f"{agent_key} · conf {result['confidence']} · {len(result['tool_calls'])} tool calls", agent=agent_key)
    user_msg.pop("_id", None)
    assistant_msg.pop("_id", None)
    return {"user_message": user_msg, "assistant_message": assistant_msg}


@router.get("/agents/memory")
async def list_memory(user: dict = Depends(current_user)):
    return await db.agent_memory.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.delete("/agents/memory/{memory_id}")
async def delete_memory(memory_id: str, user: dict = Depends(current_user)):
    if role_of(user) not in {"admin", "manager"}:
        raise HTTPException(403, "Only admin/manager")
    res = await db.agent_memory.delete_one({"id": memory_id})
    if not res.deleted_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}
