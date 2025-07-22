from firebase_admin import firestore
from config.prompts import system_prompt
from mcp.gemini_chat_service import get_chat_response

MAX_HISTORY_LENGTH = 8
CHAT_HISTORY_DOC = "chat/history"

# Placeholder for semantic search (to be implemented later)
def get_semantic_context(user_input):
    # TODO: Implement semantic search over features and memory
    # Return a list of relevant context strings
    return []

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
