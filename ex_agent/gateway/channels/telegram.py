"""
Telegram Messaging Bridge for EX Agent Gateway.
Connects Telegram chat threads directly to persistent EXAgent sessions.
"""
from __future__ import annotations

import logging
from typing import Optional
from ex_agent.agent.core import EXAgent
from ex_agent.config import load_config

logger = logging.getLogger("ex_agent.gateway.telegram")


class TelegramBridge:
    def __init__(self, bot_token: Optional[str] = None):
        self.cfg = load_config()
        self.bot_token = bot_token or self.cfg.channels.get("telegram", {}).token

    async def start_polling(self) -> None:
        if not self.bot_token:
            logger.warning("[Telegram] Bot token not configured. Skipping.")
            return

        try:
            from telegram import Update
            from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

            async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if not update.effective_message or not update.effective_message.text:
                    return

                user_text = update.effective_message.text
                chat_id = str(update.effective_chat.id)
                session_id = f"telegram_{chat_id}"

                agent = EXAgent(config=self.cfg, session_id=session_id)
                await update.effective_chat.send_action("typing")

                res = await agent.run_conversation_async(user_message=user_text)
                await update.effective_message.reply_text(res.get("response", ""))

            app = ApplicationBuilder().token(self.bot_token).build()
            app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
            logger.info("[Telegram] Starting bot polling loop...")
            await app.run_polling()
        except ImportError:
            logger.error("[Telegram] python-telegram-bot is required for Telegram bridge.")
        except Exception as e:
            logger.error(f"[Telegram] Error: {e}")
