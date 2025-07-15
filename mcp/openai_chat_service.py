import openai
import os

openai_chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo-0125")
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_chat_response(messages):
    # Validate messages format
    if not all(isinstance(m, dict) and "role" in m and "content" in m for m in messages):
        raise ValueError("All messages must be dicts with 'role' and 'content' keys.")
    response = openai.chat.completions.create(
        model=openai_chat_model,
        messages=messages
    )
    return response.choices[0].message.content
