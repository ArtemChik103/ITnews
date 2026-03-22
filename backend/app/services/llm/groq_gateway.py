from __future__ import annotations

import time

import httpx

from app.core.config import get_settings


class GroqGateway:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(self, messages: list[dict], temperature: float = 0.1) -> dict:
        models = [
            self.settings.groq_model_primary,
            self.settings.groq_model_fallback,
            self.settings.groq_model_fast,
        ]
        last_error = None

        for index, model in enumerate(models):
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.settings.groq_timeout_seconds) as client:
                    response = await client.post(
                        self.settings.groq_api_url,
                        headers={
                            "Authorization": f"Bearer {self.settings.groq_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

            content = payload["choices"][0]["message"]["content"]
            return {
                "text": content,
                "provider": self.settings.llm_provider,
                "model": model,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "degraded_mode": None if index == 0 else "llm_fallback",
            }

        raise RuntimeError(f"All Groq models failed: {last_error}")
