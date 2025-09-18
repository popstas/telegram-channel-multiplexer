"""Entry point for the Telegram Channel Multiplexer bot."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from .config import ConfigManager
from .forwarder import Forwarder

CONFIG_PATH = Path(os.environ.get("TCM_CONFIG", "config.yml"))
TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _resolve_token(config_manager: ConfigManager) -> str:
    token = os.environ.get(TOKEN_ENV_VAR) or config_manager.config.bot_token
    if not token:
        raise RuntimeError(
            "Bot token missing. Provide it in the configuration file under 'bot_token' "
            f"or via the {TOKEN_ENV_VAR} environment variable."
        )
    return token


def register_handlers(router: Dispatcher, config_manager: ConfigManager, forwarder: Forwarder) -> None:
    @router.message(Command("activate"))
    @router.channel_post(Command("activate"))
    async def activate_handler(message: Message, bot: Bot) -> None:
        username: Optional[str] = message.from_user.username if message.from_user else None
        allowed = {name.lower() for name in config_manager.config.admin_usernames}
        if not username or username.lower() not in allowed:
            await message.answer("You do not have permission to activate forwarding in this chat.")
            return
        chat_id = message.chat.id
        thread_id = getattr(message, "message_thread_id", None)
        added = config_manager.add_target_chat(chat_id, thread_id)
        if added:
            await message.answer("Channel registered for forwarding.")
        else:
            await message.answer("Channel already registered.")

    @router.channel_post()
    async def channel_post_handler(message: Message, bot: Bot) -> None:
        if message.chat.id not in config_manager.config.source_chats:
            return
        await forwarder.forward(bot, message, config_manager.config.target_chats)

    @router.message(F.chat.type.in_({"group", "supergroup"}))
    async def group_message_handler(message: Message, bot: Bot) -> None:
        if message.chat.id not in config_manager.config.source_chats:
            return
        await forwarder.forward(bot, message, config_manager.config.target_chats)


def create_dispatcher(config_manager: ConfigManager, forwarder: Forwarder | None = None) -> Dispatcher:
    dispatcher = Dispatcher()
    forwarder = forwarder or Forwarder(delay_seconds=config_manager.config.delay_seconds)
    register_handlers(dispatcher, config_manager, forwarder)
    return dispatcher


async def run_async() -> None:
    config_manager = ConfigManager(CONFIG_PATH)
    token = _resolve_token(config_manager)
    bot = Bot(token=token, parse_mode=ParseMode.HTML)
    dispatcher = create_dispatcher(config_manager)

    logger.info(
        "Starting bot. Forwarding to %d target chats with delay %.2fs.",
        len(config_manager.config.target_chats),
        config_manager.config.delay_seconds,
    )

    await dispatcher.start_polling(bot)


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    run()
