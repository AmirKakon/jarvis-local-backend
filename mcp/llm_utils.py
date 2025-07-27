import re
import json

def strip_code_block(text: str) -> str:
    """
    Removes Markdown code block markers (e.g., ```json ... ```) from LLM output.
    """
    cleaned = text.strip()
    # Remove triple backticks and optional language
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned)
        cleaned = re.sub(r'```$', '', cleaned)
    return cleaned.strip()

def is_meta_response(text: str) -> bool:
    """
    Returns True if the LLM output is a meta-response (asking for input or instructions).
    """
    meta_phrases = [
        "please provide the chat text",
        "i will then extract",
        "provide the text",
        "i can help you extract",
        "let me know what to analyze"
    ]
    return any(phrase in text.lower() for phrase in meta_phrases)

def safe_json_loads(text: str):
    """
    Attempts to parse JSON, returns [] on failure and logs error.
    """
    try:
        return json.loads(text)
    except Exception as e:
        print(f"LLM did not return valid JSON. Raw output: {text}")
        print(f"JSON decode error: {e}")
        return []
