import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_API_URL")
MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME")
def query_ollama(MODEL_NAME: str, system_prompt: str, user_input: str, history=None):
    if history is None:
        history = []

    # Combine history
    full_prompt = system_prompt + "\n\n"
    for msg in history:
        full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
    full_prompt += f"USER: {user_input}\nASSISTANT:"

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")
