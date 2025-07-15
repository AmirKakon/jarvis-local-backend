from flask import Blueprint, request, jsonify
from services.chat_service import chat_response, update_chat_history, get_chat_history

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat_endpoint():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    # Get current chat history
    chat_history = get_chat_history()
    try:
        full_response_text = chat_response(user_input)
        # Update chat history with new user and assistant messages
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": full_response_text})
        update_chat_history(chat_history)
        return jsonify({"response": full_response_text})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500
