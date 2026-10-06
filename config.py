"""Central settings: model, limits, paths, doc sources."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env", override=True)   # load FIRST so every setting below sees .env

# --- LLM (Gemini) ---
MODEL = os.getenv("MODEL", "gemini-3.8-flash").replace("models/", "").strip()
FALLBACK_MODELS = [
    m.strip().replace("models/", "")
    for m in os.getenv("FALLBACK_MODELS", "").split(",")
    if m.strip()
]
MAX_TOKENS = 16000          # output limit (Gemini "thinking" tokens count toward it)
CODER_MAX_TOKENS = 32000

# --- Free-tier friendly defaults (a run needs roughly 5-10 model calls) ---
SINGLE_CODER_CALL = os.getenv("SINGLE_CODER_CALL", "1") == "1"   # 1 call writes all files
MAX_PARALLEL_CODERS = 1
MAX_TEST_RETRIES = int(os.getenv("MAX_TEST_RETRIES", 2))
MAX_REVIEW_ROUNDS = int(os.getenv("MAX_REVIEW_ROUNDS", 1))

# --- Paths ---
PROMPTS_DIR = BASE_DIR / "prompts"
WORKSPACE_DIR = BASE_DIR / "workspace"
LOGS_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "rag" / "docs"
VECTORDB_DIR = BASE_DIR / "rag" / "vectordb"
COLLECTION = "framework_docs"

# --- Sandbox ---
DOCKER_IMAGE = "app-factory-sandbox"
SANDBOX_TIMEOUT = 120  # seconds
ALLOW_LOCAL_EXEC = os.getenv("ALLOW_LOCAL_EXEC", "0") == "1"

# --- Framework docs to ingest (one stack first: FastAPI + SQLite) ---
DOC_URLS = [
    "https://fastapi.tiangolo.com/tutorial/first-steps/",
    "https://fastapi.tiangolo.com/tutorial/path-params/",
    "https://fastapi.tiangolo.com/tutorial/query-params/",
    "https://fastapi.tiangolo.com/tutorial/body/",
    "https://fastapi.tiangolo.com/tutorial/handling-errors/",
    "https://fastapi.tiangolo.com/tutorial/sql-databases/",
    "https://fastapi.tiangolo.com/tutorial/testing/",
    "https://fastapi.tiangolo.com/tutorial/static-files/",
    "https://docs.pydantic.dev/latest/concepts/models/",
    "https://docs.sqlalchemy.org/en/20/orm/quickstart.html",
]
