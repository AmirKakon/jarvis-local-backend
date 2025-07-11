import openai
import os
from firebase_admin import firestore

openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo-0125")
MAX_HISTORY_LENGTH = 30
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
        return doc.to_dict().get("messages", [])
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
    system_prompt = "You are Jarvis, a helpful and highly personalized AI assistant."
    if semantic_context:
        system_prompt += "\nRelevant info:\n" + "\n".join(f"- {c}" for c in semantic_context)
    messages = [{"role": "system", "content": system_prompt}]
    messages += chat_history[-MAX_HISTORY_LENGTH:]
    messages.append({"role": "user", "content": user_input})
    return messages

def get_chat_response(user_input):
    messages = build_messages(user_input)
    response = openai.chat.completions.create(
        model=openai_chat_model,
        messages=messages
    )
    return response.choices[0].message.content
