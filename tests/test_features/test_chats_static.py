"""
tests/test_features/test_chats_static.py

Тесты: classify_entity — классификация Telethon-сущностей.
"""
import pytest
from features.chats.api import classify_entity
from telethon.tl.types import User, Chat, Channel


class TestClassifyEntity:
    def test_user_is_private(self):
        assert classify_entity(User(id=1)) == "private"

    def test_user_with_name(self):
        u = User(id=42, first_name="Alice")
        assert classify_entity(u) == "private"

    def test_chat_is_group(self):
        from unittest.mock import MagicMock
        assert classify_entity(
            Chat(id=1, title="g", photo=MagicMock(), participants_count=0, date=None, version=0)
        ) == "group"

    def test_chat_with_title(self):
        from unittest.mock import MagicMock
        g = Chat(id=100, title="Моя группа", photo=MagicMock(), participants_count=0, date=None, version=0)
        assert classify_entity(g) == "group"

    def test_broadcast_is_channel(self):
        from unittest.mock import MagicMock
        ch = Channel(id=1, title="c", photo=MagicMock(), date=None)
        ch.broadcast = True
        assert classify_entity(ch) == "channel"

    def test_forum_is_forum(self):
        from unittest.mock import MagicMock
        ch = Channel(id=1, title="f", photo=MagicMock(), date=None)
        ch.broadcast = False
        ch.megagroup = True
        ch.forum = True
        assert classify_entity(ch) == "forum"

    def test_megagroup_no_forum_is_group(self):
        from unittest.mock import MagicMock
        ch = Channel(id=1, title="g", photo=MagicMock(), date=None)
        ch.broadcast = False
        ch.megagroup = True
        ch.forum = False
        assert classify_entity(ch) == "group"

    def test_channel_no_flags_is_channel(self):
        from unittest.mock import MagicMock
        ch = Channel(id=1, title="x", photo=MagicMock(), date=None)
        ch.broadcast = False
        ch.megagroup = False
        ch.forum = False
        assert classify_entity(ch) == "channel"

    def test_unknown_object(self):
        assert classify_entity("not a telethon object") == "unknown"

    def test_unknown_type_int(self):
        assert classify_entity(12345) == "unknown"

    def test_none(self):
        assert classify_entity(None) == "unknown"
