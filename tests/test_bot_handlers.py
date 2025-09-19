from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from telegram_channel_multiplexer.bot import create_dispatcher
from telegram_channel_multiplexer.config import ConfigManager, SourceChat, TargetChat
from telegram_channel_multiplexer.forwarder import Forwarder


class DummyMessage:
    def __init__(
        self,
        chat_id: int,
        user_id: int | None,
        chat_type: str = "channel",
        username: str | None = None,
        message_thread_id: int | None = None,
        chat_title: str | None = None,
    ) -> None:
        self.chat = SimpleNamespace(id=chat_id, type=chat_type, title=chat_title)
        if user_id is not None:
            self.from_user = SimpleNamespace(id=user_id, username=username)
        else:
            self.from_user = None
        self.message_id = 1
        self.message_thread_id = message_thread_id
        self._responses: list[str] = []

    async def answer(self, text: str) -> None:
        self._responses.append(text)

    @property
    def responses(self) -> list[str]:
        return self._responses


class StubForwarder(Forwarder):
    def __init__(self) -> None:
        super().__init__(delay_seconds=0)
        self.calls: list[tuple[int, list[TargetChat]]] = []

    async def forward(self, bot, message, target_chats):  # type: ignore[override]
        self.calls.append((message.chat.id, list(target_chats)))


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        """
bot_token: test-token
target_chats: []
source_chats:
  - chat_id: -100
    title: Source
admin_usernames: [admin]
delay_seconds: 0.5
""".strip()
    )
    return ConfigManager(config_path)


@pytest.mark.asyncio
async def test_activate_command_adds_channel(config_manager: ConfigManager) -> None:
    forwarder = StubForwarder()
    dispatcher = create_dispatcher(config_manager, forwarder)
    activate_handler = next(h for h in dispatcher.message.handlers if h.callback.__name__ == "activate_handler")

    assert config_manager.config.source_chats == [SourceChat(chat_id=-100, title="Source")]

    message = DummyMessage(chat_id=-200, user_id=1, chat_type="channel", username="admin")
    bot = AsyncMock()

    await activate_handler.callback(message=message, bot=bot)

    assert config_manager.config.target_chats == [TargetChat(chat_id=-200, thread_id=None, title="")]
    assert message.responses == ["Channel registered for forwarding."]


@pytest.mark.asyncio
async def test_activate_command_rejects_non_admin(config_manager: ConfigManager) -> None:
    forwarder = StubForwarder()
    dispatcher = create_dispatcher(config_manager, forwarder)
    activate_handler = next(h for h in dispatcher.message.handlers if h.callback.__name__ == "activate_handler")

    message = DummyMessage(chat_id=-200, user_id=999, chat_type="channel", username="other")
    bot = AsyncMock()

    await activate_handler.callback(message=message, bot=bot)

    assert config_manager.config.target_chats == []
    assert message.responses == ["You do not have permission to activate forwarding in this chat."]


@pytest.mark.asyncio
async def test_channel_post_triggers_forward(config_manager: ConfigManager) -> None:
    config_manager.add_target_chat(-300, title="Target")
    forwarder = StubForwarder()
    dispatcher = create_dispatcher(config_manager, forwarder)
    channel_handler = next(h for h in dispatcher.channel_post.handlers if h.callback.__name__ == "channel_post_handler")

    message = DummyMessage(chat_id=-100, user_id=None, chat_type="channel")
    bot = AsyncMock()

    await channel_handler.callback(message=message, bot=bot)

    assert forwarder.calls[0][0] == -100
    forwarded = forwarder.calls[0][1]
    assert [chat.chat_id for chat in forwarded] == [-300]


@pytest.mark.asyncio
async def test_group_message_triggers_forward(config_manager: ConfigManager) -> None:
    config_manager.add_target_chat(-300, title="Target")
    forwarder = StubForwarder()
    dispatcher = create_dispatcher(config_manager, forwarder)
    group_handler = next(h for h in dispatcher.message.handlers if h.callback.__name__ == "group_message_handler")

    message = DummyMessage(chat_id=-100, user_id=5, chat_type="group", username="admin")
    bot = AsyncMock()

    await group_handler.callback(message=message, bot=bot)

    assert forwarder.calls[0][0] == -100
    forwarded = forwarder.calls[0][1]
    assert [chat.chat_id for chat in forwarded] == [-300]
