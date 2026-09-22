"""BM25 lexical retrieval over stored document chunks and agent memory (no external vector DB)."""
import re
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi

from core.db import db

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


def rank(query: str, docs: List[dict], text_key: str, limit: int) -> List[dict]:
    if not docs:
        return []
    corpus = [tokenize(d.get(text_key, "")) for d in docs]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order[:limit]:
        if scores[i] <= 0:
            continue
        out.append({**docs[i], "score": round(float(scores[i]), 3)})
    return out


async def search_chunks(query: str, limit: int = 5, entity: Optional[str] = None, file_id: Optional[str] = None) -> List[Dict]:
    q: Dict = {}
    if entity:
        q["entity"] = entity
    if file_id:
        q["file_id"] = file_id
    docs = await db.doc_chunks.find(q, {"_id": 0}).to_list(3000)
    hits = rank(query, docs, "text", limit)
    return [{"file_id": h["file_id"], "filename": h["filename"], "entity": h.get("entity"),
             "chunk": h["index"], "score": h["score"], "text": h["text"]} for h in hits]


async def search_memory(agent: str, query: str, limit: int = 5) -> List[Dict]:
    docs = await db.agent_memory.find({"agent": {"$in": [agent, "shared"]}}, {"_id": 0}).sort("created_at", -1).to_list(500)
    hits = rank(query, docs, "fact", limit)
    return [{"fact": h["fact"], "tags": h.get("tags", []), "agent": h["agent"], "created_at": h["created_at"], "score": h["score"]} for h in hits]
