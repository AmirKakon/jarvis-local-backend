import os
import google.generativeai as genai
import json
from config.prompts import llm_extractor_prompt

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
        # Check for meta-responses (LLM asking for input or instructions)
        meta_phrases = [
            "please provide the chat text",
            "i will then extract",
            "provide the text",
            "i can help you extract",
            "let me know what to analyze"
        ]
        if any(phrase in result_text.lower() for phrase in meta_phrases):
            print(f"Gemini LLM returned a meta-response instead of extracted memories: {result_text}")
            return []
        try:
            memory_items = json.loads(result_text)
            return memory_items
        except Exception as json_err:
            print(f"Gemini LLM did not return valid JSON. Raw output: {result_text}")
            print(f"JSON decode error: {json_err}")
            return []
    except Exception as e:
        print(f"Error in gemini extract_memories_from_text: {e}")
        return []
