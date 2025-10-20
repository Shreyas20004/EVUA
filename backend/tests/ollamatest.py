import os
import json
import sys
from typing import List, Dict, Any

def _http_get_json(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        import requests  # type: ignore
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except ImportError:
        # Fallback to stdlib if requests is not available
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read()
            return json.loads(data.decode("utf-8"))

def probe_ollama(host: str, timeout: float = 3.0) -> List[Dict[str, Any]]:
    host = host.rstrip("/")
    url = f"{host}/api/tags"
    data = _http_get_json(url, timeout=timeout)
    models = data.get("models", [])
    if not isinstance(models, list):
        raise RuntimeError("Unexpected response structure from Ollama /api/tags")
    return models

def main() -> int:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    try:
        models = probe_ollama(host)
        print(f"OK: Connected to Ollama at {host}")
        if models:
            print(f"Models ({len(models)}): " + ", ".join(m.get("name", "?") for m in models))
        else:
            print("No models found. You may need to pull a model, e.g. `ollama pull llama3`.")
        return 0
    except Exception as e:
        print(f"ERROR: Could not connect to Ollama at {host}: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    # Allow running as a standalone connectivity check
    raise SystemExit(main())

# Optional: pytest-style test (run with `pytest -q`)
try:
    import pytest  # type: ignore

    def test_ollama_connection():
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
        try:
            models = probe_ollama(host)
        except Exception as e:
            pytest.skip(f"Ollama not reachable at {host}: {e}")
        assert isinstance(models, list)
except Exception:
    # If pytest isn't installed, ignore test definition
    pass