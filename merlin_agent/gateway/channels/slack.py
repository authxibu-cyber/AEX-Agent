"""
Slack Messaging Bridge for Merlin Agent Gateway.
"""
from __future__ import annotations

import logging
from typing import Optional
from merlin_agent.agent.core import MerlinAgent
from merlin_agent.config import load_config

logger = logging.getLogger("merlin_agent.gateway.slack")


class SlackBridge:
    def __init__(self, bot_token: Optional[str] = None):
        self.cfg = load_config()
        self.bot_token = bot_token or self.cfg.channels.get("slack", {}).token

    async def start(self) -> None:
        if not self.bot_token:
            logger.warning("[Slack] Bot token not provided. Skipping.")
            return
        logger.info("[Slack] Initializing Slack gateway client...")
