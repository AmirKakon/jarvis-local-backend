import os
import openai
import json
from config.prompts import llm_extractor_prompt

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
        # Check for meta-responses (LLM asking for input or instructions)
        meta_phrases = [
            "please provide the chat text",
            "i will then extract",
            "provide the text",
            "i can help you extract",
            "let me know what to analyze"
        ]
        if any(phrase in result_text.lower() for phrase in meta_phrases):
            print(f"OpenAI LLM returned a meta-response instead of extracted memories: {result_text}")
            return []
        try:
            memory_items = json.loads(result_text)
            return memory_items
        except Exception as json_err:
            print(f"OpenAI LLM did not return valid JSON. Raw output: {result_text}")
            print(f"JSON decode error: {json_err}")
            return []
    except Exception as e:
        print(f"Error in extract_memories_from_text: {e}")
        return []
