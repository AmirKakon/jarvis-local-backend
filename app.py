# app.py

import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import openai
import firebase_admin
from firebase_admin import credentials, firestore
import chromadb
import requests # For Home Assistant API
import asyncio # For async operations if using FastAPI/async calls
from routes.chat import chat_bp

# --- 1. Load Environment Variables ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HA_URL = os.getenv("HA_URL")
HA_ACCESS_TOKEN = os.getenv("HA_ACCESS_TOKEN")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

if not all([OPENAI_API_KEY, HA_URL, HA_ACCESS_TOKEN, FIREBASE_SERVICE_ACCOUNT_PATH]):
    print("Error: Missing one or more environment variables. Check your .env file.")
    exit(1)

openai.api_key = OPENAI_API_KEY

# --- 2. Initialize Firebase Admin SDK ---
try:
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    exit(1)

# --- 3. Initialize Flask App ---
app = Flask(__name__)
app.register_blueprint(chat_bp)

# --- 4. Initialize ChromaDB (Local Vector Database for RAG) ---
try:
    chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
    personal_memory_collection = chroma_client.get_or_create_collection(name="jarvis_personal_memory")
    print("ChromaDB initialized successfully.")
except Exception as e:
    print(f"Error initializing ChromaDB: {e}")
    exit(1)

# --- 5. Utility Endpoints ---
@app.route('/')
def home():
    return "Jarvis Local Backend is running!"

# --- Firestore Endpoints (Preferences) ---
@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    try:
        doc_ref = db.collection('preferences').document('general')
        doc = doc_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict())
        else:
            return jsonify({}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/preferences', methods=['POST'])
def update_preferences():
    preferences_data = request.json
    try:
        doc_ref = db.collection('preferences').document('general')
        doc_ref.set(preferences_data, merge=True)
        return jsonify({"status": "success", "message": "Preferences updated."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ChromaDB Memory Endpoint ---
@app.route('/api/memory', methods=['GET'])
def get_memory():
    try:
        memory = []
        results = personal_memory_collection.get()
        for doc, meta, doc_id in zip(results["documents"], results["metadatas"], results["ids"]):
            memory.append({
                "id": doc_id,
                "content": doc,
                "metadata": meta
            })
        return jsonify({"status": "success", "memory": memory})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Entry Point ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)