import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
API_KEY = os.getenv("GEMINI_API_KEY")

if MODEL is None :
    raise ValueError("GEMINI_MODEL is not set")

if API_KEY is None:
    raise ValueError("GEMINI_API_KEY is not set")

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        timeout=60_000,  # ms
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
)


odpowiedz = client.models.generate_content(
    model=MODEL,
    contents="Napisz w jednym zdaniu, czym jest agent AI.",
)
print(odpowiedz.text)

client.close()

