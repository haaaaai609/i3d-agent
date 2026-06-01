"""LLM client for interacting with Anthropic and OpenAI APIs."""

import os
import json
from dataclasses import dataclass
from typing import List, Optional, Union, Literal, AsyncIterator

import httpx

from i3d_agent.config.settings import get_settings
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    """Chat message for LLM interactions."""
    role: Literal["user", "assistant", "system"]
    content: str


class LLMClient:
    """Unified LLM client supporting Anthropic, OpenAI, and DashScope APIs."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """Initialize LLM client.

        Args:
            provider: LLM provider ("anthropic", "openai", or "dashscope")
            api_key: API key for the provider
            model: Model identifier
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        settings = get_settings()

        self.provider = provider or settings.DEFAULT_LLM_PROVIDER

        # Get API key based on provider
        if api_key:
            self.api_key = api_key
        elif self.provider == "anthropic":
            self.api_key = settings.ANTHROPIC_API_KEY
        elif self.provider == "dashscope":
            self.api_key = settings.DASHSCOPE_API_KEY
        else:  # openai
            self.api_key = settings.OPENAI_API_KEY

        self.model = model or settings.DEFAULT_LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self.timeout = timeout

        if not self.api_key:
            logger.warning(f"No API key configured for {self.provider}")

        # Configure endpoints
        if self.provider == "anthropic":
            self.base_url = base_url or "https://api.anthropic.com"
            self.headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        elif self.provider == "dashscope":
            self.base_url = base_url or settings.DASHSCOPE_BASE_URL
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            }
        else:  # openai
            self.base_url = base_url or "https://api.openai.com/v1"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            }

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """Generate text response from LLM.

        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt (for Anthropic)
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Whether to stream responses (not yet implemented)

        Returns:
            Generated text response
        """
        if not self.api_key:
            return "抱歉，LLM 服务未配置 API Key。"

        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.provider == "anthropic":
                    return await self._anthropic_generate(
                        client, messages, system_prompt, temp, tokens
                    )
                else:
                    return await self._openai_generate(
                        client, messages, system_prompt, temp, tokens
                    )
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return f"LLM 调用失败: {str(e)}"

    async def _anthropic_generate(
        self,
        client: httpx.AsyncClient,
        messages: List[Message],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate using Anthropic API."""
        # Separate user messages for Anthropic format
        user_messages = []
        for msg in messages:
            if msg.role == "user":
                user_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                user_messages.append({"role": "assistant", "content": msg.content})

        payload = {
            "model": self.model,
            "messages": user_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = await client.post(
            f"{self.base_url}/v1/messages",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("content", [{}])[0].get("text", "")

    async def _openai_generate(
        self,
        client: httpx.AsyncClient,
        messages: List[Message],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate using OpenAI API (and compatible APIs like DashScope)."""
        # Convert messages to OpenAI format
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
        }

        # DashScope doesn't support max_tokens in the same way
        # Only add it if not using DashScope
        if self.provider != "dashscope":
            payload["max_tokens"] = max_tokens

        logger.debug(f"LLM Request: {self.provider} -> {self.base_url}/chat/completions")
        logger.debug(f"Payload model: {self.model}")

        response = await client.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
        )

        # Log error details for debugging
        if not response.is_success:
            logger.error(f"LLM API error response: {response.text}")

        response.raise_for_status()

        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def _openai_generate_stream(
        self,
        client: httpx.AsyncClient,
        messages: List[Message],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Generate using OpenAI API with streaming support."""
        # Convert messages to OpenAI format
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "stream": True,  # Enable streaming
        }

        logger.debug(f"LLM Stream Request: {self.provider} -> {self.base_url}/chat/completions")

        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
        ) as response:
            if not response.is_success:
                error_text = await response.aread()
                logger.error(f"LLM Stream API error: {error_text}")
                raise Exception(f"LLM Stream error: {error_text}")

            # Parse SSE-style response
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix

                # Skip [DONE] marker
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    # Extract content from streaming response
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse stream chunk: {data_str}, error: {e}")
                    continue

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Generate streaming text response from LLM.

        Args:
            messages: List of chat messages
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Yields:
            Content chunks as they arrive from LLM
        """
        if not self.api_key:
            yield "抱歉，LLM 服务未配置 API Key。"
            return

        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # For now, only OpenAI-compatible APIs (DashScope) support streaming
                if self.provider in ["openai", "dashscope"]:
                    async for chunk in self._openai_generate_stream(
                        client, messages, system_prompt, temp, tokens
                    ):
                        yield chunk
                else:
                    # Fallback to non-streaming for Anthropic
                    result = await self._anthropic_generate(
                        client, messages, system_prompt, temp, tokens
                    )
                    yield result
        except Exception as e:
            logger.error(f"LLM Stream API error: {e}")
            yield f"LLM 调用失败: {str(e)}"


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        settings = get_settings()
        if settings.DASHSCOPE_API_KEY:
            _llm_client = LLMClient(provider="dashscope")
        elif settings.ANTHROPIC_API_KEY:
            _llm_client = LLMClient(provider="anthropic")
        elif settings.OPENAI_API_KEY:
            _llm_client = LLMClient(provider="openai")
        else:
            _llm_client = LLMClient()  # Will return "no API key" message
    return _llm_client


def set_llm_client(client: LLMClient) -> None:
    """Set global LLM client instance (useful for testing)."""
    global _llm_client
    _llm_client = client


async def simple_generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Simple wrapper for single-prompt generation.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        temperature: Temperature for generation

    Returns:
        Generated response
    """
    client = get_llm_client()
    messages = [Message(role="user", content=prompt)]
    return await client.generate(messages, system_prompt, temperature)
