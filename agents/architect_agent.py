"""Architect agent: requirements -> stack, file tree, tasks. Uses RAG for framework docs."""
import json

from agents.base import call_json, load_prompt
from orchestrator.state import Architecture
from rag import retriever


def run(requirements: dict) -> dict:
    queries = [
        "FastAPI project structure routes and static files",
        "SQLAlchemy models SQLite session dependency",
        "FastAPI testing with TestClient",
        requirements.get("summary", ""),
    ]
    docs = "\n\n".join(filter(None, (retriever.query(q, k=2) for q in queries)))
    user = (
        f"REQUIREMENTS:\n{json.dumps(requirements, indent=2)}\n\n"
        f"REFERENCE DOCS:\n{docs or '(none - RAG empty)'}"
    )
    return call_json(load_prompt("architect"), user, "architect", Architecture)
