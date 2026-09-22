"""
Provider-agnostic tool-use agent loop with persistent conversation memory.

Talks to any OpenAI-compatible Chat Completions endpoint (Google Gemini, Anthropic, Groq, OpenAI,
local Ollama/vLLM …) — provider is selected purely through LLM_BASE_URL / LLM_API_KEY / LLM_MODEL.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openai import (APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, InternalServerError, RateLimitError)

from core.config import settings
from core.db import db, new_id, utcnow_iso
from agents.prompts import AGENTS, SYSTEM_TEMPLATE
from agents.tools import ToolContext, handler_for, tools_for

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6
HISTORY_TURNS = 16
_client: Optional[AsyncOpenAI] = None


def client() -> AsyncOpenAI:
    global _client
    if not settings.LLM_API_KEY:
        raise HTTPException(503, "LLM_API_KEY is not configured on the server")
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL or None,
                              default_headers=settings.LLM_EXTRA_HEADERS or None, max_retries=2, timeout=90)
    return _client


def system_prompt(agent_key: str, user: dict) -> str:
    a = AGENTS[agent_key]
    return SYSTEM_TEMPLATE.format(name=a["name"], specialty=a["specialty"], prompt=a["prompt"],
                                  now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                                  user_name=user.get("name", "unknown"), user_role=user.get("role", "employee"))


def to_openai_tools(schemas: List[dict]) -> List[dict]:
    out = []
    for s in schemas:
        fn = {"name": s["name"], "description": s["description"]}
        if s["input_schema"].get("properties"):
            fn["parameters"] = s["input_schema"]
        out.append({"type": "function", "function": fn})
    return out


async def history_for(conversation_id: Optional[str]) -> List[Dict[str, Any]]:
    if not conversation_id:
        return []
    docs = await db.chat_messages.find({"conversation_id": conversation_id}, {"_id": 0, "role": 1, "content": 1}) \
        .sort("created_at", -1).to_list(HISTORY_TURNS)
    turns = [{"role": d["role"], "content": d["content"] or "(no text)"} for d in reversed(docs) if d["role"] in {"user", "assistant"}]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return turns


def _assistant_turn(msg) -> dict:
    # Round-trip provider extras (e.g. Gemini thought signatures) but drop null/irrelevant fields.
    turn = msg.model_dump(exclude_none=True)
    for k in ("annotations", "refusal", "audio", "function_call", "reasoning"):
        turn.pop(k, None)
    turn.setdefault("content", "")
    return turn


async def _complete(messages: List[Dict[str, Any]], tools: List[dict]):
    """Call the primary model; on rate-limit / capacity errors back off, then fall back to LLM_FALLBACK_MODEL."""
    models = [settings.LLM_MODEL] + ([settings.LLM_FALLBACK_MODEL] if settings.LLM_FALLBACK_MODEL else [])
    kwargs = {"tools": tools, "tool_choice": "auto"} if tools else {}
    last_error: Optional[Exception] = None
    for attempt in range(3):
        for model in models:
            try:
                return await client().chat.completions.create(model=model, messages=messages, **kwargs), model
            except (RateLimitError, InternalServerError, APIConnectionError, APITimeoutError) as exc:
                logger.warning("LLM %s unavailable (%s) attempt %d", model, type(exc).__name__, attempt + 1)
                last_error = exc
            except APIStatusError as exc:
                raise HTTPException(502, f"LLM provider error ({exc.status_code}): {getattr(exc, 'message', str(exc))[:200]}")
        await asyncio.sleep(8 * (attempt + 1))
    raise HTTPException(503, f"LLM provider is temporarily unavailable (rate limit). Please retry in a minute. {str(last_error)[:160]}")


async def run_agent(agent_key: str, user_text: str, user: dict, conversation_id: Optional[str], depth: int = 0) -> Dict[str, Any]:
    if agent_key not in AGENTS:
        raise HTTPException(404, "Unknown agent")
    ctx = ToolContext(user, agent_key, conversation_id, depth)
    ctx.delegate = run_agent
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt(agent_key, user)}]
    messages += await history_for(conversation_id) if depth == 0 else []
    messages.append({"role": "user", "content": user_text})
    tools = to_openai_tools(tools_for(agent_key))
    trace: List[Dict[str, Any]] = []
    verdict: Dict[str, Any] = {}
    usage = {"input_tokens": 0, "output_tokens": 0}
    final_text = ""
    model_used = settings.LLM_MODEL

    for _ in range(MAX_TOOL_ROUNDS):
        resp, model_used = await _complete(messages, tools)
        if resp.usage:
            usage["input_tokens"] += resp.usage.prompt_tokens or 0
            usage["output_tokens"] += resp.usage.completion_tokens or 0
        msg = resp.choices[0].message
        if msg.content:
            final_text = msg.content.strip()
        if not msg.tool_calls:
            break
        messages.append(_assistant_turn(msg))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            name = tc.function.name
            if name == "report_outcome":
                verdict = args
                output: Any = {"recorded": True}
            else:
                handler = handler_for(agent_key, name)
                if handler is None:
                    output = {"error": f"unknown tool {name}"}
                else:
                    try:
                        output = await handler(ctx, args)
                    except Exception as exc:  # tool failure is fed back to the model, never crashes the run
                        logger.exception("tool %s failed", name)
                        output = {"error": str(exc)[:300]}
            trace.append({"name": name, "input": args, "output": output})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(output, default=str)[:12000]})

    if not final_text:
        # Some models end their turn on report_outcome without prose — ask for the write-up explicitly.
        messages.append({"role": "user", "content": "Now write the final answer for the user in concise Markdown, based only on the tool results above."})
        resp, model_used = await _complete(messages, [])
        final_text = (resp.choices[0].message.content or "").strip()
        if resp.usage:
            usage["input_tokens"] += resp.usage.prompt_tokens or 0
            usage["output_tokens"] += resp.usage.completion_tokens or 0

    approvals_created = [t for t in trace if isinstance(t["output"], dict) and t["output"].get("approval_id")]
    escalate = bool(verdict.get("requires_human_review", bool(approvals_created)))
    confidence = verdict.get("confidence")
    if confidence is None:
        confidence = 60 if approvals_created else 75
    return {
        "text": final_text or "(no response text)",
        "tool_calls": trace,
        "confidence": max(0, min(100, int(confidence))),
        "escalate": escalate,
        "next_action": verdict.get("next_action"),
        "approvals": [t["output"]["approval_id"] for t in approvals_created],
        "usage": usage,
        "model": model_used,
    }


async def record_task(agent_key: str, goal: str, result: Dict[str, Any], actor: str, conversation_id: Optional[str]) -> dict:
    doc = {
        "id": new_id(), "agent": agent_key, "goal": goal[:500], "reasoning": result["text"],
        "confidence": result["confidence"], "escalate": result["escalate"],
        "tool_calls": [t["name"] for t in result["tool_calls"]], "approvals": result["approvals"],
        "status": "pending_approval" if result["escalate"] else "completed",
        "actor": actor, "conversation_id": conversation_id, "created_at": utcnow_iso(),
    }
    await db.agent_tasks.insert_one(doc)
    await db.agents.update_one({"key": agent_key}, {"$set": {"last_run": utcnow_iso(), "last_confidence": result["confidence"]}})
    doc.pop("_id", None)
    return doc
