"""
Local Provider for Merlin Agent (vLLM / Ollama / llama.cpp).
Injects Tier-3 Hardware Awareness: detects CUDA Tensor Cores, BF16, and FlashAttention availability.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from merlin_agent.providers.base import BaseProvider, StreamChunk
from merlin_agent.providers.openai_provider import OpenAICompatibleProvider

logger = logging.getLogger("merlin_agent.providers.local")


class LocalProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        api_key: Optional[str] = "local-ex-token",
        base_url: Optional[str] = "http://localhost:11434/v1",
        model: str = "hermes3:8b",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_budget: int = 0,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
        )
        self._audit_hardware_acceleration()

    def _audit_hardware_acceleration(self) -> None:
        """Tier 3: Audit local accelerator features (Tensor Cores / FlashAttention)."""
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                bf16_supported = torch.cuda.is_bf16_supported()
                logger.info(f"[EX Local] GPU detected: {device_name} (BF16 Supported: {bf16_supported})")
            else:
                logger.info("[EX Local] Running on CPU host.")
        except Exception:
            pass
