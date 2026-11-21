"""Shared helpers for the #727 Part 2 run. ASCII-only output (cp1252 console)."""
import json
import os
import pathlib
import time

import anthropic
from dotenv import dotenv_values

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
OUT = ROOT / "out"
LOGS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

KEY_NAME = "CRUX_727_ANTHROPIC_KEY"
def _main_checkout_env():
    """The .env at the main checkout's root, found through git so worktrees reach it too."""
    import subprocess
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True, cwd=pathlib.Path(__file__).parent).stdout.strip()
    return pathlib.Path(common).parent / ".env" if common else pathlib.Path(".env")


REPO_ENV = _main_checkout_env()

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
OPUS = "claude-opus-5-5"

# USD per 1M tokens: input, 5-min cache write, 1-hour cache write, cache read, output.
# From docs/research/claude-anthropic-api-model.md item 9 (Haiku: prompts up to 100K).
PRICES = {
    HAIKU: (0.10, 0.125, 0.20, 0.01, 0.50),
    SONNET: (2.00, 2.50, 4.00, 0.10, 10.00),
    OPUS: (4.00, 5.00, 8.00, 0.20, 20.00),
}

SPEND_STOP = float(os.environ.get("CRUX_727_SPEND_STOP", "3.0"))


def _load_key():
    if os.environ.get(KEY_NAME):
        return os.environ[KEY_NAME], "process env"
    if REPO_ENV.exists():
        val = dotenv_values(REPO_ENV).get(KEY_NAME)
        if val:
            return val.strip(), "repo .env"
    raise SystemExit(f"[ERROR] {KEY_NAME} not found in process env or repo .env")


def client():
    key, where = _load_key()
    print(f"[OK] key loaded from {where} (value not shown)")
    return anthropic.Anthropic(api_key=key, max_retries=3)


def usage_dict(u):
    d = {
        "input_tokens": u.input_tokens or 0,
        "output_tokens": u.output_tokens or 0,
        "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
        "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
    }
    cc = getattr(u, "cache_creation", None)
    if cc is not None:
        d["write_5m"] = getattr(cc, "ephemeral_5m_input_tokens", 0) or 0
        d["write_1h"] = getattr(cc, "ephemeral_1h_input_tokens", 0) or 0
    else:
        d["write_5m"], d["write_1h"] = d["cache_write"], 0
    return d


def cost(model, u, batch=False):
    p_in, p_w5, p_w1, p_r, p_out = PRICES[model]
    c = (
        u["input_tokens"] * p_in
        + u["write_5m"] * p_w5
        + u["write_1h"] * p_w1
        + u["cache_read"] * p_r
        + u["output_tokens"] * p_out
    ) / 1e6
    return c * (0.5 if batch else 1.0)


import threading

_LOCK = threading.Lock()
_PID = os.getpid()
# Spend before per-process logs existed (smoke + history-edit tests + first trial), from logs/spent_base.json.
_BASE_FILE = LOGS / "spent_base.json"


def spent():
    """Total spend = base + the sum of every per-process call log. Safe across processes."""
    total = json.loads(_BASE_FILE.read_text())["usd"] if _BASE_FILE.exists() else 0.0
    for p in LOGS.glob("*_p*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                total += json.loads(line)["cost"]
            except (json.JSONDecodeError, KeyError):
                pass
    return total


def add_spent(usd):
    return spent()


def guard():
    if spent() >= SPEND_STOP:
        raise SystemExit(f"[STOP] spend stop reached: {spent():.4f} USD")


def log_call(logname, model, resp, tag, extra=None, batch=False):
    u = usage_dict(resp.usage)
    c = cost(model, u, batch=batch)
    thinking_chars = sum(
        len(getattr(b, "thinking", "") or "") for b in resp.content if b.type == "thinking"
    )
    rec = {
        "t": time.time(),
        "tag": tag,
        "model": model,
        "stop_reason": resp.stop_reason,
        "stop_details": (resp.stop_details.to_dict() if getattr(resp, "stop_details", None) else None),
        "usage": u,
        "cost": c,
        "thinking_blocks": sum(1 for b in resp.content if b.type == "thinking"),
        "thinking_chars": thinking_chars,
        "request_id": getattr(resp, "_request_id", None),
    }
    if extra:
        rec.update(extra)
    with _LOCK:
        with open(LOGS / f"{logname}_p{_PID}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return rec, None


def text_of(resp):
    return "".join(b.text for b in resp.content if b.type == "text")
