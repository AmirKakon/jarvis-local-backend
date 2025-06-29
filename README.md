# Jarvis Local Backend

A modular, scalable backend for a personalized AI assistant, **Jarvis**.  
Designed for minimal local resource usage, leveraging cloud services (Firebase, OpenAI) wherever possible, while enabling local smart home control and automation.

---

## Features

- **Modular Flask API** for chat, smart home, and automation triggers.
- **Cloud-first:** Uses Firebase for authentication, user data, and learning log.
- **OpenAI API** for chat, function calling, and embeddings (easily swappable for other LLMs).
- **Smart Home Integration:** Local backend can trigger Home Assistant or other local automations.
- **MCP (Model Communication Protocol):** Standardizes communication between backend and AI models for easy model swapping.
- **Learning & Memory:** Stores user facts, preferences, and notes in Firestore.
- **Easily Extensible:** Add new modules (skills, triggers, actions) with minimal code changes.
- **Frontend-ready:** Designed for a React SPA frontend (see [Frontend Plan](#frontend-plan)).

---

## Architecture Overview
[React Frontend] <--Firebase Auth/Firestore--> [Firebase Cloud] |
| (chat/smart home API calls)
v
[Flask Backend] <----> [OpenAI API / MCP]
|
v
[Home Assistant API] (local network)

---

## Modular Structure

- **/api/chat**: Conversational endpoint (OpenAI/MCP).
- **/api/smarthome**: Proxy for Home Assistant or local automations.
- **/api/preferences**: User preferences (Firestore).
- **/api/notes**: Learning log/memory (Firestore).
- **/modules/**: Pluggable skills, triggers, and actions.
- **/mcp/**: Model Communication Protocol adapters for LLMs.

---

## Workload Breakdown

### 1. **Cloud Setup**
- [ ] Create Firebase project.
- [ ] Enable Google Auth.
- [ ] Set up Firestore collections:
    - `users/{userId}/preferences/general`
    - `users/{userId}/personal_notes`

### 2. **Backend (Flask)**
- [ ] Scaffold Flask app with modular blueprint structure.
- [ ] Implement `/api/chat` endpoint using OpenAI API via MCP adapter.
- [ ] Implement `/api/smarthome` endpoint for Home Assistant/local actions.
- [ ] Implement `/api/preferences` and `/api/notes` endpoints (Firestore proxy).
- [ ] Add `/modules/` directory for skills/triggers/actions.
- [ ] Add `/mcp/` directory for model adapters (OpenAI, Gemini, etc.).
- [ ] Add config for easy model/provider switching.

### 3. **Frontend (React)**
- [ ] Scaffold React app (Vite, Tailwind).
- [ ] Integrate Firebase Auth and Firestore.
- [ ] Build chat interface and sidebar.
- [ ] Connect to backend endpoints.
- [ ] Implement TTS/STT using Web APIs.

### 4. **Extensibility & Automation**
- [ ] Define module interface for new skills/triggers/actions.
- [ ] Implement example modules (e.g., weather, reminders, routines).
- [ ] Document how to add new modules or swap LLMs via MCP.

---

## MCP (Model Communication Protocol)

- **Purpose:** Standardizes requests/responses between backend and any LLM provider.
- **Adapters:** Implement for OpenAI, Gemini, etc.
- **Benefits:** Swap models/providers with minimal code changes.

---

## Example Directory Structure

GitHub Copilot
[React Frontend] <--Firebase Auth/Firestore--> [Firebase Cloud] |
| (chat/smart home API calls)
v
[Flask Backend] <----> [OpenAI API / MCP]
|
v
[Home Assistant API] (local network)

jarvis-local-backend/ │ ├── app.py ├── requirements.txt ├── .env ├── mcp/ │ ├── openai_adapter.py │ └── gemini_adapter.py ├── modules/ │ ├── weather.py │ ├── reminders.py │ └── ... ├── firebase/ │ └── serviceAccount.json ├── README.md └── ...


---

## Frontend Plan

- **React SPA** (Vite, Tailwind)
- **Sidebar:** Overview, preferences, learning log, smart home controls.
- **Chat Interface:** Text/voice input, TTS/STT, chat history.
- **Firebase Auth:** Google Sign-In.
- **Firestore:** Preferences and learning log.
- **API:** All chat and smart home actions via Flask backend.

---

## Extending Jarvis

- **Add a new skill:** Drop a new module in `/modules/` and register it.
- **Add a new LLM:** Implement an MCP adapter in `/mcp/` and update config.
- **Add a new trigger/action:** Create a module and expose an endpoint or function.

---

## Getting Started

1. **Clone the repo and install dependencies:**
    ```bash
    git clone https://github.com/your-username/jarvis-local-backend.git
    cd jarvis-local-backend
    python3 -m venv venv
    source venv/bin/activate
    ./venv/bin/python3 -m pip install -r requirements.txt
    ```

2. **Set up your `.env` file:**
    ```
    OPENAI_API_KEY=your_openai_key
    FIREBASE_SERVICE_ACCOUNT_PATH=/full/path/to/serviceAccount.json
    HA_URL=http://your-home-assistant:8123
    HA_ACCESS_TOKEN=your_home_assistant_token
    ```

3. **Run the backend:**
    ```bash
    python [app.py](http://_vscodecontentref_/3)
    ```

4. **Deploy frontend (see frontend repo for details).**

---

## Contributing

- Modular codebase: add new skills, triggers, or model adapters easily.
- PRs and suggestions welcome!

---