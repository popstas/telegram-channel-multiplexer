from pathlib import Path

import pytest

from telegram_channel_multiplexer.config import ConfigManager, TargetChat


def test_config_manager_initializes_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yml"
    manager = ConfigManager(config_path)

    assert config_path.exists()
    assert manager.config.target_chats == []
    assert manager.config.admin_usernames == []
    assert manager.config.source_chats == []
    assert manager.config.bot_token == ""


def test_add_target_chat_persists(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yml"
    manager = ConfigManager(config_path)

    added = manager.add_target_chat(-100111, thread_id=55)
    assert added is True
    assert manager.config.target_chats == [TargetChat(chat_id=-100111, thread_id=55)]

    # Ensure persistence
    reloaded = ConfigManager(config_path)
    assert reloaded.config.target_chats == [TargetChat(chat_id=-100111, thread_id=55)]


def test_add_target_chat_is_idempotent(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yml"
    manager = ConfigManager(config_path)
    manager.add_target_chat(-1)
    added = manager.add_target_chat(-1)
    assert added is False
    assert manager.config.target_chats == [TargetChat(chat_id=-1, thread_id=None)]


def test_update_delay_and_admins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yml"
    manager = ConfigManager(config_path)

    manager.update_delay(2.5)
    manager.set_admin_usernames(["Admin", "second"])
    manager.set_source_chats([-1, "-2"])
    manager.set_bot_token("abc123")

    reloaded = ConfigManager(config_path)
    assert reloaded.config.delay_seconds == 2.5
    assert reloaded.config.admin_usernames == ["Admin", "second"]
    assert reloaded.config.source_chats == [-1, -2]
    assert reloaded.config.bot_token == "abc123"
