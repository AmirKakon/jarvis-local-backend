# app.py

import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
import chromadb
import requests # For Home Assistant API
import asyncio # For async operations if using FastAPI/async calls

# --- 1. Load Environment Variables ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HA_URL = os.getenv("HA_URL")
HA_ACCESS_TOKEN = os.getenv("HA_ACCESS_TOKEN")
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

if not all([GEMINI_API_KEY, HA_URL, HA_ACCESS_TOKEN, FIREBASE_SERVICE_ACCOUNT_PATH]):
    print("Error: Missing one or more environment variables. Check your .env file.")
    exit(1)

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

# --- 4. Initialize Gemini Model ---
genai.configure(api_key=GEMINI_API_KEY)
# We'll use gemini-pro for general chat and function calling
# For native audio TTS, you'd call a separate model like 'gemini-2.5-flash-preview-native-audio-dialog'
# directly via the API, which we'll abstract in a function.
gemini_chat_model = genai.GenerativeModel('gemini-pro')
gemini_embedding_model = genai.GenerativeModel('text-embedding-004') # For RAG embeddings

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
    """
    Adds a new personal note or fact to Jarvis's memory.
    This note will be embedded and stored in the local vector database (ChromaDB) for RAG.
    Args:
        note_content (str): The content of the personal note to be stored.
    """
    print(f"DEBUG: Adding personal note: '{note_content}' to ChromaDB")
    try:
        # Generate embedding for the note
        embedding_response = gemini_embedding_model.embed_content(model="text-embedding-004", content=note_content)
        embedding = embedding_response['embedding']

        # Add to ChromaDB
        # Using a simple UUID for ID in a real app, but for demo, a timestamp or hash is fine.
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

# --- Function Calling Tool Definitions for Gemini ---
# These describe the functions to Gemini so it knows when and how to call them.
# NOTE: google.generativeai does not have FunctionDeclaration or Schema classes. You must define your tools differently or use OpenAI-compatible schemas if supported.
# For now, we'll define the tools as dictionaries (OpenAI style), which is compatible with many LLM APIs.
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
async def chat_endpoint():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    # For simplicity, we'll maintain a simple chat history in memory for this session.
    # In a real app, you'd use a more robust session management.
    # We'll use a global variable here, but for production, consider session storage or a DB.
    global chat_history
    if 'chat_history' not in globals():
        chat_history = []

    try:
        # --- RAG: Retrieve relevant personal memory ---
        retrieved_context = ""
        try:
            query_embedding_response = gemini_embedding_model.embed_content(model="text-embedding-004", content=user_input)
            query_embedding = query_embedding_response['embedding']
            
            # Query ChromaDB for top 2 most relevant notes
            results = personal_memory_collection.query(
                query_embeddings=[query_embedding],
                n_results=2, # Adjust as needed
                include=['documents']
            )
            if results and results['documents'] and results['documents'][0]:
                retrieved_context = "\n".join(results['documents'][0])
                print(f"DEBUG: Retrieved context from personal memory:\n{retrieved_context}")
        except Exception as e:
            print(f"WARNING: Error during ChromaDB RAG: {e}. Proceeding without additional context.")
            retrieved_context = ""


        # Construct the prompt with retrieved context
        system_prompt = (
            "You are Jarvis, a helpful and highly personalized AI assistant. "
            "You are running on the user's local computer, giving you capabilities "
            "to interact with their local environment and smart home. "
            "Always be concise and helpful. Refer to the user directly when appropriate. "
            "If you need more information to perform a task, ask clarifying questions. "
            "Current Date and Time: " + firestore.SERVER_TIMESTAMP.isoformat() + " (approx) "
            "Current Location: Pardes Hanna-Karkur, Haifa District, Israel."
            "You can use tools to get real-time information or perform actions."
        )
        if retrieved_context:
            system_prompt += f"\n\n--- Personal Context (from user's memory) ---\n{retrieved_context}\n---------------------------------------------"

        # Add system prompt as a first message for context
        if not chat_history or chat_history[0].role != "user":
            chat_history.insert(0, {"role": "user", "parts": [{"text": system_prompt + "\nUser's initial query starts below."}]})

        # Append current user message to history
        chat_history.append({"role": "user", "parts": [{"text": user_input}]})

        # Send to Gemini with function calling
        response_stream = gemini_chat_model.generate_content(
            chat_history,
            tools=jarvis_tools,
            stream=True
        )

        full_response_text = ""
        tool_calls = []

        for chunk in response_stream:
            # Check for text response
            if chunk.candidates and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if part.text:
                        full_response_text += part.text
                    # Check for tool calls
                    if part.function_call:
                        tool_calls.append(part.function_call)

        print(f"DEBUG: Gemini Text Response: {full_response_text}")
        print(f"DEBUG: Gemini Tool Calls: {tool_calls}")

        # --- Handle Tool Calls ---
        if tool_calls:
            tool_outputs = []
            for tool_call in tool_calls:
                function_name = tool_call.name
                function_args = {k: v for k, v in tool_call.args.items()} # Ensure args are dict
                print(f"DEBUG: Executing tool: {function_name} with args: {function_args}")

                if function_name in available_tools:
                    # Execute the local Python function
                    result = available_tools[function_name](**function_args)
                    tool_outputs.append({
                        "functionResponse": {
                            "name": function_name,
                            "response": result
                        }
                    })
                    print(f"DEBUG: Tool '{function_name}' returned: {result}")
                else:
                    tool_outputs.append({
                        "functionResponse": {
                            "name": function_name,
                            "response": {"error": f"Tool '{function_name}' not found."}
                        }
                    })

            # Send tool outputs back to Gemini for final response generation
            # Add Gemini's tool call response to history first
            chat_history.append({"role": "model", "parts": [part for tc in tool_calls for part in [genai.types.Part.from_function_call(tc)] ]})
            chat_history.append({"role": "tool", "parts": [part for to in tool_outputs for part in [genai.types.Part.from_function_response(**to['functionResponse'])] ]})


            final_response_stream = gemini_chat_model.generate_content(
                chat_history,
                stream=True
            )
            full_response_text = ""
            for chunk in final_response_stream:
                if chunk.text:
                    full_response_text += chunk.text
            print(f"DEBUG: Gemini Final Response after tool execution: {full_response_text}")

        # Append Jarvis's final text response to history
        chat_history.append({"role": "model", "parts": [{"text": full_response_text}]})

        # --- Generate TTS Audio (Optional - can be done on frontend too) ---
        # For high-quality, consider calling Gemini's native audio model here.
        # This is a more complex step involving streaming audio bytes,
        # so for initial setup, we'll just send text.
        # If you wanted to do this, you'd add:
        # audio_response = gemini_chat_model.generate_content(
        #    "tts for: " + full_response_text,
        #    model='gemini-2.5-flash-preview-native-audio-dialog',
        #    stream=False # Or true if you handle streaming audio
        # )
        # then return audio_response.audio or a base64 encoded string.

        return jsonify({"response": full_response_text})

    except Exception as e:
        print(f"An error occurred: {e}")
        # Append error message to history to prevent breaking context on future turns
        chat_history.append({"role": "model", "parts": [{"text": f"I'm sorry, but I encountered an error: {e}"}]})
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