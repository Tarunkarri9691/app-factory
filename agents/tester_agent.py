"""Tester agent: writes pytest tests from acceptance criteria. Execution happens in the sandbox."""
import json

import config
from agents.base import call_llm, load_prompt, parse_files


def write_tests(state: dict) -> dict:
    code = "\n\n".join(
        f"=== FILE: {p} ===\n{c}\n=== END FILE ===" for p, c in state["files"].items()
    )
    user = (
        f"ACCEPTANCE CRITERIA:\n{json.dumps(state['requirements']['acceptance_criteria'], indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(state['architecture'], indent=2)}\n\n"
        f"CODE:\n{code}"
    )
    text = call_llm(load_prompt("tester"), user, "tester", config.CODER_MAX_TOKENS)
    skip = {"conftest.py", "__init__.py"}      # the pipeline provides these itself
    return {
        p: c for p, c in parse_files(text).items()
        if p.startswith("tests/") and p.split("/")[-1] not in skip
    }
