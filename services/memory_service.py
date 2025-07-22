from firebase_admin import firestore
from models.memory import Memory
from typing import List, Optional
from datetime import datetime
import uuid
from chromadb import Client as ChromaClient
from mcp.openai_llm_extractor import extract_memories_from_text

MEMORY_COLLECTION = "memory"
CHROMA_COLLECTION = "memory_semantic"
CHROMA_DB_PATH = "data/chroma_db"
chroma_client = ChromaClient()

def memory_model_to_dict(memory: Memory) -> dict:
    return {
        "id": memory.id,
        "type": memory.type,
        "content": memory.content,
        "created_at": memory.created_at.isoformat(),
        "tags": memory.tags
    }

def add_memory(content: str, type_: str = "note", tags: Optional[List[str]] = None) -> Memory:
    db = firestore.client()
    memory_id = str(uuid.uuid4())
    memory = Memory(
        id=memory_id,
        type=type_,
        content=content,
        created_at=datetime.utcnow(),
        tags=tags or []
    )
    db.collection(MEMORY_COLLECTION).document(memory_id).set(memory.to_dict())
    return memory

def get_memory(memory_id: str) -> Optional[Memory]:
    db = firestore.client()
    doc = db.collection(MEMORY_COLLECTION).document(memory_id).get()
    if doc.exists:
        return Memory.from_dict(doc.to_dict())
    return None

def list_memories(type_: Optional[str] = None) -> List[Memory]:
    db = firestore.client()
    query = db.collection(MEMORY_COLLECTION)
    if type_:
        query = query.where("type", "==", type_)
    docs = query.stream()
    return [Memory.from_dict(doc.to_dict()) for doc in docs]

def update_memory(memory_id: str, content: Optional[str] = None, type_: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[Memory]:
    db = firestore.client()
    updates = {}
    if content is not None:
        updates["content"] = content
    if type_ is not None:
        updates["type"] = type_
    if tags is not None:
        updates["tags"] = tags
    if updates:
        db.collection(MEMORY_COLLECTION).document(memory_id).update(updates)
    return get_memory(memory_id)

def delete_memory(memory_id: str) -> bool:
    db = firestore.client()
    db.collection(MEMORY_COLLECTION).document(memory_id).delete()
    return True

# Semantic search over memory using ChromaDB
# Sync Firestore memory to ChromaDB before searching

def sync_memories_to_chromadb():
    db = firestore.client()
    docs = db.collection(MEMORY_COLLECTION).stream()
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    for doc in docs:
        mem = Memory.from_dict(doc.to_dict())
        # Convert tags list to comma-separated string for ChromaDB metadata
        tags_str = ",".join(mem.tags) if isinstance(mem.tags, list) else str(mem.tags)
        collection.add(
            documents=[mem.content],
            ids=[mem.id],
            metadatas=[{"type": mem.type, "tags": tags_str, "created_at": mem.created_at.isoformat()}]
        )


def search_memories(query: str, top_k: int = 5):
    sync_memories_to_chromadb()
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    results = collection.query(query_texts=[query], n_results=top_k)
    # Return Memory objects for found ids
    db = firestore.client()
    found_ids = results.get("ids", [[]])[0]
    return [get_memory(mem_id) for mem_id in found_ids if get_memory(mem_id)]

# Automatic memory addition via LLM-based detection
def auto_add_memory_from_chat(chat_text: str):
    """
    Uses MCP LLM extractor to extract important facts, notes, or events from chat text and adds them to memory.
    Returns a list of added Memory objects.
    """
    memory_items = extract_memories_from_text(chat_text)
    added_memories = []
    for item in memory_items:
        content = item.get("content")
        type_ = item.get("type", "note")
        tags = item.get("tags", [])
        if content:
            mem = add_memory(content, type_, tags)
            added_memories.append(mem)
    return added_memories
