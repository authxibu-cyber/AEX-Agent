"""
Merlin Agent Model Providers Subsystem.
Unified streaming interface for Nous Portal, OpenRouter, OpenAI, Anthropic, Gemini, and Local (vLLM/Ollama).
"""
from merlin_agent.providers.base import BaseProvider, StreamChunk
from merlin_agent.providers.openai_provider import OpenAICompatibleProvider
from merlin_agent.providers.anthropic_provider import AnthropicProvider
from merlin_agent.providers.local_provider import LocalProvider

__all__ = [
    "BaseProvider",
    "StreamChunk",
    "OpenAICompatibleProvider",
    "AnthropicProvider",
    "LocalProvider",
]
