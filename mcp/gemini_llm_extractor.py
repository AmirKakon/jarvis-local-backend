import os
import google.generativeai as genai
from config.prompts import llm_extractor_prompt
from mcp.llm_utils import strip_code_block, is_meta_response, safe_json_loads

gemini_chat_model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def extract_memories_from_text(chat_text: str):
    """
    Uses Gemini to extract important facts, notes, preferences, or events from chat text.
    Returns a list of dicts with 'type', 'content', and optional 'tags'.
    """
    prompt = llm_extractor_prompt(chat_text)
    try:
        model = genai.GenerativeModel(gemini_chat_model)
        response = model.generate_content(prompt)
        result_text = response.text.strip() if response.text else ""
        if not result_text:
            print("Gemini LLM returned empty response for memory extraction.")
            return []
        if is_meta_response(result_text):
            print(f"Gemini LLM returned a meta-response instead of extracted memories: {result_text}")
            return []
        cleaned = strip_code_block(result_text)
        return safe_json_loads(cleaned)
    except Exception as e:
        print(f"Error in gemini extract_memories_from_text: {e}")
        return []
