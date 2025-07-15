import os
import openai
import json

openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo-0125")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def extract_memories_from_text(chat_text: str):
    """
    Uses an LLM (OpenAI by default) to extract important facts, notes, or events from chat text.
    Returns a list of dicts with 'type', 'content', and optional 'tags'.
    """
    prompt = (
        "Extract any important facts, notes, or events from the following chat text. "
        "Return a JSON array of objects with 'type', 'content', and optional 'tags'.\nChat text: " + chat_text
    )
    try:
        response = openai.ChatCompletion.create(
            model=openai_chat_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2
        )
        result_text = response.choices[0].message["content"]
        memory_items = json.loads(result_text)
        return memory_items
    except Exception as e:
        print(f"Error in extract_memories_from_text: {e}")
        return []
