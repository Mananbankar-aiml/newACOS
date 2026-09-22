"""Document ingestion: extract text from uploads, chunk it, persist chunks for retrieval."""
import io
import re
from typing import List, Optional

from pypdf import PdfReader

from core.db import db, new_id, utcnow_iso

CHUNK_CHARS = 900
OVERLAP = 150


def extract_text(data: bytes, ext: str) -> str:
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if ext in {"txt", "csv", "md"}:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1")
    return ""


def chunk_text(text: str) -> List[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + CHUNK_CHARS)
        cut = text.rfind(". ", start, end)
        if cut == -1 or cut < start + CHUNK_CHARS // 2:
            cut = end
        else:
            cut += 1
        chunks.append(text[start:cut].strip())
        start = max(cut - OVERLAP, start + 1)
    return [c for c in chunks if c]


async def ingest_file(file_id: str, filename: str, data: bytes, ext: str, entity: Optional[str]) -> int:
    chunks = chunk_text(extract_text(data, ext))
    if not chunks:
        return 0
    docs = [{
        "id": new_id(), "file_id": file_id, "filename": filename, "entity": entity,
        "index": i, "text": c, "created_at": utcnow_iso(),
    } for i, c in enumerate(chunks)]
    await db.doc_chunks.insert_many(docs)
    return len(docs)
