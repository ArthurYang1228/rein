"""Anthropic LLMProvider 實作(adapter)。"""

from core.interfaces.llm_provider import LLMProvider


class AnthropicProvider(LLMProvider):
    """LLMProvider 介面的 Anthropic SDK 實作。"""
