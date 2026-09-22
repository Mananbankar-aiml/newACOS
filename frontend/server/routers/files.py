from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from core.audit import audit
from core.config import settings
from core.db import db, new_id, utcnow_iso
from core.security import can_write, current_user
from core.storage import get_object, put_object
from rag.ingest import ingest_file

router = APIRouter(prefix="/files", tags=["files"])
ALLOWED = {"pdf", "png", "jpg", "jpeg", "webp", "csv", "txt", "md"}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), attach_to: Optional[str] = Query(None), user: dict = Depends(current_user)):
    if not can_write(user):
        raise HTTPException(403, "Only admin/manager can upload files")
    ext = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin").lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "Unsupported file type")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (max {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    file_id = new_id()
    entity = attach_to if attach_to and ":" in attach_to else None
    storage_id = await put_object(file.filename or file_id, data, file.content_type or "application/octet-stream", {"file_id": file_id, "uploaded_by": user["email"]})
    chunks = await ingest_file(file_id, file.filename or file_id, data, ext, entity)
    doc = {"id": file_id, "storage_id": storage_id, "original_filename": file.filename, "content_type": file.content_type,
           "size": len(data), "indexed_chunks": chunks, "entity": entity, "uploaded_by": user["email"], "is_deleted": False, "created_at": utcnow_iso()}
    await db.files.insert_one(doc)
    if entity:
        kind, target_id = entity.split(":", 1)
        collection = {"invoice": "invoices", "contract": "contracts"}.get(kind)
        if collection:
            await db[collection].update_one({"id": target_id}, {"$push": {"attachments": file_id}})
    await audit(user["email"], "file_upload", "storage", f"Uploaded {file.filename} ({len(data)} bytes, {chunks} chunks indexed)")
    doc.pop("_id", None)
    return doc


@router.get("")
async def list_files(user: dict = Depends(current_user)):
    return await db.files.find({"is_deleted": False}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.get("/{file_id}/download")
async def download_file(file_id: str, user: dict = Depends(current_user)):
    rec = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "File not found")
    data = await get_object(rec["storage_id"])
    return Response(content=data, media_type=rec.get("content_type") or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{rec.get("original_filename", file_id)}"'})
