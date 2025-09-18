import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from telegram_channel_multiplexer.config import TargetChat
from telegram_channel_multiplexer.forwarder import Forwarder


class DummyMessage(SimpleNamespace):
    pass


@pytest.mark.asyncio
async def test_forwarder_skips_source_channel(monkeypatch):
    bot = AsyncMock()
    message = DummyMessage(chat=SimpleNamespace(id=-100), message_id=42)
    forwarder = Forwarder(delay_seconds=0.1)

    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    targets = [TargetChat(chat_id=-100), TargetChat(chat_id=-200)]
    await forwarder.forward(bot, message, targets)

    bot.copy_message.assert_called_once_with(chat_id=-200, from_chat_id=-100, message_id=42)
    assert sleep_calls == [0.1]


@pytest.mark.asyncio
async def test_forwarder_handles_retry_after(monkeypatch):
    bot = AsyncMock()
    message = DummyMessage(chat=SimpleNamespace(id=-100), message_id=43)
    forwarder = Forwarder(delay_seconds=0)

    class Retry(Exception):
        def __init__(self, retry_after):
            self.retry_after = retry_after

    # configure bot to raise once then succeed
    bot.copy_message = AsyncMock(side_effect=[Retry(1), None])

    waits = []

    async def fake_sleep(delay):
        waits.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr("telegram_channel_multiplexer.forwarder.TelegramRetryAfter", Retry)

    await forwarder._forward_single(bot, message, TargetChat(chat_id=-200))

    assert waits == [2]  # retry_after + 1
    assert bot.copy_message.await_count == 2


@pytest.mark.asyncio
async def test_forwarder_excludes_specific_ids(monkeypatch):
    bot = AsyncMock()
    message = DummyMessage(chat=SimpleNamespace(id=-100), message_id=99)
    forwarder = Forwarder(delay_seconds=0, excluded_chat_ids={-300})

    targets = [TargetChat(chat_id=-200), TargetChat(chat_id=-300), TargetChat(chat_id=-400, thread_id=77)]
    await forwarder.forward(bot, message, targets)

    calls = [call.kwargs for call in bot.copy_message.await_args_list]
    assert calls == [
        {"chat_id": -200, "from_chat_id": -100, "message_id": 99},
        {"chat_id": -400, "from_chat_id": -100, "message_id": 99, "message_thread_id": 77},
    ]
