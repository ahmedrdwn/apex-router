#!/usr/bin/env python3
"""apex-router delegation logger (PostToolUse hook for Task/Agent).

Appends one JSON line per delegation to <project>/.router/log.jsonl.
It never blocks the session: any error exits silently with code 0.
Prompt text is not stored, only its first 120 characters and an
escalation marker if present.
"""
import json
import os
import re
import sys
import time
import uuid

ESC = re.compile(r"\[APEX-ESCALATE\s+from=(\w+)\s+to=(\w+)\]")
TIER_BY_AGENT = {
    "apex-scout": "S", "apex-grunt": "E", "apex-builder": "N",
    "apex-architect": "H", "apex-verifier": "V",
}
TIER_BY_MODEL = {"haiku": "E", "sonnet": "N", "opus": "H", "fable": "X"}
PROXIES = {"general-purpose", "explore", "claude", ""}


def usage_of(resp):
    if not isinstance(resp, dict):
        return None
    u = resp.get("usage")
    if isinstance(u, dict) and u:
        keys = ("input_tokens", "output_tokens",
                "cache_creation_input_tokens", "cache_read_input_tokens")
        return {k: u.get(k, 0) for k in keys if k in u} or None
    for k in ("total_tokens", "totalTokens"):
        if k in resp:
            return {"total_tokens": resp[k]}
    return None


def build_record(event):
    ti = event.get("tool_input") or {}
    agent = (ti.get("subagent_type") or "").strip()
    short = agent.split(":")[-1]
    model = (ti.get("model") or "").strip().lower()
    prompt = ti.get("prompt") or ""
    m = ESC.search(prompt)
    tier = TIER_BY_AGENT.get(short) or TIER_BY_MODEL.get(model, "?")
    if short == "apex-architect" and model == "fable":
        tier = "X"
    return {
        "ts": int(time.time()),
        "source": "hook",
        "id": uuid.uuid4().hex[:12],
        "session_id": event.get("session_id", ""),
        "agent": agent or "(default)",
        "named_tier": short in TIER_BY_AGENT,
        "fallback": short.lower() in PROXIES,
        "model": model or "(not passed)",
        "tier": tier,
        "escalated_from": m.group(1) if m else None,
        "escalated_to": m.group(2) if m else None,
        "prompt_head": prompt[:120],
        "tokens": usage_of(event.get("tool_response")),
    }


def main():
    try:
        event = json.load(sys.stdin)
        cwd = event.get("cwd") or os.getcwd()
        rec = build_record(event)
        d = os.path.join(cwd, ".router")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
