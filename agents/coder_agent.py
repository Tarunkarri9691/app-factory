"""Coder agents: build each task in parallel, then fix problems from tests/review."""
import json
from concurrent.futures import ThreadPoolExecutor

import config
from agents.base import call_llm, load_prompt, parse_files
from rag import retriever


def _context(state: dict) -> str:
    return (
        f"REQUIREMENTS:\n{json.dumps(state['requirements'], indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(state['architecture'], indent=2)}"
    )


def build_task(state: dict, task: dict) -> dict:
    docs = retriever.query(f"{task['title']} {task['description']}", k=3)
    user = (
        f"{_context(state)}\n\nYOUR TASK:\n{json.dumps(task, indent=2)}\n\n"
        f"REFERENCE DOCS:\n{docs or '(none)'}\n\n"
        f"Write ONLY these files: {task['files']}"
    )
    text = call_llm(load_prompt("coder"), user, "coder", config.CODER_MAX_TOKENS)
    files = parse_files(text)
    owned = {p: c for p, c in files.items() if p in task["files"]}
    return owned or files


def build_all(state: dict) -> dict:
    tasks = state["architecture"]["tasks"]
    if config.SINGLE_CODER_CALL:
        # One model call writes every file (saves free-tier quota).
        all_files = []
        for t in tasks:
            all_files += [f for f in t["files"] if f not in all_files]
        combined = {
            "id": "ALL",
            "title": "Entire application",
            "files": all_files,
            "description": "Implement ALL of these tasks and write every listed file:\n"
            + json.dumps(tasks, indent=2),
        }
        return build_task(state, combined)
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_CODERS) as ex:
        results = list(ex.map(lambda t: build_task(state, t), tasks))
    merged = {}
    for r in results:
        merged.update(r)
    return merged


def fix(state: dict) -> dict:
    """Return only the changed files. Tests are never modified by the coder."""
    current = "\n\n".join(
        f"=== FILE: {p} ===\n{c}\n=== END FILE ===" for p, c in state["files"].items()
    )
    user = (
        f"{_context(state)}\n\nCURRENT FILES:\n{current}\n\n"
        f"PROBLEMS TO FIX:\n{state['feedback']}"
    )
    text = call_llm(load_prompt("coder_fix"), user, "coder_fix", config.CODER_MAX_TOKENS)
    return {p: c for p, c in parse_files(text).items() if not p.startswith("tests/")}
