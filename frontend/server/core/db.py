import uuid
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from core.config import settings

_current_loop = None
_client_instance = None
_db_instance = None
_fs_instance = None

def _ensure_connected():
    global _current_loop, _client_instance, _db_instance, _fs_instance
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if _current_loop is not loop or _client_instance is None:
        if _client_instance is not None:
            try:
                _client_instance.close()
            except Exception:
                pass
        
        _current_loop = loop
        _client_instance = AsyncIOMotorClient(settings.MONGO_URL)
        _db_instance = _client_instance[settings.DB_NAME]
        _fs_instance = AsyncIOMotorGridFSBucket(_db_instance, bucket_name="uploads")

class ClientProxy:
    def __getattr__(self, name):
        _ensure_connected()
        return getattr(_client_instance, name)
    def __getitem__(self, key):
        _ensure_connected()
        return _client_instance[key]

class DBProxy:
    def __getattr__(self, name):
        _ensure_connected()
        return getattr(_db_instance, name)
    def __getitem__(self, key):
        _ensure_connected()
        return _db_instance[key]

class FSProxy:
    def __getattr__(self, name):
        _ensure_connected()
        return getattr(_fs_instance, name)

client = ClientProxy()
db = DBProxy()
fs = FSProxy()

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id() -> str:
    return str(uuid.uuid4())

async def ensure_indexes() -> None:
    _ensure_connected()
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
