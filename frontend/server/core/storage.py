"""File storage on MongoDB GridFS via Motor (fully async, no third-party object store)."""
from bson import ObjectId
from core.db import fs


async def put_object(filename: str, data: bytes, content_type: str, metadata: dict) -> str:
    oid = await fs.upload_from_stream(filename, data, metadata={"content_type": content_type, **metadata})
    return str(oid)


async def get_object(storage_id: str) -> bytes:
    stream = await fs.open_download_stream(ObjectId(storage_id))
    return await stream.read()


async def delete_object(storage_id: str) -> None:
    await fs.delete(ObjectId(storage_id))
