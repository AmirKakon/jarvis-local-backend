from services.chroma_service import add_to_chromadb, update_in_chromadb, delete_from_chromadb, search_chromadb, sync_chromadb_with_firestore
from firebase_admin import firestore
from models.memory import Memory
from typing import List, Optional
from datetime import datetime
import uuid

from mcp.gemini_llm_extractor import extract_memories_from_text

MEMORY_COLLECTION = "memory"


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
    # Add to ChromaDB for semantic search
    add_to_chromadb(memory)
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
        # Also update in ChromaDB
        mem = get_memory(memory_id)
        if mem:
            update_in_chromadb(mem)
    return get_memory(memory_id)

def delete_memory(memory_id: str) -> bool:
    db = firestore.client()
    db.collection(MEMORY_COLLECTION).document(memory_id).delete()
    # Also delete from ChromaDB
    delete_from_chromadb(memory_id)
    return True

def search_memories(query: str, top_k: int = 5):
    found_ids = search_chromadb(query, top_k=top_k)
    return [get_memory(mem_id) for mem_id in found_ids if get_memory(mem_id)]

def sync_chromadb_with_firestore_on_startup():
    """
    Loads all memories from Firestore and syncs them to ChromaDB. Call this on app startup.
    """
    db = firestore.client()
    docs = db.collection(MEMORY_COLLECTION).stream()
    memories = [Memory.from_dict(doc.to_dict()) for doc in docs]
    sync_chromadb_with_firestore(memories)

# Automatic memory addition via LLM-based detection
def auto_add_memory_from_chat(messages, response):
    """
    Uses MCP LLM extractor to extract important facts, notes, or events from the full chat context (messages + response) and adds them to memory.
    Returns a list of added Memory objects.
    """
    # Combine messages and response for context
    chat_context = "\n".join([
        f"{m['role']}: {m['content']}" for m in messages if isinstance(m, dict) and 'role' in m and 'content' in m
    ])
    chat_context += f"\nassistant: {response}"
    memory_items = extract_memories_from_text(chat_context)
    added_memories = []
    for item in memory_items:
        content = item.get("content")
        type_ = item.get("type", "note")
        tags = item.get("tags", [])
        if content:
            mem = add_memory(content, type_, tags)
            added_memories.append(mem)
    if len(added_memories) > 0:
        print("Memories extracted from chat context.")
    return added_memories
