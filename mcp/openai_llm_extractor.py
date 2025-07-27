import os
import openai
from config.prompts import llm_extractor_prompt
from mcp.llm_utils import strip_code_block, is_meta_response, safe_json_loads

openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo-0125")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def extract_memories_from_text(chat_text: str):
    """
    Uses an LLM (OpenAI by default) to extract important facts, notes, or events from chat text.
    Returns a list of dicts with 'type', 'content', and optional 'tags'.
    """
    prompt = llm_extractor_prompt(chat_text)
    try:
        response = openai.ChatCompletion.create(
            model=openai_chat_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2
        )
        result_text = response.choices[0].message["content"].strip() if response.choices[0].message["content"] else ""
        if not result_text:
            print("OpenAI LLM returned empty response for memory extraction.")
            return []
        if is_meta_response(result_text):
            print(f"OpenAI LLM returned a meta-response instead of extracted memories: {result_text}")
            return []
        cleaned = strip_code_block(result_text)
        return safe_json_loads(cleaned)
    except Exception as e:
        print(f"Error in extract_memories_from_text: {e}")
        return []
