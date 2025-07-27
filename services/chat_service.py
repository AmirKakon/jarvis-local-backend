import os
from firebase_admin import firestore
from config.prompts import system_prompt
from mcp.gemini_chat_service import get_chat_response
from services.memory_service import search_memories, auto_add_memory_from_chat

MAX_HISTORY_LENGTH = os.getenv("MAX_CHAT_HISTORY_LENGTH", 8)
CHAT_HISTORY_DOC = "chat/history"

TOKEN_BUDGET = os.getenv("TOKEN_BUDGET", 500)
TOP_K_MEMORIES = os.getenv("TOP_K_MEMORIES", 3)

def get_semantic_context(user_input):
    relevant_memories = search_memories(user_input, top_k=TOP_K_MEMORIES)
    context_snippets = []
    token_budget = TOKEN_BUDGET
    used_tokens = 0
    for mem in relevant_memories:
        snippet = f"[{mem.type}] {mem.content}"
        snippet_tokens = len(snippet.split())
        if used_tokens + snippet_tokens > token_budget:
            break
        context_snippets.append(snippet)
        used_tokens += snippet_tokens
    return context_snippets

def get_chat_history():
    db = firestore.client()
    doc_ref = db.document(CHAT_HISTORY_DOC)
    doc = doc_ref.get()
    if doc.exists:
        messages = doc.to_dict().get("messages", [])
        valid_messages = []
        for m in messages:
            if isinstance(m, dict) and "role" in m and "content" in m:
                valid_messages.append(m)
            elif isinstance(m, str):
                valid_messages.append({"role": "user", "content": m})
        return valid_messages
    return []

def update_chat_history(history):
    trimmed_history = history[-MAX_HISTORY_LENGTH:]
    db = firestore.client()
    doc_ref = db.document(CHAT_HISTORY_DOC)
    doc_ref.set({"messages": trimmed_history})

# Build context for the model
# Combines system prompt, semantic context, and recent chat history

def build_messages(user_input):
    chat_history = get_chat_history()
    semantic_context = get_semantic_context(user_input)
    prompt = system_prompt
    if semantic_context:
        prompt += "\nRelevant info:\n" + "\n".join(f"- {c}" for c in semantic_context)
    messages = [{"role": "system", "content": prompt}]
    messages += chat_history[-MAX_HISTORY_LENGTH:]
    messages.append({"role": "user", "content": user_input})
    return messages

def chat_response(user_input):
    messages = build_messages(user_input)
    response = get_chat_response(messages)
    # Pass semantic context to auto_add_memory_from_chat to avoid adding memories already present
    semantic_context = get_semantic_context(user_input)
    current_chat = "{user_input}\n{response}"
    auto_add_memory_from_chat(current_chat, semantic_context=semantic_context)
    return response
