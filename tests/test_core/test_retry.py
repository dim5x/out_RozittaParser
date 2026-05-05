"""
tests/test_core/test_retry.py

Тесты: @async_retry — retry, backoff, FloodWait, edge cases.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from core.retry import async_retry


@pytest.mark.asyncio
class TestAsyncRetry:
    async def test_success_no_retry(self):
        fn = AsyncMock(return_value=42)
        decorated = async_retry()(fn)
        result = await decorated()
        assert result == 42
        assert fn.call_count == 1

    async def test_retriable_exception_retries(self):
        fn = AsyncMock(side_effect=[OSError("fail"), OSError("fail"), "ok"])
        decorated = async_retry(max_attempts=3, base_delay=0.01, backoff=1.0)(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await decorated()
        assert result == "ok"
        assert fn.call_count == 3

    async def test_exhausted_attempts_reraise(self):
        fn = AsyncMock(side_effect=OSError("persistent"))
        decorated = async_retry(max_attempts=2, base_delay=0.01)(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OSError, match="persistent"):
                await decorated()
        assert fn.call_count == 2

    async def test_non_retriable_reraise_immediately(self):
        fn = AsyncMock(side_effect=ValueError("bad"))
        decorated = async_retry(exc_retry=(OSError,))(fn)
        with pytest.raises(ValueError, match="bad"):
            await decorated()
        assert fn.call_count == 1

    async def test_flood_wait_does_not_count(self):
        call_count = 0

        class FakeFlood(Exception):
            seconds = 5

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise FakeFlood()
            return "ok"

        decorated = async_retry(
            max_attempts=1,
            base_delay=0.01,
            flood_cls=FakeFlood,
            flood_buffer=0.1,
        )(fn)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await decorated()

        assert result == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # только flood wait sleep

    async def test_max_attempts_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="max_attempts"):
            async_retry(max_attempts=0)

    async def test_preserves_function_metadata(self):
        @async_retry()
        async def my_function():
            """My doc."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My doc."

    async def test_exponential_backoff_timing(self):
        fn = AsyncMock(side_effect=[OSError("1"), OSError("2"), "ok"])
        delays = []

        async def fake_sleep(d):
            delays.append(d)

        decorated = async_retry(
            max_attempts=3, base_delay=1.0, backoff=2.0,
        )(fn)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await decorated()

        assert len(delays) == 2
        assert delays[0] == pytest.approx(1.0)   # 1.0 * 2^0
        assert delays[1] == pytest.approx(2.0)   # 1.0 * 2^1

    async def test_single_attempt_success(self):
        fn = AsyncMock(return_value="done")
        decorated = async_retry(max_attempts=1)(fn)
        result = await decorated()
        assert result == "done"
        assert fn.call_count == 1

    async def test_single_attempt_fail_reraise(self):
        fn = AsyncMock(side_effect=OSError("once"))
        decorated = async_retry(max_attempts=1, base_delay=0.01)(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OSError, match="once"):
                await decorated()


# ---------------------------------------------------------------------------
# S8: Advanced retry tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAsyncRetryAdvanced:
    async def test_negative_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            async_retry(max_attempts=-1)

    async def test_custom_exc_retry_tuple(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("retry me")
            return "ok"

        decorated = async_retry(
            max_attempts=3, base_delay=0.01, exc_retry=(ValueError,),
        )(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await decorated()
        assert result == "ok"
        assert call_count == 3

    async def test_different_exc_retry_not_retried(self):
        fn = AsyncMock(side_effect=TypeError("wrong"))
        decorated = async_retry(max_attempts=3, exc_retry=(OSError,))(fn)
        with pytest.raises(TypeError, match="wrong"):
            await decorated()
        assert fn.call_count == 1

    async def test_flood_wait_with_seconds(self):
        class Flood(Exception):
            seconds = 120

        fn = AsyncMock(side_effect=[Flood(), "ok"])
        decorated = async_retry(
            max_attempts=1, flood_cls=Flood, flood_buffer=3.0,
        )(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await decorated()
        assert result == "ok"
        assert mock_sleep.call_count == 1
        waited = mock_sleep.call_args[0][0]
        assert waited >= 120

    async def test_flood_wait_custom_buffer(self):
        class Flood(Exception):
            seconds = 10

        fn = AsyncMock(side_effect=[Flood(), "ok"])
        decorated = async_retry(
            max_attempts=1, flood_cls=Flood, flood_buffer=5.0,
        )(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await decorated()
        waited = mock_sleep.call_args[0][0]
        assert waited == pytest.approx(15.0)

    async def test_flood_wait_zero_seconds(self):
        class Flood(Exception):
            seconds = 0

        fn = AsyncMock(side_effect=[Flood(), "ok"])
        decorated = async_retry(
            max_attempts=1, flood_cls=Flood, flood_buffer=3.0,
        )(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await decorated()
        waited = mock_sleep.call_args[0][0]
        assert waited == pytest.approx(3.0)

    async def test_max_attempts_one_no_sleep(self):
        fn = AsyncMock(return_value="ok")
        decorated = async_retry(max_attempts=1)(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await decorated()
        assert result == "ok"
        mock_sleep.assert_not_called()

    async def test_return_value_preserved(self):
        data = {"key": [1, 2, 3], "nested": {"a": True}}
        fn = AsyncMock(return_value=data)
        decorated = async_retry()(fn)
        result = await decorated()
        assert result == data
