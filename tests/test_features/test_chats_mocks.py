"""
tests/test_features/test_chats_mocks.py

Тесты: ChatsService — get_dialogs, get_topics, get_linked_group, get_user_stats с моками.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from telethon.tl.types import Channel, Chat, User, ChatPhotoEmpty

from features.chats.api import ChatsService
from core.exceptions import ChatNotFoundError, TelegramError


def _channel(i, title=None, broadcast=True, forum=False):
    return Channel(
        id=i, title=title or f"Channel{i}",
        photo=ChatPhotoEmpty(), date=datetime.now(timezone.utc),
        broadcast=broadcast, megagroup=not broadcast, forum=forum,
    )


def _make_channel_dialog(i, broadcast=True, forum=False):
    dialog = MagicMock()
    dialog.entity = _channel(i, broadcast=broadcast, forum=forum)
    return dialog


def _chat(i, title=None):
    return Chat(
        id=i, title=title or f"Group{i}",
        photo=ChatPhotoEmpty(), participants_count=100,
        date=datetime.now(timezone.utc), version=1,
    )


def _make_group_dialog(i):
    dialog = MagicMock()
    dialog.entity = _chat(i)
    return dialog


def _make_user_dialog(i):
    dialog = MagicMock()
    dialog.entity = User(id=i, first_name=f"User{i}", last_name="", username=f"user{i}")
    return dialog


def _client_with_dialogs(dialogs):
    client = MagicMock()
    client.get_dialogs = AsyncMock(return_value=dialogs)
    return client


class TestGetDialogs:
    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        dialogs = [
            _make_channel_dialog(1),
            _make_group_dialog(2),
            _make_user_dialog(3),
        ]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(d, dict) for d in result)

    @pytest.mark.asyncio
    async def test_dict_has_required_keys(self):
        dialogs = [_make_channel_dialog(1)]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        d = result[0]
        for key in ("id", "raw_id", "title", "type", "username",
                     "participants_count", "has_comments", "linked_chat_id"):
            assert key in d

    @pytest.mark.asyncio
    async def test_sorted_by_type(self):
        dialogs = [
            _make_user_dialog(1),
            _make_group_dialog(2),
            _make_channel_dialog(3),
        ]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        types = [d["type"] for d in result]
        order = {"channel": 0, "forum": 1, "group": 2, "private": 3}
        indices = [order.get(t, 9) for t in types]
        assert indices == sorted(indices)

    @pytest.mark.asyncio
    async def test_limit_param(self):
        dialogs = [_make_channel_dialog(i) for i in range(10)]
        client = MagicMock()
        client.get_dialogs = AsyncMock(return_value=dialogs)
        svc = ChatsService(client)
        await svc.get_dialogs(limit=10)
        client.get_dialogs.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_network_error_raises(self):
        client = MagicMock()
        client.get_dialogs = AsyncMock(side_effect=Exception("timeout"))
        svc = ChatsService(client)
        with pytest.raises(TelegramError, match="диалогов"):
            await svc.get_dialogs()

    @pytest.mark.asyncio
    async def test_skips_unknown_entities(self):
        unknown = MagicMock()
        unknown.entity = "not_a_telethon_entity"
        dialogs = [_make_channel_dialog(1), unknown, _make_group_dialog(2)]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_private_chat_title_from_name(self):
        dialogs = [_make_user_dialog(42)]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        assert result[0]["title"] == "User42"

    @pytest.mark.asyncio
    async def test_channel_title_from_entity(self):
        dialogs = [_make_channel_dialog(1)]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        assert result[0]["title"] == "Channel1"

    @pytest.mark.asyncio
    async def test_forum_detected(self):
        dialogs = [_make_channel_dialog(1, broadcast=False, forum=True)]
        svc = ChatsService(_client_with_dialogs(dialogs))
        result = await svc.get_dialogs()
        assert result[0]["type"] == "forum"


class TestGetTopics:
    @pytest.mark.asyncio
    async def test_not_a_forum_returns_empty(self):
        entity = _channel(1, title="Test", broadcast=False)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.side_effect = AsyncMock(return_value=MagicMock(
            full_chat=MagicMock(), chats=[]
        ))
        svc = ChatsService(client)
        result = await svc.get_topics(-100)
        assert result == {}

    @pytest.mark.asyncio
    async def test_chat_not_found_raises(self):
        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        svc = ChatsService(client)
        with pytest.raises(ChatNotFoundError):
            await svc.get_topics(-100)

    @pytest.mark.asyncio
    async def test_forum_with_api_topics(self):
        entity = _channel(1, title="Forum", broadcast=False, forum=True)

        topic1 = MagicMock()
        topic1.id = 10
        topic1.title = "General"
        topic2 = MagicMock()
        topic2.id = 20
        topic2.title = "News"
        api_result = MagicMock()
        api_result.topics = [topic1, topic2]
        api_result.count = 2

        input_entity = MagicMock()
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.get_input_entity = AsyncMock(return_value=input_entity)
        client.side_effect = AsyncMock(return_value=api_result)

        svc = ChatsService(client)
        result = await svc.get_topics(-100)
        assert result == {10: "General", 20: "News"}

    @pytest.mark.asyncio
    async def test_forum_fallback_scan(self):
        entity = _channel(1, title="Forum", broadcast=False, forum=True)

        input_entity = MagicMock()
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.get_input_entity = AsyncMock(return_value=input_entity)
        client.side_effect = AsyncMock(side_effect=Exception("API error"))

        msg1 = MagicMock()
        msg1.id = 100
        msg1.action = MagicMock()
        msg1.action.title = "General"

        async def mock_iter(*a, **kw):
            yield msg1

        client.iter_messages = mock_iter

        svc = ChatsService(client)
        result = await svc.get_topics(-100)
        assert 100 in result
        assert result[100] == "General"


class TestGetLinkedGroup:
    @pytest.mark.asyncio
    async def test_non_channel_returns_none(self):
        entity = _chat(1)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        svc = ChatsService(client)
        result = await svc.get_linked_group(1)
        assert result is None

    @pytest.mark.asyncio
    async def test_channel_with_linked_group(self):
        entity = _channel(1, title="Ch", broadcast=True)
        full_result = MagicMock()
        full_result.full_chat = MagicMock(linked_chat_id=-200)
        full_result.chats = []

        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.side_effect = AsyncMock(return_value=full_result)

        svc = ChatsService(client)
        result = await svc.get_linked_group(-100)
        assert result == -200

    @pytest.mark.asyncio
    async def test_channel_without_linked_group(self):
        entity = _channel(1, title="Ch", broadcast=True)
        full_result = MagicMock()
        full_result.full_chat = MagicMock(linked_chat_id=None)
        full_result.chats = []

        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.side_effect = AsyncMock(return_value=full_result)

        svc = ChatsService(client)
        result = await svc.get_linked_group(-100)
        assert result is None

    @pytest.mark.asyncio
    async def test_chat_not_found_raises(self):
        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        svc = ChatsService(client)
        with pytest.raises(ChatNotFoundError):
            await svc.get_linked_group(-100)

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        entity = _channel(1, title="Ch", broadcast=True)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.side_effect = AsyncMock(side_effect=Exception("api fail"))

        svc = ChatsService(client)
        result = await svc.get_linked_group(-100)
        assert result is None


class TestGetUserStats:
    @pytest.mark.asyncio
    async def test_returns_sorted_stats(self):
        entity = _channel(1, title="Test", broadcast=False)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)

        msgs = []
        for i in range(3):
            m = MagicMock()
            m.sender_id = 10
            m.sender = User(id=10, first_name="Alice")
            msgs.append(m)
        m = MagicMock()
        m.sender_id = 20
        m.sender = User(id=20, first_name="Bob")
        msgs.append(m)

        async def mock_iter(*a, **kw):
            for m in msgs:
                yield m

        client.iter_messages = mock_iter
        svc = ChatsService(client)
        result = await svc.get_user_stats(-100)
        assert len(result) == 2
        assert result[0]["message_count"] == 3
        assert result[0]["name"] == "Alice"
        assert result[1]["message_count"] == 1

    @pytest.mark.asyncio
    async def test_entity_not_found_returns_empty(self):
        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        svc = ChatsService(client)
        result = await svc.get_user_stats(-100)
        assert result == []

    @pytest.mark.asyncio
    async def test_limit_param(self):
        entity = _channel(1, title="Test", broadcast=False)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)

        msgs = []
        for uid in range(10):
            m = MagicMock()
            m.sender_id = uid
            m.sender = User(id=uid, first_name=f"U{uid}")
            msgs.append(m)

        async def mock_iter(*a, **kw):
            for m in msgs:
                yield m

        client.iter_messages = mock_iter
        svc = ChatsService(client)
        result = await svc.get_user_stats(-100, limit=3)
        assert len(result) == 3


class TestResolveChat:
    @pytest.mark.asyncio
    async def test_returns_entity(self):
        entity = _channel(1, title="Test", broadcast=True)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        svc = ChatsService(client)
        result = await svc.resolve_chat(-100)
        assert result is entity

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        svc = ChatsService(client)
        with pytest.raises(ChatNotFoundError):
            await svc.resolve_chat(-999)
