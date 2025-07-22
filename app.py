# app.py

import os
import json
from dotenv import load_dotenv
from flask import Flask
import openai
import firebase_admin
from firebase_admin import credentials
from routes.chat import chat_bp
from routes.memory import memory_bp
from services.memory_service import sync_chromadb_with_firestore_on_startup

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
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    exit(1)


# --- 3. Initialize Flask App ---
app = Flask(__name__)
app.register_blueprint(chat_bp)
app.register_blueprint(memory_bp)

# --- 4. Sync ChromaDB with Firestore on Startup ---
try:
    sync_chromadb_with_firestore_on_startup()
    print("ChromaDB synced with Firestore memories.")
except Exception as e:
    print(f"Error syncing ChromaDB with Firestore: {e}")

# --- 5. Utility Endpoints ---
@app.route('/')
def home():
    return "Jarvis Local Backend is running!"

# --- Entry Point ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)