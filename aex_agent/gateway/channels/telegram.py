"""
Telegram Messaging Bridge for AEX Agent Gateway.
Connects Telegram chat threads directly to persistent EXAgent sessions.

Security model (fail-closed):
- Only chat IDs listed in config channels.telegram.allowed_ids may talk to
  the agent. An empty allowlist blocks EVERYONE until explicitly configured -
  an open bot is a remote-command surface for whoever finds the handle.
- Unlisted senders get no agent session, no tool access, nothing.
- /id echoes the chat ID so the owner can discover the value to allowlist.
"""
from __future__ import annotations

import logging
from typing import Optional

from aex_agent.agent.core import EXAgent
from aex_agent.config import load_config

logger = logging.getLogger("aex_agent.gateway.telegram")


class TelegramBridge:
    def __init__(self, bot_token: Optional[str] = None):
        self.cfg = load_config()
        tch = self.cfg.channels.get("telegram")
        self.bot_token = bot_token or (tch.token if tch is not None else None)
        self.allowed_ids = {
            str(x).strip()
            for x in (getattr(tch, "allowed_ids", None) or [])
            if str(x).strip()
        }

    async def start_polling(self) -> None:
        if not self.bot_token:
            logger.warning("[Telegram] Bot token not configured. Skipping.")
            return

        if not self.allowed_ids:
            logger.error(
                "[Telegram] REJECTED STARTUP: channels.telegram.allowed_ids is empty. "
                "An open Telegram bot is a remote-command surface. Add your chat ID(s) "
                "to config.yaml (channels.telegram.allowed_ids: ['<chat_id>']) or set "
                "TELEGRAM_ALLOWED_CHAT_IDS, then restart."
            )
            return

        try:
            from telegram import Update
            from telegram.ext import (
                ApplicationBuilder,
                CommandHandler,
                ContextTypes,
                MessageHandler,
                filters,
            )

            async def _is_allowed(update: Update) -> bool:
                cid = str(update.effective_chat.id) if update.effective_chat else ""
                return cid in self.allowed_ids

            async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if update.effective_message is None:
                    return
                cid = str(update.effective_chat.id) if update.effective_chat else "unknown"
                await update.effective_message.reply_text(f"chat_id: {cid}")

            async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if not update.effective_message or not update.effective_message.text:
                    return
                if not await _is_allowed(update):
                    logger.warning(
                        "[Telegram] DENIED chat_id=%s - not in allowed_ids. Silent drop."
                        % (str(update.effective_chat.id) if update.effective_chat else "?")
                    )
                    return

                user_text = update.effective_message.text
                chat_id = str(update.effective_chat.id)
                session_id = f"telegram_{chat_id}"

                agent = EXAgent(config=self.cfg, session_id=session_id)
                await update.effective_chat.send_action("typing")

                res = await agent.run_conversation_async(user_message=user_text)
                await update.effective_message.reply_text(res.get("response", ""))

            app = ApplicationBuilder().token(self.bot_token).build()
            app.add_handler(CommandHandler("id", handle_id))
            app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
            logger.info(
                "[Telegram] Starting bot polling loop with allowlist enforcement "
                "(%d allowed id(s))." % len(self.allowed_ids)
            )
            await app.run_polling()
        except ImportError:
            logger.error("[Telegram] python-telegram-bot is required for Telegram bridge.")
        except Exception as e:
            logger.error(f"[Telegram] Error: {e}")