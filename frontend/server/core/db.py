import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URL)
db = client[settings.DB_NAME]
fs = AsyncIOMotorGridFSBucket(db, bucket_name="uploads")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


async def ensure_indexes() -> None:
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.agents.create_index("key", unique=True)
    await db.agent_tasks.create_index([("agent", 1), ("created_at", -1)])
    await db.approvals.create_index([("status", 1), ("created_at", -1)])
    await db.otps.create_index([("email", 1), ("purpose", 1), ("used", 1)])
    await db.otps.create_index("created_at")
    await db.schedules.create_index("agent_key", unique=True)
    await db.audit_logs.create_index([("timestamp", -1)])
    await db.chat_conversations.create_index([("owner", 1), ("updated_at", -1)])
    await db.chat_messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await db.agent_memory.create_index([("agent", 1), ("created_at", -1)])
    await db.doc_chunks.create_index("file_id")
    for col in ["employees", "leaves", "invoices", "inventory", "leads", "contracts", "files"]:
        await db[col].create_index("id", unique=True)
        await db[col].create_index("is_deleted")
