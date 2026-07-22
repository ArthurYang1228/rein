"""Gemini LLMProvider 實作(adapter)。"""

from core.interfaces.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    """LLMProvider 介面的 Gemini SDK 實作。"""
