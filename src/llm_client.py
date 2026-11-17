"""Optional LLM draft of the weekly note. The published note uses the sentence template (no key needed).

Only used when .env sets LLM_PROVIDER and LLM_API_KEY. The model receives the week's fact sheet (aggregates
only: no visitor, no customer data) and must use those numbers only. Whatever it writes is then checked by
src/check_numbers.py and rejected if any number does not match the data.

Supported provider: LLM_PROVIDER=anthropic (Claude, via the official `anthropic` Python SDK, installed
separately: pip install anthropic). Optional: LLM_MODEL (default below).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM = (
    "You write the weekly conversion-rate-optimisation note of an e-commerce team. Write 5 to 8 plain sentences: "
    "what moved, the likely reason, what to do next. Use ONLY numbers that appear in the fact sheet, written "
    "exactly as they appear there (same rounding, same unit). Say 'pp' for a change in percentage points and "
    "'%' for a relative change. Name the period of every comparison (week on week, vs the same week last year). "
    "Say 'per session' or 'per user' for conversion, 'gross' or 'net of returns' for revenue. "
    "If the fact sheet marks a move as a traffic-mix effect, do not call it a problem."
)


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def available() -> bool:
    env = load_env()
    return bool(env.get("LLM_PROVIDER")) and bool(env.get("LLM_API_KEY"))


def draft(facts: dict) -> str | None:
    """Return the model's draft, or None (no key, unsupported provider, refusal or API error)."""
    env = load_env()
    if not available() or env["LLM_PROVIDER"].lower() != "anthropic":
        return None
    try:
        import anthropic  # optional dependency
    except ImportError:
        return None
    client = anthropic.Anthropic(api_key=env["LLM_API_KEY"])
    prompt = "Fact sheet (JSON):\n" + json.dumps(facts, indent=1, ensure_ascii=False)
    try:
        response = client.beta.messages.create(
            model=env.get("LLM_MODEL", DEFAULT_MODEL),
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # if the model declines, the API retries on a fallback model
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        print(f"[llm] request failed, template used instead: {e}")
        return None
    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or None
