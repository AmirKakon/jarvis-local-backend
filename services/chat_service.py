from firebase_admin import firestore
from config.prompts import system_prompt
from mcp.gemini_chat_service import get_chat_response
from services.memory_service import search_memories

MAX_HISTORY_LENGTH = 8
CHAT_HISTORY_DOC = "chat/history"

# Placeholder for semantic search (to be implemented later)
def get_semantic_context(user_input):
    # Use ChromaDB semantic search to find relevant memory
    # Limit to top 3 results, and total token count ~500 (approx 3-5 short facts/notes)
    relevant_memories = search_memories(user_input, top_k=3)
    context_snippets = []
    token_budget = 500  # rough token budget for memory context
    used_tokens = 0
    for mem in relevant_memories:
        snippet = f"[{mem.type}] {mem.content}"
        snippet_tokens = len(snippet.split())  # crude token estimate
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
        # Ensure all messages are dicts with 'role' and 'content'
        valid_messages = []
        for m in messages:
            if isinstance(m, dict) and "role" in m and "content" in m:
                valid_messages.append(m)
            elif isinstance(m, str):
                # If message is a string, treat as user message
                valid_messages.append({"role": "user", "content": m})
            # Add more conversion logic if needed
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
    return response
