"""Configuration utilities for the Telegram channel multiplexer bot."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

import yaml


DEFAULT_DELAY_SECONDS = 1.0


@dataclass(eq=True)
class TargetChat:
    """Represents a forwarding destination."""

    chat_id: int
    thread_id: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TargetChat":
        chat_id = int(data.get("chat_id"))
        thread_id = data.get("thread_id")
        if thread_id is not None:
            thread_id = int(thread_id)
        return cls(chat_id=chat_id, thread_id=thread_id)

    def to_dict(self) -> dict:
        result = {"chat_id": self.chat_id}
        if self.thread_id is not None:
            result["thread_id"] = self.thread_id
        return result


@dataclass
class BotConfig:
    """Container for bot configuration settings."""

    bot_token: str = ""
    target_chats: List[TargetChat] = field(default_factory=list)
    source_chats: List[int] = field(default_factory=list)
    admin_usernames: List[str] = field(default_factory=list)
    delay_seconds: float = DEFAULT_DELAY_SECONDS

    @classmethod
    def from_dict(cls, data: dict) -> "BotConfig":
        target_chats_raw = data.get("target_chats", [])
        target_chats = [TargetChat.from_dict(item) for item in target_chats_raw]
        source_chats = [int(item) for item in data.get("source_chats", [])]
        admin_usernames = [str(item) for item in data.get("admin_usernames", [])]
        delay = float(data.get("delay_seconds", DEFAULT_DELAY_SECONDS))
        bot_token = str(data.get("bot_token", ""))
        return cls(
            bot_token=bot_token,
            target_chats=target_chats,
            source_chats=source_chats,
            admin_usernames=admin_usernames,
            delay_seconds=delay,
        )

    def to_dict(self) -> dict:
        return {
            "bot_token": self.bot_token,
            "target_chats": [chat.to_dict() for chat in self.target_chats],
            "source_chats": self.source_chats,
            "admin_usernames": self.admin_usernames,
            "delay_seconds": self.delay_seconds,
        }


class ConfigManager:
    """Manages reading and writing bot configuration."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._config = self._load_from_disk()

    @property
    def config(self) -> BotConfig:
        return self._config

    def _load_from_disk(self) -> BotConfig:
        if not self._path.exists():
            # initialize with default structure
            default_config = BotConfig()
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._write_to_disk(default_config)
            return default_config

        with self._path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return BotConfig.from_dict(raw)

    def _write_to_disk(self, config: BotConfig) -> None:
        with self._path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(config.to_dict(), fh, sort_keys=False)

    def reload(self) -> BotConfig:
        with self._lock:
            self._config = self._load_from_disk()
            return self._config

    def add_target_chat(self, chat_id: int, thread_id: int | None = None) -> bool:
        """Add a chat to the target list. Returns True if added."""

        with self._lock:
            target = TargetChat(chat_id=int(chat_id), thread_id=int(thread_id) if thread_id is not None else None)
            if target in self._config.target_chats:
                return False
            self._config.target_chats.append(target)
            self._write_to_disk(self._config)
            return True

    def remove_target_chat(self, chat_id: int, thread_id: int | None = None) -> bool:
        with self._lock:
            target = TargetChat(chat_id=int(chat_id), thread_id=int(thread_id) if thread_id is not None else None)
            try:
                self._config.target_chats.remove(target)
            except ValueError:
                return False
            self._write_to_disk(self._config)
            return True

    def update_delay(self, delay_seconds: float) -> None:
        with self._lock:
            self._config.delay_seconds = float(delay_seconds)
            self._write_to_disk(self._config)

    def set_admin_usernames(self, usernames: Iterable[str]) -> None:
        with self._lock:
            self._config.admin_usernames = [str(user) for user in usernames]
            self._write_to_disk(self._config)

    def set_source_chats(self, chat_ids: Sequence[int]) -> None:
        with self._lock:
            self._config.source_chats = [int(chat_id) for chat_id in chat_ids]
            self._write_to_disk(self._config)

    def set_bot_token(self, token: str) -> None:
        with self._lock:
            self._config.bot_token = str(token)
            self._write_to_disk(self._config)


__all__ = ["BotConfig", "ConfigManager", "TargetChat", "DEFAULT_DELAY_SECONDS"]
