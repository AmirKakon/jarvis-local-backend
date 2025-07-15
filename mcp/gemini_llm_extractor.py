import os
import google.generativeai as genai
import json

gemini_chat_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def extract_memories_from_text(chat_text: str):
    """
    Uses Gemini to extract important facts, notes, or events from chat text.
    Returns a list of dicts with 'type', 'content', and optional 'tags'.
    """
    prompt = (
        "Extract any important facts, notes, or events from the following chat text. "
        "Return a JSON array of objects with 'type', 'content', and optional 'tags'.\nChat text: " + chat_text
    )
    try:
        model = genai.GenerativeModel(gemini_chat_model)
        response = model.generate_content(prompt)
        result_text = response.text
        memory_items = json.loads(result_text)
        return memory_items
    except Exception as e:
        print(f"Error in gemini extract_memories_from_text: {e}")
        return []
