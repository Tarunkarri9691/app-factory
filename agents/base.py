"""Shared Gemini helper: model fallback, quota handling, token logging, JSON/file parsing."""
from __future__ import annotations

import json
import os
import re
import threading
import time

from google import genai
from google.genai import types

import config

_client = None
_lock = threading.Lock()
_current_run = "default"


class LLMError(Exception):
    """Any model-call problem with a human-readable message."""


class QuotaExhausted(LLMError):
    """Every configured model is out of free quota (or not found)."""


def set_run(run_id: str) -> None:
    global _current_run
    _current_run = run_id


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key or key.startswith("paste-your"):
            raise LLMError("GEMINI_API_KEY is missing. Put your key in the .env file and restart.")
        _client = genai.Client(api_key=key)
    return _client


def load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _models() -> list[str]:
    out: list[str] = []
    for m in [config.MODEL, *config.FALLBACK_MODELS]:
        m = m.replace("models/", "").strip()
        if m and m not in out:
            out.append(m)
    return out


def _retry_delay(msg: str):
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", msg)
    if m:
        return float(m.group(1))
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", msg)
    return float(m.group(1)) if m else None


def call_llm(system: str, user: str, agent: str, max_tokens: int | None = None,
             json_mode: bool = False) -> str:
    start = time.time()
    cfg_args = {"system_instruction": system, "max_output_tokens": max_tokens or config.MAX_TOKENS}
    if json_mode:
        cfg_args["response_mime_type"] = "application/json"
    cfg = types.GenerateContentConfig(**cfg_args)

    resp, used_model, notes = None, None, []
    for model in _models():
        for attempt in range(3):
            try:
                resp = _get_client().models.generate_content(model=model, contents=user, config=cfg)
                used_model = model
                break
            except LLMError:
                raise
            except Exception as e:  # noqa: BLE001
                msg, code = str(e), getattr(e, "code", None)
                if code == 404 or "NOT_FOUND" in msg:
                    notes.append(f"{model}: model name not found")
                    break                                   # try next model
                if code == 429 or "RESOURCE_EXHAUSTED" in msg:
                    delay = _retry_delay(msg)
                    if "PerDay" not in msg and delay is not None and delay <= 70 and attempt < 2:
                        time.sleep(delay + 1)               # per-minute limit: wait and retry
                        continue
                    notes.append(f"{model}: free quota used up")
                    break                                   # daily limit: try next model
                if code in (500, 502, 503, 504) or "UNAVAILABLE" in msg:
                    time.sleep(4 * (attempt + 1))           # Google side busy: retry
                    continue
                raise LLMError(f"Gemini error with {model}: {msg[:300]}") from e
        if resp is not None:
            break

    if resp is None:
        if notes:
            raise QuotaExhausted(
                "No model could answer. " + "; ".join(notes) + ".\n"
                "Fix: run `python check_models.py`, put models that work in MODEL / FALLBACK_MODELS "
                "in .env, or enable billing / use a key from a new Google project."
            )
        raise LLMError("Gemini is busy right now. Wait a minute and press Retry.")

    try:
        text = resp.text or ""
    except Exception:  # noqa: BLE001
        text = ""
    if not text.strip():
        raise LLMError("Gemini returned an empty reply (output limit or safety filter). Press Retry.")

    usage = getattr(resp, "usage_metadata", None)
    entry = {
        "agent": agent,
        "model": used_model,
        "input_tokens": (getattr(usage, "prompt_token_count", 0) or 0) if usage else 0,
        "output_tokens": (getattr(usage, "candidates_token_count", 0) or 0) if usage else 0,
        "seconds": round(time.time() - start, 2),
        "output": text,
    }
    config.LOGS_DIR.mkdir(exist_ok=True)
    with _lock:
        with open(config.LOGS_DIR / f"{_current_run}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    return text


def usage_for_run(run_id: str) -> dict:
    path = config.LOGS_DIR / f"{run_id}.jsonl"
    totals = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            totals["input_tokens"] += e["input_tokens"]
            totals["output_tokens"] += e["output_tokens"]
            totals["calls"] += 1
    return totals


def extract_json(text: str):
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL)
    if m:
        t = m.group(1).strip()
    starts = [i for i in (t.find("{"), t.find("[")) if i != -1]
    if starts:
        t = t[min(starts):]
    obj, _ = json.JSONDecoder().raw_decode(t)
    return obj


def call_json(system: str, user: str, agent: str, schema=None, retries: int = 1) -> dict:
    """Call the model in JSON mode, validate with a Pydantic schema; retry once on bad JSON."""
    prompt, last_err = user, None
    for _ in range(retries + 1):
        text = call_llm(system, prompt, agent, json_mode=True)
        try:
            data = extract_json(text)
            if schema is not None:
                data = schema.model_validate(data).model_dump()
            return data
        except Exception as e:  # noqa: BLE001
            last_err = e
            prompt = (
                f"{user}\n\nYour previous reply was invalid ({str(e)[:200]}). "
                "Return ONLY valid JSON matching the required schema."
            )
    raise LLMError(f"{agent} returned invalid JSON twice: {str(last_err)[:200]}")


_FILE_RE = re.compile(r"=== FILE: (.+?) ===\n(.*?)\n=== END FILE ===", re.DOTALL)


def parse_files(text: str) -> dict:
    """Parse '=== FILE: path === ... === END FILE ===' blocks into {path: content}."""
    files = {}
    for path, content in _FILE_RE.findall(text):
        content = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", content.strip("\n"))
        files[path.strip()] = content + "\n"
    return files
