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

# --- 4. Initialize OpenAI Model ---
openai_chat_model = "gpt-3.5-turbo-1106"  # or gpt-4o if you have access
openai_embedding_model = "text-embedding-3-small"

# --- 5. Initialize ChromaDB (Local Vector Database for RAG) ---
# Using PersistentClient so data is saved to disk
try:
    chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
    # Get or create a collection for personal notes/memory
    personal_memory_collection = chroma_client.get_or_create_collection(name="jarvis_personal_memory")
    print("ChromaDB initialized successfully.")
except Exception as e:
    print(f"Error initializing ChromaDB: {e}")
    exit(1)


# --- 6. Define Tools (Functions Gemini can call) ---
# These are the Python functions that execute real-world actions.
# We'll expose their definitions to Gemini via function calling.

def get_current_weather(location: str):
    """
    Gets the current weather for a specified location (city, district).
    Args:
        location (str): The city or district name for which to get the weather.
                        Example: "Pardes Hanna-Karkur"
    """
    print(f"DEBUG: Calling get_current_weather for {location}")
    # This is a placeholder. You'd integrate with a real weather API here.
    # For a production app, use an actual weather API (e.g., OpenWeatherMap, AccuWeather).
    # For now, let's return a fixed value for Pardes Hanna-Karkur, Haifa District, Israel.
    if "pardes hanna" in location.lower():
        return {
            "location": "Pardes Hanna-Karkur, Haifa District, Israel",
            "temperature_celsius": 28,
            "condition": "Partly Cloudy",
            "humidity": 70,
            "wind_speed_kph": 15
        }
    else:
        return {"error": "Weather data not available for this location via this tool."}

def control_home_assistant_device(entity_id: str, service: str, domain: str, data: dict = None):
    """
    Controls a Home Assistant device by calling a service.
    Args:
        entity_id (str): The Home Assistant entity ID (e.g., "light.living_room_lamp").
        service (str): The service to call (e.g., "turn_on", "turn_off", "toggle").
        domain (str): The domain of the service (e.g., "light", "switch", "fan").
        data (dict, optional): Additional service data (e.g., {"brightness": 100}). Defaults to None.
    """
    print(f"DEBUG: Calling Home Assistant service: {domain}.{service} for {entity_id} with data {data}")
    headers = {
        "Authorization": f"Bearer {HA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{HA_URL}/api/services/{domain}/{service}"
    payload = {"entity_id": entity_id}
    if data:
        payload.update(data)

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        return {"status": "success", "response": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error controlling HA device: {e}")
        return {"status": "error", "message": str(e), "details": response.text if response else "No response"}

def add_personal_note(note_content: str):
    print(f"DEBUG: Adding personal note: '{note_content}' to ChromaDB")
    try:
        # Generate embedding for the note using OpenAI
        embedding_response = openai.embeddings.create(
            input=note_content,
            model=openai_embedding_model
        )
        embedding = embedding_response.data[0].embedding
        note_id = f"note_{len(personal_memory_collection.get()['ids'])}_{os.urandom(4).hex()}"
        personal_memory_collection.add(
            documents=[note_content],
            embeddings=[embedding],
            metadatas=[{"source": "user_input", "timestamp": firestore.SERVER_TIMESTAMP}],
            ids=[note_id]
        )
        return {"status": "success", "message": "Note added to personal memory."}
    except Exception as e:
        print(f"Error adding personal note: {e}")
        return {"status": "error", "message": str(e)}

# --- Function Calling Tool Definitions for OpenAI ---
jarvis_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Gets the current weather for a specified location (city, district).",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city or district name for which to get the weather. Example: 'Pardes Hanna-Karkur'"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_home_assistant_device",
            "description": "Controls a Home Assistant device by calling a service (e.g., turn on/off light, set thermostat).",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The Home Assistant entity ID (e.g., 'light.living_room_lamp', 'switch.bedroom_fan')."
                    },
                    "service": {
                        "type": "string",
                        "description": "The service to call (e.g., 'turn_on', 'turn_off', 'toggle', 'set_temperature')."
                    },
                    "domain": {
                        "type": "string",
                        "description": "The domain of the service (e.g., 'light', 'switch', 'fan', 'climate')."
                    },
                    "data": {
                        "type": "object",
                        "description": "Additional service data as a dictionary (e.g., {'brightness_pct': 50} for light.turn_on)."
                    }
                },
                "required": ["entity_id", "service", "domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_personal_note",
            "description": "Adds a new personal note or fact to Jarvis's memory for future retrieval. Use this to store information the user wants Jarvis to remember.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_content": {
                        "type": "string",
                        "description": "The full content of the personal note to be stored."
                    }
                },
                "required": ["note_content"]
            }
        }
    }
]

# Map tool names to their Python functions
available_tools = {
    "get_current_weather": get_current_weather,
    "control_home_assistant_device": control_home_assistant_device,
    "add_personal_note": add_personal_note
}

# --- 7. Flask API Endpoints ---

@app.route('/')
def home():
    return "Jarvis Local Backend is running!"

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    global chat_history
    if 'chat_history' not in globals():
        chat_history = []
    try:
        # --- RAG: Retrieve relevant personal memory ---
        retrieved_context = ""
        try:
            query_embedding_response = openai.embeddings.create(
                input=user_input,
                model=openai_embedding_model
            )
            query_embedding = query_embedding_response.data[0].embedding
            results = personal_memory_collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                include=['documents']
            )
            if results and results['documents'] and results['documents'][0]:
                retrieved_context = "\n".join(results['documents'][0])
                print(f"DEBUG: Retrieved context from personal memory:\n{retrieved_context}")
        except Exception as e:
            print(f"WARNING: Error during ChromaDB RAG: {e}. Proceeding without additional context.")
            retrieved_context = ""
        system_prompt = (
            "You are Jarvis, a helpful and highly personalized AI assistant. "
            "You are running on the user's local computer, giving you capabilities "
            "to interact with their local environment and smart home. "
            "Always be concise and helpful. Refer to the user directly when appropriate. "
            "If you need more information to perform a task, ask clarifying questions. "
            f"Current Date and Time: {str(firestore.SERVER_TIMESTAMP)} (approx) "
            "Current Location: Pardes Hanna-Karkur, Haifa District, Israel."
            "You can use tools to get real-time information or perform actions."
        )
        if retrieved_context:
            system_prompt += f"\n\n--- Personal Context (from user's memory) ---\n{retrieved_context}\n---------------------------------------------"
        if not chat_history or chat_history[0].get("role") != "user":
            chat_history.insert(0, {"role": "user", "content": system_prompt + "\nUser's initial query starts below."})
        chat_history.append({"role": "user", "content": user_input})
        # OpenAI function calling
        response = openai.chat.completions.create(
            model=openai_chat_model,
            messages=chat_history,
            tools=jarvis_tools,
            tool_choice="auto"
        )
        full_response_text = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": full_response_text})
        return jsonify({"response": full_response_text})
    except Exception as e:
        print(f"An error occurred: {e}")
        chat_history.append({"role": "assistant", "content": f"I'm sorry, but I encountered an error: {e}"})
        return jsonify({"error": str(e)}), 500

# --- Firestore Endpoints (Example for syncing preferences) ---

@app.route('/api/preferences/<user_id>', methods=['GET'])
def get_preferences(user_id):
    try:
        doc_ref = db.collection('users').document(user_id).collection('preferences').document('general')
        doc = doc_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict())
        else:
            return jsonify({}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/preferences/<user_id>', methods=['POST'])
def update_preferences(user_id):
    preferences_data = request.json
    try:
        doc_ref = db.collection('users').document(user_id).collection('preferences').document('general')
        doc_ref.set(preferences_data, merge=True)
        return jsonify({"status": "success", "message": "Preferences updated."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Entry Point ---
if __name__ == '__main__':
    # When running locally, ensure the Flask app is accessible from your frontend.
    # Use host='0.0.0.0' to make it accessible from other devices on your local network.
    # IMPORTANT: Do NOT use debug=True in a production environment.
    app.run(debug=True, host='0.0.0.0', port=5000)