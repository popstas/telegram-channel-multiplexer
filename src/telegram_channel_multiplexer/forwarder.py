"""Message forwarding utilities."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Sequence

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message

from .config import TargetChat


logger = logging.getLogger(__name__)


class Forwarder:
    """Forward messages to a list of target channels with rate limiting."""

    def __init__(self, delay_seconds: float, excluded_chat_ids: Iterable[int] | None = None) -> None:
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.excluded_chat_ids = set(excluded_chat_ids or [])

    async def forward(self, bot: Bot, message: Message, target_chats: Sequence[TargetChat]) -> None:
        source_chat_id = message.chat.id
        for target in target_chats:
            chat_id = target.chat_id
            if chat_id == source_chat_id or chat_id in self.excluded_chat_ids:
                continue
            await self._forward_single(bot, message, target)
            if self.delay_seconds > 0:
                await asyncio.sleep(self.delay_seconds)

    async def _forward_single(self, bot: Bot, message: Message, target: TargetChat) -> None:
        target_chat_id = target.chat_id
        try:
            copy_kwargs = {
                "chat_id": target_chat_id,
                "from_chat_id": message.chat.id,
                "message_id": message.message_id,
            }
            if target.thread_id is not None:
                copy_kwargs["message_thread_id"] = target.thread_id
            await bot.copy_message(**copy_kwargs)
        except TelegramRetryAfter as exc:
            wait_time = exc.retry_after + 1
            logger.warning("Rate limited while forwarding to %s. Sleeping for %ss.", target_chat_id, wait_time)
            await asyncio.sleep(wait_time)
            await self._forward_single(bot, message, target)
        except TelegramForbiddenError:
            logger.error("Lost access to target channel %s. Consider removing it from configuration.", target_chat_id)
        except TelegramAPIError as exc:
            logger.exception("Failed to forward message %s to %s: %s", message.message_id, target_chat_id, exc)


__all__ = ["Forwarder"]
