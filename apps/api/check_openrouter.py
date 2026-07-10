"""Check OpenRouter connectivity without printing credentials."""
import os

import httpx

key = os.getenv("OPENROUTER_API_KEY")
print("KEY_SET", bool(key), "LENGTH", len(key or ""))
response = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={
        "model": os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.6"),
        "messages": [{"role": "user", "content": "Reply with JSON containing ok true"}],
        "response_format": {"type": "json_object"},
        "max_tokens": 50,
    },
    timeout=30,
)
print("STATUS", response.status_code)
print(response.text[:1200])
