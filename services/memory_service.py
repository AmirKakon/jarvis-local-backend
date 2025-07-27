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
        mem = get_memory(memory_id)
        if mem:
            update_in_chromadb(mem)
    return get_memory(memory_id)

def delete_memory(memory_id: str) -> bool:
    db = firestore.client()
    db.collection(MEMORY_COLLECTION).document(memory_id).delete()
    delete_from_chromadb(memory_id)
    return True

def search_memories(query: str, top_k: int = 5):
    found_ids = search_chromadb(query, top_k=top_k)
    return [get_memory(mem_id) for mem_id in found_ids if get_memory(mem_id)]

# Helper to check for duplicate memory (exact and semantic match)
def is_duplicate_memory(content: str, type_: str = "note", similarity_threshold: float = 0.9) -> bool:
    db = firestore.client()
    query = db.collection(MEMORY_COLLECTION).where("content", "==", content).where("type", "==", type_)
    docs = list(query.stream())
    if docs:
        return True
    found_ids = search_chromadb(content, top_k=1, return_scores=True) if 'return_scores' in search_chromadb.__code__.co_varnames else search_chromadb(content, top_k=1)
    if found_ids:
        # If return_scores is supported, found_ids is a list of (id, score)
        if isinstance(found_ids[0], (list, tuple)) and len(found_ids[0]) == 2:
            mem_id, score = found_ids[0]
            if score >= similarity_threshold:
                return True
        else:
            # If only ids are returned, optionally fetch and compare content (fallback)
            mem = get_memory(found_ids[0])
            if mem and mem.content.strip().lower() == content.strip().lower():
                return True
    return False

def sync_chromadb_with_firestore_on_startup():
    """Loads all memories from Firestore and syncs them to ChromaDB. Call this on app startup."""
    db = firestore.client()
    docs = db.collection(MEMORY_COLLECTION).stream()
    memories = [Memory.from_dict(doc.to_dict()) for doc in docs]
    sync_chromadb_with_firestore(memories)

# Automatic memory addition via LLM-based detection
def auto_add_memory_from_chat(response, semantic_context=None):
    """
    Uses the LLM extractor to extract new facts, notes, preferences, or events from the response, avoiding any already present in the semantic context. Returns a list of added Memory objects.
    """
    existing_info = "\n".join(f"- {item}" for item in semantic_context) if semantic_context else ""
    prompt = (
        "Below is a list of existing information. Do NOT extract or repeat any of it. "
        "Only extract new facts, notes, preferences, or events from the response.\n"
        "Existing Information (do not extract):\n"
        f"{existing_info}\n"
        "Response to extract from:\n"
        f"{response}"
    )
    memory_items = extract_memories_from_text(prompt)
    added_memories = []
    for item in memory_items:
        content = item.get("content")
        type_ = item.get("type", "note")
        tags = item.get("tags", [])
        if content:
            if is_duplicate_memory(content, type_):
                print(f"Duplicate or similar memory detected, skipping: {content}")
                continue
            mem = add_memory(content, type_, tags)
            added_memories.append(mem)
    if added_memories:
        print("Memories extracted from chat context.")
    return added_memories
