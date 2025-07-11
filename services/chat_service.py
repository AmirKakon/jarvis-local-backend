import openai
import os
from firebase_admin import firestore

openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo-1106")

# Firestore document for chat history
CHAT_HISTORY_DOC = "chat/history"

def get_chat_history():
    db = firestore.client()
    doc_ref = db.document(CHAT_HISTORY_DOC)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("messages", [])
    return []

def update_chat_history(history):
    db = firestore.client()
    doc_ref = db.document(CHAT_HISTORY_DOC)
    doc_ref.set({"messages": history})

def get_chat_response(chat_history):
    response = openai.chat.completions.create(
        model=openai_chat_model,
        messages=chat_history
    )
    return response.choices[0].message.content
