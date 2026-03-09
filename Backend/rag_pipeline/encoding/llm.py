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


def get_llm(provider: str = "openai", temperature: float = 0, json_mode: bool = False):
    """
    Return a LangChain BaseChatModel for the given provider.

    json_mode=True:
      - OpenAI: no change needed (JsonOutputParser handles it)
      - Ollama: passes format="json" to constrain output to valid JSON
    """
    provider = (provider or "openai").lower().strip()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs = {}
        if json_mode:
            kwargs["format"] = "json"
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
            **kwargs,
        )

    # Default: openai
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=temperature,
    )


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
