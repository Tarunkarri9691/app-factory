"""List the Gemini models your key can use.
   python check_models.py          -> only lists names (uses NO quota)
   python check_models.py --test   -> also sends 1 tiny request per model to see which still have quota"""
import sys

import config  # loads .env
import os
from google import genai

key = os.getenv("GEMINI_API_KEY", "")
if not key or key.startswith("paste-your"):
    sys.exit("GEMINI_API_KEY is missing in .env")

client = genai.Client(api_key=key)
test = "--test" in sys.argv
names = []
for m in client.models.list():
    name = m.name.replace("models/", "")
    if "generateContent" in (m.supported_actions or []) and "gemini" in name:
        names.append(name)

print(f"Current MODEL in .env/config: {config.MODEL}\n")
for name in sorted(names):
    if not test:
        print(name)
        continue
    try:
        client.models.generate_content(model=name, contents="Say OK")
        print("WORKS ", name)
    except Exception as e:  # noqa: BLE001
        print("FAILS ", name, "->", str(e)[:80].replace("\n", " "))
