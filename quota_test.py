# quota_test.py
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

for m in ["gemini-flash-lite-latest", "gemini-3.6-flash", "gemini-omni-1.1-flash"]:
    try:
        r = client.models.generate_content(model=m, contents="Say OK")
        print(m, "->", r.text.strip())
    except Exception as e:
        print(m, "-> FAILED:", str(e)[:120])