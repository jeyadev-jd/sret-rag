import httpx
import asyncio
from typing import AsyncGenerator
from core.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.pc4_url
        self.client = httpx.AsyncClient(timeout=settings.llm_timeout)

    async def complete(self, prompt: str, max_tokens: int = 2048) -> str:
        """Sync completion → single response."""
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": self.settings.llm_temperature,
            "top_p": 0.95,
            "stop": ["</s>", "Human:", "User:", "Instruct:", "Question:", "<|", "Student:", "Tutor:", "Exercise", "\nQ:", "\nA:"]
        }

        response = await self.client.post(
            f"{self.base_url}/completion",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content", "").strip()

    async def stream_complete(self, prompt: str, max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        """Stream completion → token-by-token."""
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": self.settings.llm_temperature,
            "top_p": 0.95,
            "stream": True,
            "stop": ["</s>", "Human:", "User:"]
        }

        async with self.client.stream(
            "POST",
            f"{self.base_url}/completion",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        import json
                        data = json.loads(line[6:])
                        token = data.get("content", "")
                        if token:
                            yield token
                    except Exception:
                        pass

    async def chat_completion(self, messages: list[dict], max_tokens: int = 2048) -> str:
        """OpenAI-compat chat endpoint."""
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.settings.llm_temperature,
            "top_p": 0.95
        }

        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self.client.aclose()
