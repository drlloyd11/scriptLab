"""Optional Ollama JSON client. No LLM or network required for basic parsing."""
from __future__ import annotations

import json
from urllib import error, request


class OllamaError(RuntimeError):
    pass


def ask_ollama(system: str, user: str, model: str, base_url: str = "http://127.0.0.1:11434", timeout: int = 180,
               *, response_schema: dict | None = None) -> dict:
    payload = json.dumps({
        "model": model,
        "stream": False,
        "think": False,
        "format": response_schema if response_schema is not None else "json",
        "options": {"temperature": 0},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode("utf-8")
    req = request.Request(base_url.rstrip("/") + "/api/chat", data=payload,
                          headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            outer = json.loads(response.read().decode("utf-8"))
        content = outer["message"]["content"]
        return json.loads(content)
    except (OSError, error.URLError, json.JSONDecodeError, KeyError, ValueError) as e:
        raise OllamaError(f"Ollama call failed or did not return valid JSON: {e}") from e


def list_ollama_models(base_url: str = "http://127.0.0.1:11434", timeout: int = 12) -> list[str]:
    """Read locally installed model names from Ollama; never downloads a model."""
    req = request.Request(base_url.rstrip("/") + "/api/tags", method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        entries = payload.get("models", [])
        if not isinstance(entries, list):
            raise ValueError("Ollama models field is not a list")
        names = [x.get("name") or x.get("model") for x in entries if isinstance(x, dict)]
        return [x for x in names if isinstance(x, str) and x]
    except (OSError, error.URLError, json.JSONDecodeError, KeyError, ValueError) as e:
        raise OllamaError(f"Unable to list models from Ollama: {e}") from e
