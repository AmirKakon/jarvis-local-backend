from chromadb import Client as ChromaClient
from chromadb.config import Settings
from models.memory import Memory
from typing import List
from datetime import datetime

CHROMA_COLLECTION = "memory_semantic"
CHROMA_DB_PATH = "data/chroma_db"
chroma_client = ChromaClient(Settings(persist_directory=CHROMA_DB_PATH))

def add_to_chromadb(memory: Memory):
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    tags_str = ",".join(memory.tags) if isinstance(memory.tags, list) else str(memory.tags)
    collection.add(
        documents=[memory.content],
        ids=[memory.id],
        metadatas=[{"type": memory.type, "tags": tags_str, "created_at": memory.created_at.isoformat()}]
    )

def update_in_chromadb(memory: Memory):
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    tags_str = ",".join(memory.tags) if isinstance(memory.tags, list) else str(memory.tags)
    collection.delete(ids=[memory.id])
    collection.add(
        documents=[memory.content],
        ids=[memory.id],
        metadatas=[{"type": memory.type, "tags": tags_str, "created_at": memory.created_at.isoformat()}]
    )

def delete_from_chromadb(memory_id: str):
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    collection.delete(ids=[memory_id])

def search_chromadb(query: str, top_k: int = 5) -> List[str]:
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    results = collection.query(query_texts=[query], n_results=top_k)
    found_ids = results.get("ids", [[]])[0]
    return found_ids

def sync_chromadb_with_firestore(memories: List[Memory]):
    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    all_ids = collection.get()['ids']
    if all_ids:
        collection.delete(ids=all_ids)
    for mem in memories:
        add_to_chromadb(mem)
