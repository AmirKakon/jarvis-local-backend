import os
import google.generativeai as genai

gemini_chat_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_chat_response(messages):
    """
    Uses Gemini to generate a chat response given a list of messages.
    messages: List of dicts with 'role' and 'content'.
    Returns the response string.
    """
    # Gemini expects a single prompt string, so concatenate messages
    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    model = genai.GenerativeModel(gemini_chat_model)
    response = model.generate_content(prompt)
    return response.text
