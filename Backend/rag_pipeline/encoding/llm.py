"""
LLM Factory
-----------
Central place to construct a LangChain chat model.

Supported providers:
  "openai"  → ChatOpenAI  (requires OPENAI_API_KEY)
  "ollama"  → ChatOllama  (requires Ollama running at OLLAMA_BASE_URL)

Usage inside nodes:
    llm = get_llm(state.get("provider", "openai"))
    llm_json = get_llm(state.get("provider", "openai"), json_mode=True)
"""

import json
import os
import re

# Cache LLM instances — avoids creating a new httpx client on every pipeline node call.
# Key: (provider, temperature, json_mode). Env vars are fixed at startup.
_llm_cache: dict = {}


def get_llm(provider: str = "openai", temperature: float = 0, json_mode: bool = False,
            model: str | None = None):
    """
    Return a LangChain BaseChatModel for the given provider.

    json_mode=True:
      - OpenAI: no change needed (JsonOutputParser handles it)
      - Ollama: passes format="json" to constrain output to valid JSON

    model: optional override for the model name (e.g. a user-selected Ollama model).
           Falls back to the env-var default if not supplied.

    Instances are cached to avoid creating a new HTTP client on every call.
    """
    provider = (provider or "openai").lower().strip()
    cache_key = (provider, temperature, json_mode, model)

    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs = {}
        if json_mode:
            kwargs["format"] = "json"
        llm = ChatOllama(
            model=model or os.getenv("OLLAMA_MODEL"),
            base_url=os.getenv("OLLAMA_BASE_URL"),
            temperature=temperature,
            **kwargs,
        )
    else:
        # Default: openai
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=temperature,
        )

    _llm_cache[cache_key] = llm
    return llm


def safe_json_parse(text: str) -> dict:
    """
    Robustly parse JSON from LLM output that may include:
    - Markdown code fences (```json ... ```)
    - Prose before/after the JSON block
    - Minor formatting quirks from smaller local models
    """
    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # 3. First {...} block in the text
    brace = re.search(r"\{[\s\S]+\}", text)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM output: {text[:300]!r}")


def check_ollama() -> dict:
    """
    Probe the Ollama server and return status + available model list.
    Uses requests (more reliable on Windows than urllib).
    Tries /api/tags first; falls back to a root ping if that fails.
    """
    import requests as _req

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    # ── 1. Full probe: get model list ─────────────────────────────────────────
    try:
        resp = _req.get(f"{base}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return {"available": True, "models": models, "base_url": base}
    except _req.exceptions.ConnectionError as e:
        detail = f"Cannot reach Ollama at {base} — is it running? ({e})"
    except _req.exceptions.Timeout:
        detail = f"Ollama at {base} timed out"
    except Exception as e:
        detail = str(e)

    # ── 2. Fallback: bare root ping (older Ollama versions) ──────────────────
    try:
        resp = _req.get(base, timeout=5)
        # Any 2xx/4xx reply means the server is up, just model list failed
        if resp.status_code < 500:
            return {"available": True, "models": [], "base_url": base,
                    "warning": "Connected but could not list models"}
    except Exception:
        pass

    return {"available": False, "models": [], "error": detail, "base_url": base}
