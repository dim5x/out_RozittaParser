"""
tests/test_features/test_finish_takeout.py

Тесты: finish_takeout.main() — async логика завершения Takeout-сессии.
Мокается TelegramClient и все его методы.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.setenv("TG_API_ID", "12345")
    monkeypatch.setenv("TG_API_HASH", "test_hash_abcdef")


@pytest.mark.asyncio
class TestFinishTakeoutAuthorized:
    @patch("finish_takeout.TelegramClient")
    async def test_calls_finish_takeout(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        me = MagicMock()
        me.first_name = "Test"
        me.username = "testuser"
        client.get_me.return_value = me
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        # client() was called (Telethon __call__)
        assert client.call_count == 1

    @patch("finish_takeout.TelegramClient")
    async def test_disconnect_after_success(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        me = MagicMock()
        me.first_name = "Test"
        me.username = None
        client.get_me.return_value = me
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        client.disconnect.assert_awaited()

    @patch("finish_takeout.TelegramClient")
    async def test_get_me_called(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        me = MagicMock()
        me.first_name = "Test"
        me.username = "testuser"
        client.get_me.return_value = me
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        client.get_me.assert_awaited()


@pytest.mark.asyncio
class TestFinishTakeoutNotAuthorized:
    @patch("finish_takeout.TelegramClient")
    async def test_returns_early_no_call(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = False
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        # client() was NOT called (Telethon __call__)
        assert client.call_count == 0

    @patch("finish_takeout.TelegramClient")
    async def test_get_me_not_called(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = False
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        client.get_me.assert_not_awaited()


@pytest.mark.asyncio
class TestFinishTakeoutErrors:
    @patch("finish_takeout.TelegramClient")
    async def test_no_takeout_handled(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        me = MagicMock()
        me.first_name = "Test"
        me.username = "testuser"
        client.get_me.return_value = me
        client.side_effect = Exception("NO_TAKEOUT_IN_PROGRESS")
        MockClient.return_value = client

        from finish_takeout import main
        await main()
        client.disconnect.assert_awaited()

    @patch("finish_takeout.TelegramClient")
    async def test_generic_exception_handled(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        me = MagicMock()
        me.first_name = "Test"
        me.username = "testuser"
        client.get_me.return_value = me
        client.side_effect = Exception("SOME_OTHER_ERROR")
        MockClient.return_value = client

        from finish_takeout import main
        await main()
        client.disconnect.assert_awaited()

    @patch("finish_takeout.TelegramClient")
    async def test_disconnect_after_error(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        me = MagicMock()
        me.first_name = "Test"
        me.username = "testuser"
        client.get_me.return_value = me
        client.side_effect = Exception("boom")
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        client.disconnect.assert_awaited()


@pytest.mark.asyncio
class TestFinishTakeoutClientCreation:
    @patch("finish_takeout.TelegramClient")
    async def test_client_created_with_params(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = False
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        MockClient.assert_called_once()
        call_kwargs = MockClient.call_args[1]
        assert call_kwargs["api_id"] == 12345
        assert call_kwargs["api_hash"] == "test_hash_abcdef"

    @patch("finish_takeout.TelegramClient")
    async def test_connect_called(self, MockClient):
        client = AsyncMock()
        client.is_user_authorized.return_value = False
        MockClient.return_value = client

        from finish_takeout import main
        await main()

        client.connect.assert_awaited()
