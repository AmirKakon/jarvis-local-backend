from flask import Blueprint, request, jsonify
from services.chat_service import get_chat_response, update_chat_history, get_chat_history

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat_endpoint():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    # Get current chat history
    chat_history = get_chat_history()
    # Add system prompt only once at the start
    if not chat_history or chat_history[0].get("role") != "system":
        chat_history.insert(0, {"role": "system", "content": "You are Jarvis, a helpful and highly personalized AI assistant."})
    chat_history.append({"role": "user", "content": user_input})
    try:
        full_response_text = get_chat_response(chat_history)
        chat_history.append({"role": "assistant", "content": full_response_text})
        update_chat_history(chat_history)
        return jsonify({"response": full_response_text})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500
