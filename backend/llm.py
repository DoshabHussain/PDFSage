import os
import re
import requests


class LLMError(Exception):
    pass


class OllamaLLM:
    """Local LLM through Ollama (https://ollama.com). No API key, runs on your PC.
    Example models: qwen2.5:3b, qwen3:4b, llama3.2:3b"""

    def __init__(self, model: str | None = None, host: str | None = None):
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    def models(self) -> list[str]:
        try:
            r = requests.get(self.host + "/api/tags", timeout=3)
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def is_up(self) -> bool:
        try:
            return requests.get(self.host + "/api/tags", timeout=2).ok
        except Exception:
            return False

    def generate(self, prompt: str, json_mode: bool = False, max_tokens: int = 700) -> str:
        payload = {"model": self.model, "stream": False,
                   "messages": [{"role": "user", "content": prompt}],
                   "options": {"num_ctx": 4096, "temperature": 0.3, "num_predict": max_tokens}}
        if json_mode:
            payload["format"] = "json"
        if self.model.startswith("qwen3"):
            payload["think"] = False  # skip slow reasoning mode
        try:
            r = requests.post(self.host + "/api/chat", json=payload, timeout=600)
            if r.status_code == 400 and "think" in payload:
                payload.pop("think")
                r = requests.post(self.host + "/api/chat", json=payload, timeout=600)
            if r.status_code == 404:
                raise LLMError(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
            r.raise_for_status()
        except LLMError:
            raise
        except requests.ConnectionError:
            raise LLMError("Ollama is not running. Start it and run: ollama pull " + self.model)
        except requests.RequestException as e:
            raise LLMError(str(e))
        try:
            text = r.json()["message"]["content"]
        except (KeyError, ValueError, TypeError) as e:
            raise LLMError(f"Unexpected response from Ollama: {e}")
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
