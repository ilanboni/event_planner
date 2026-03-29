from __future__ import annotations

import base64
from pathlib import Path

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from config import settings
from utils.logger import logger

# MIME types supported by both vision APIs
_VISION_MIME_MAP: dict[str, str] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

# Anthropic requires an explicit max_tokens value
_MAX_TOKENS = 4096


class BaseAgent:
    """
    Shared foundation for all agents.

    Provides two LLM call modes:
      _call_llm        — standard text completion, optionally JSON-mode
      _call_llm_vision — multimodal call with a local image

    The active provider is selected at init time from settings.LLM_PROVIDER:
      "anthropic" (default) — uses AsyncAnthropic
      "openai"              — uses AsyncOpenAI

    All agent subclasses call _call_llm / _call_llm_vision unchanged.
    Provider routing is fully contained in this base class.

    Note: json_mode=True is OpenAI-specific (response_format=json_object).
    With Anthropic, the prompt itself enforces JSON structure — the flag is
    accepted but has no effect on the API call. All agent prompts already
    instruct the model to return only a JSON object, so output is consistent
    across providers.
    """

    def __init__(self) -> None:
        self._provider = settings.LLM_PROVIDER.lower()

        if self._provider == "anthropic":
            self._anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self._model = settings.ANTHROPIC_MODEL
        else:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self._model = settings.OPENAI_MODEL

    # ── Public interface (unchanged for all subclasses) ───────────────────────

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> str:
        if self._provider == "anthropic":
            return await self._anthropic_call(system_prompt, user_message, temperature)
        return await self._openai_call(system_prompt, user_message, json_mode, temperature)

    async def _call_llm_vision(
        self,
        system_prompt: str,
        user_message: str,
        image_path: str,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        if self._provider == "anthropic":
            return await self._anthropic_vision_call(system_prompt, user_message, image_path, temperature)
        return await self._openai_vision_call(system_prompt, user_message, image_path, json_mode, temperature)

    # ── Anthropic ─────────────────────────────────────────────────────────────

    async def _anthropic_call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
    ) -> str:
        response = await self._anthropic.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        content = response.content[0].text
        logger.debug("%s raw response: %s…", self.__class__.__name__, content[:120])
        return _strip_code_fences(content)

    async def _anthropic_vision_call(
        self,
        system_prompt: str,
        user_message: str,
        image_path: str,
        temperature: float,
    ) -> str:
        ext = Path(image_path).suffix.lower()
        mime = _VISION_MIME_MAP.get(ext, "image/jpeg")

        with open(image_path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("utf-8")

        response = await self._anthropic.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            temperature=temperature,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": encoded,
                        },
                    },
                    {"type": "text", "text": user_message},
                ],
            }],
        )
        content = response.content[0].text
        logger.debug("%s vision response: %s…", self.__class__.__name__, content[:120])
        return _strip_code_fences(content)

    # ── OpenAI ────────────────────────────────────────────────────────────────

    async def _openai_call(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool,
        temperature: float,
    ) -> str:
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

        response = await self._openai.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("%s raw response: %s…", self.__class__.__name__, content[:120])
        return content

    async def _openai_vision_call(
        self,
        system_prompt: str,
        user_message: str,
        image_path: str,
        json_mode: bool,
        temperature: float,
    ) -> str:
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

        response = await self._openai.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences that some models wrap around JSON responses.
    Handles ```json ... ```, ``` ... ```, and leading/trailing whitespace.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        # Remove closing fence
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()
