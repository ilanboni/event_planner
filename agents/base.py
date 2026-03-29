from __future__ import annotations

import base64
from pathlib import Path

from openai import AsyncOpenAI

from config import settings
from utils.logger import logger

# MIME types supported by the vision API
_VISION_MIME_MAP: dict[str, str] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}


class BaseAgent:
    """
    Shared foundation for all agents.

    Provides two LLM call modes:
      _call_llm        — standard text completion, optionally JSON-mode
      _call_llm_vision — multimodal call with a local image or PDF page
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> str:
        """
        Single-turn chat completion.

        json_mode=True forces the model to return valid JSON (uses
        response_format={"type": "json_object"}).  The system or user
        prompt must mention JSON for this to work correctly.
        """
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("%s raw response: %s…", self.__class__.__name__, content[:120])
        return content

    async def _call_llm_vision(
        self,
        system_prompt: str,
        user_message: str,
        image_path: str,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        """
        Multimodal call that attaches a local image as a base64 data URL.
        Used by the Archivist for images, logos, floor plans, and scanned PDFs.
        """
        ext = Path(image_path).suffix.lower()
        mime = _VISION_MIME_MAP.get(ext, "image/jpeg")

        with open(image_path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("utf-8")

        data_url = f"data:{mime};base64,{encoded}"

        content: list[dict] = [
            {"type": "text", "text": user_message},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
        ]

        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": content},
            ],
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
