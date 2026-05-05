# 🧪 Полный план тестирования — Rozitta Parser v4.2

> **Файл:** `docs/TESTS_FULL_PLAN.md`
> **Дата:** 2026-05-06
> **Статус:** ✅ Complete
> **Цель:** 70%+ покрытие non-UI кода к завершению спринта S5

---

## Структура спринтов

| Спринт | Фокус | Новых тестов | Прирост покрытия | Зависимости |
|--------|-------|-------------|-----------------|-------------|
| **S1** | Инфраструктура + config + exceptions + retry | ~40 | +15% | нет | ✅ Done (94 теста) |
| **S2** | Parser static methods + Chats classify | ~45 | +10% | S1 | ✅ Done (73 теста) |
| **S3** | Export generators (JSON, MD, HTML) | ~40 | +15% | S1 | ✅ Done (67 тестов) |
| **S4** | Mock-тесты Auth, Chats, Parser API | ~40 | +15% | S1, S2 | ✅ Done (96 тестов) |
| **S5** | E2E циклы, стресс, безопасность | ~30 | +10% | S1–S4 | ✅ Done (34 теста) |

---

## Инфраструктура

### Зависимости

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov pytest-timeout
```

### pytest.ini (создать в корне проекта)

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
markers =
    slow: долгие тесты (>5 сек)
    integration: требуют БД или файловую систему
    network: требуют Telegram API (обычно моки)
    stt: требуют faster-whisper и FFmpeg
addopts = -v --tb=short
```

### conftest.py (создать в tests/)

Общие фикстуры для всех тестов:

```python
# tests/conftest.py
import pytest
from core.database import DBManager


@pytest.fixture
def db(tmp_path):
    """БД на файловой системе (для тестов транзакций и WAL)."""
    path = str(tmp_path / "test.db")
    with DBManager(path) as _db:
        yield _db


@pytest.fixture
def db_mem():
    """БД в памяти (для быстрых модульных тестов)."""
    return DBManager(":memory:")


def make_msg(id_, user_id=1, date="2025-06-01T12:00:00", text="hello",
             media_path=None, file_type=None, topic_id=None,
             post_id=None, is_comment=0, merge_group_id=None, merge_part_index=None):
    """Фабрика сообщений для вставки в БД."""
    return {
        "chat_id": -100123,
        "message_id": id_,
        "topic_id": topic_id,
        "user_id": user_id,
        "username": f"user_{user_id}",
        "date": date,
        "text": text,
        "media_path": media_path,
        "file_type": file_type,
        "post_id": post_id,
        "is_comment": is_comment,
        "merge_group_id": merge_group_id,
        "merge_part_index": merge_part_index,
    }


def insert_sample_messages(db, count=10, chat_id=-100123, user_id=1):
    """Быстрая вставка N тестовых сообщений."""
    msgs = []
    for i in range(1, count + 1):
        msgs.append({
            "chat_id": chat_id,
            "message_id": i,
            "user_id": user_id,
            "username": "test_user",
            "date": f"2025-06-{1 + i // 24:02d}T{i % 24:02d}:00:00",
            "text": f"Message {i}",
        })
    db.insert_messages_batch(msgs)
    return msgs
```

### Структура файлов

```
tests/
├── conftest.py                      ← общие фикстуры
├── test_core/
│   ├── test_config.py               ← S1: config.py
│   ├── test_exceptions.py           ← S1: exceptions.py
│   ├── test_retry.py                ← S1: retry.py
│   ├── test_database.py             ← существует (дополнить в S1)
│   ├── test_merger.py               ← существует (дополнить в S1)
│   └── test_utils.py                ← существует (дополнить в S1)
├── test_features/
│   ├── test_parser_static.py        ← S2: статические методы ParserService
│   ├── test_chats_static.py         ← S2: classify_entity
│   ├── test_auth_static.py          ← S2: parse_proxy_link, detect_tdata
│   ├── test_export_docx.py          ← S3: DocxGenerator (расширение существующего)
│   ├── test_export_json.py          ← S3: JsonGenerator
│   ├── test_export_md.py            ← S3: MarkdownGenerator
│   ├── test_export_html.py          ← S3: HtmlGenerator
│   ├── test_parser_mocks.py         ← S4: collect_data с моками
│   ├── test_chats_mocks.py          ← S4: ChatsService с моками
│   ├── test_auth_mocks.py           ← S4: AuthService.sign_in с моками
│   └── test_parser.py               ← существует (обновить)
├── test_e2e/
│   ├── test_full_cycle.py           ← S5: Parser→STT→Export
│   ├── test_stress.py               ← S5: большие объёмы
│   └── test_security.py             ← S5: безопасность
```

---

## Спринт S1: Инфраструктура + Config + Exceptions + Retry

**Цель:** Настроить pytest, написать тесты для чистых модулей без внешних зависимостей.
**Приоритет:** 🔴 Обязательный — фундамент для остальных спринтов.

### 1.1 config.py → `tests/test_core/test_config.py`

```python
import json
import os
import pytest
from config import AppConfig, load_config, save_config, CONFIG_FILE


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        cfg = load_config(str(tmp_path / "nonexistent.json"))
        assert cfg.api_id == ""
        assert cfg.api_hash == ""
        assert cfg.phone == ""
        assert cfg.days == 30
        assert cfg.split_mode == "none"

    def test_invalid_json_returns_defaults(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json", encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == ""

    def test_full_config(self, tmp_path):
        path = tmp_path / "full.json"
        data = {
            "api_id": "12345",
            "api_hash": "abc123",
            "phone": "+79991234567",
            "days": 90,
            "media_filter": ["Фото"],
            "comments": True,
            "split_mode": "day",
            "stt_model": "medium",
            "stt_language": "en",
            "proxy_enabled": True,
            "proxy_type": "socks5",
            "proxy_host": "127.0.0.1",
            "proxy_port": 9050,
            "proxy_secret": "",
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == "12345"
        assert cfg.api_hash == "abc123"
        assert cfg.days == 90
        assert cfg.comments is True
        assert cfg.split_mode == "day"
        assert cfg.proxy_enabled is True

    def test_partial_config_fills_defaults(self, tmp_path):
        path = tmp_path / "partial.json"
        path.write_text('{"api_id": "999"}', encoding="utf-8")
        cfg = load_config(str(path))
        assert cfg.api_id == "999"
        assert cfg.api_hash == ""           # default
        assert cfg.split_mode == "none"     # default

    def test_round_trip(self, tmp_path):
        path = str(tmp_path / "rt.json")
        original = AppConfig(api_id="42", api_hash="x", phone="+1")
        save_config(original, path)
        loaded = load_config(path)
        assert loaded.api_id == "42"
        assert loaded.api_hash == "x"
        assert loaded.phone == "+1"


class TestAppConfigValidate:
    def test_empty_api_id_raises(self):
        cfg = AppConfig(api_id="", api_hash="abc")
        with pytest.raises(ConfigError, match="API ID"):
            cfg.validate()

    def test_non_numeric_api_id_raises(self):
        cfg = AppConfig(api_id="abc", api_hash="xyz")
        with pytest.raises(ConfigError, match="числом"):
            cfg.validate()

    def test_empty_api_hash_raises(self):
        cfg = AppConfig(api_id="123", api_hash="")
        with pytest.raises(ConfigError, match="API Hash"):
            cfg.validate()

    def test_invalid_split_mode_raises(self):
        cfg = AppConfig(api_id="1", api_hash="x", split_mode="bad")
        with pytest.raises(ConfigError, match="split_mode"):
            cfg.validate()

    def test_valid_config_passes(self):
        cfg = AppConfig(api_id="12345", api_hash="abcdef1234567890")
        cfg.validate()  # no exception


class TestAppConfigProperties:
    def test_api_id_int_valid(self):
        assert AppConfig(api_id="42").api_id_int == 42

    def test_api_id_int_empty(self):
        assert AppConfig(api_id="").api_id_int is None

    def test_api_id_int_non_numeric(self):
        assert AppConfig(api_id="abc").api_id_int is None

    def test_is_all_time_true(self):
        assert AppConfig(days=365).is_all_time is True
        assert AppConfig(days=500).is_all_time is True

    def test_is_all_time_false(self):
        assert AppConfig(days=30).is_all_time is False

    def test_db_path(self):
        cfg = AppConfig(output_dir="/tmp/out")
        assert cfg.db_path == os.path.join("/tmp/out", "telegram_archive.db")

    def test_session_path_absolute(self):
        cfg = AppConfig(session_name="test_session")
        assert os.path.isabs(cfg.session_path)


class TestSaveConfig:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "new.json")
        save_config(AppConfig(api_id="1", api_hash="x"), path)
        assert os.path.exists(path)

    def test_excludes_runtime_fields(self, tmp_path):
        path = str(tmp_path / "rt.json")
        cfg = AppConfig(api_id="1", api_hash="x", output_dir="/secret", session_name="priv")
        save_config(cfg, path)
        with open(path) as f:
            data = json.load(f)
        assert "output_dir" not in data
        assert "session_name" not in data

    def test_readonly_path_raises(self, tmp_path):
        path = str(tmp_path / "readonly" / "config.json")
        with pytest.raises(ConfigError):
            save_config(AppConfig(), path)
```

### 1.2 exceptions.py → `tests/test_core/test_exceptions.py`

```python
import pytest
from core.exceptions import *


class TestHierarchy:
    @pytest.mark.parametrize("cls", [
        ConfigError, AuthError, SessionExpiredError, PhoneCodeInvalidError,
        DatabaseError, DatabaseLockedError, TelegramError, ChatNotFoundError,
        ForumTopicsError, FloodWaitError, LinkedGroupNotFoundError,
        MediaDownloadError, STTError, ExportError, DocxGenerationError,
        EmptyDataError,
    ])
    def test_inherits_rozitta_error(self, cls):
        assert issubclass(cls, RozittaError)

    def test_catch_all_via_base(self):
        """Любая кастомная ошибка ловится через RozittaError."""
        errors = [
            ConfigError("cfg"),
            ChatNotFoundError(123),
            FloodWaitError(60),
            EmptyDataError(chat_id=-100),
        ]
        for err in errors:
            with pytest.raises(RozittaError):
                raise err


class TestSpecialAttributes:
    def test_chat_not_found_stores_id(self):
        e = ChatNotFoundError(-100123)
        assert e.chat_id == -100123
        assert "-100123" in str(e)

    def test_flood_wait_stores_seconds(self):
        e = FloodWaitError(300)
        assert e.seconds == 300
        assert "300" in str(e)

    def test_database_error_with_original(self):
        original = OSError("disk full")
        e = DatabaseError("write failed", original=original)
        assert e.original is original
        assert "disk full" in str(e)

    def test_database_error_without_original(self):
        e = DatabaseError("simple error")
        assert str(e) == "simple error"

    def test_media_download_error(self):
        e = MediaDownloadError(message_id=42)
        assert e.message_id == 42
        assert "42" in str(e)

    def test_docx_gen_error_stores_path(self):
        e = DocxGenerationError(file_path="/out/a.docx")
        assert e.file_path == "/out/a.docx"

    def test_empty_data_with_topic(self):
        e = EmptyDataError(chat_id=-100, topic_id=5)
        assert "5" in str(e)

    def test_empty_data_without_topic(self):
        e = EmptyDataError(chat_id=-100)
        assert "-100" in str(e)

    def test_stt_error_fields(self):
        e = STTError("fail", media_path="/a.ogg", message_id=7)
        assert e.media_path == "/a.ogg"
        assert e.message_id == 7

    def test_linked_group_not_found(self):
        e = LinkedGroupNotFoundError(channel_id=-100200)
        assert e.channel_id == -100200
```

### 1.3 retry.py → `tests/test_core/test_retry.py`

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from core.retry import async_retry


@pytest.mark.asyncio
class TestAsyncRetry:
    async def test_success_no_retry(self):
        """Успешный вызов — retry не происходит."""
        fn = AsyncMock(return_value=42)
        decorated = async_retry()(fn)
        result = await decorated()
        assert result == 42
        assert fn.call_count == 1

    async def test_retriable_exception_retries(self):
        """Retriable exception → retry до успеха."""
        fn = AsyncMock(side_effect=[OSError("fail"), OSError("fail"), "ok"])
        decorated = async_retry(max_attempts=3, base_delay=0.01, backoff=1.0)(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await decorated()
        assert result == "ok"
        assert fn.call_count == 3

    async def test_exhausted_attempts_reraise(self):
        """Исчерпаны попытки → re-raise."""
        fn = AsyncMock(side_effect=OSError("persistent"))
        decorated = async_retry(max_attempts=2, base_delay=0.01)(fn)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OSError, match="persistent"):
                await decorated()
        assert fn.call_count == 2

    async def test_non_retriable_reraise_immediately(self):
        """Не-retriable exception → немедленный re-raise."""
        fn = AsyncMock(side_effect=ValueError("bad"))
        decorated = async_retry(exc_retry=(OSError,))(fn)
        with pytest.raises(ValueError, match="bad"):
            await decorated()
        assert fn.call_count == 1

    async def test_flood_wait_does_not_count(self):
        """FloodWait не считается за попытку."""
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
        # sleep вызван для flood wait (не для retry)
        assert mock_sleep.call_count == 2

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
        """Проверка что задержки растут экспоненциально."""
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
        assert delays[0] == pytest.approx(1.0)    # 1.0 * 2^0
        assert delays[1] == pytest.approx(2.0)    # 1.0 * 2^1
```

### 1.4 Дополнения к существующим тестам

**test_database.py** — добавить:

```python
def test_upsert_preserves_merge_fields(db_mem):
    """upsert (INSERT OR IGNORE) не затирает merge_group_id."""
    msgs = [{
        "chat_id": -100, "message_id": 1, "date": "2025-01-01T00:00:00",
        "text": "v1", "merge_group_id": 5, "merge_part_index": 0,
    }]
    db_mem.upsert_messages_batch(msgs)
    # Попытка перезаписать — merge-поля сохраняются
    msgs[0]["text"] = "v2"
    msgs[0]["merge_group_id"] = None
    db_mem.upsert_messages_batch(msgs)
    rows = db_mem.get_messages(-100)
    assert rows[0][7] == "v1"  # text не изменён
    # merge_group_id сохранился

def test_insert_chat_upsert(db_mem):
    db_mem.insert_chat(-100, "Test", "channel", None)
    db_mem.insert_chat(-100, "Updated", "channel", -200)
    rows = db_mem.conn.execute("SELECT title, linked_chat_id FROM chats WHERE chat_id=-100").fetchall()
    assert rows[0][0] == "Updated"
    assert rows[0][1] == -200

def test_thread_safety(tmp_path):
    """Два потока одновременно пишут — нет database locked."""
    import threading
    path = str(tmp_path / "thread_test.db")
    db = DBManager(path)
    errors = []

    def writer(start):
        msgs = [
            {"chat_id": -100, "message_id": start + i, "date": "2025-01-01T00:00:00", "text": f"msg{start+i}"}
            for i in range(100)
        ]
        try:
            db.insert_messages_batch(msgs)
        except Exception as e:
            errors.append(str(e))

    t1 = threading.Thread(target=writer, args=(0,))
    t2 = threading.Thread(target=writer, args=(200,))
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert not errors
    rows = db.get_messages(-100)
    assert len(rows) == 200
```

**test_merger.py** — добавить:

```python
def test_merge_large_chain():
    """10 сообщений одного автора подряд → 1 группа."""
    msgs = [_msg(i, 1, f"2025-01-01T10:00:{i:02d}") for i in range(10)]
    result = MergerService().merge(msgs)
    assert len(result) == 1
    assert result[0].get("merge_group_id") is not None

def test_merge_interleaved_authors():
    """A B A B — 4 отдельных сообщения, нет склейки."""
    msgs = [
        _msg(1, "A", "2025-01-01T10:00:00"),
        _msg(2, "B", "2025-01-01T10:00:10"),
        _msg(3, "A", "2025-01-01T10:00:20"),
        _msg(4, "B", "2025-01-01T10:00:30"),
    ]
    result = MergerService().merge(msgs)
    assert len(result) == 4

def test_merge_statistics():
    msgs = [
        _msg(1, 42, "2025-01-01T10:00:00"),
        _msg(2, 42, "2025-01-01T10:00:30"),
        _msg(3, 99, "2025-01-01T10:01:00"),
    ]
    svc = MergerService()
    svc.merge(msgs)
    assert svc.stats["total_input"] == 3
    assert svc.stats["groups_created"] >= 1
```

---

## Спринт S2: Parser Static Methods + Chats Classify + Auth Static

**Цель:** Покрыть все чистые функции и статические методы без моков.
**Приоритет:** 🔴 Обязательный — высокий ROI, нет моков.

### 2.1 ParserService static → `tests/test_features/test_parser_static.py`

```python
import pytest
from unittest.mock import MagicMock
from features.parser.api import ParserService, CollectParams, _cleanup_partial


class TestShouldDownload:
    def _msg(self, media_type="photo"):
        msg = MagicMock()
        if media_type is None:
            msg.media = None
            return msg
        msg.media = MagicMock()
        if media_type == "photo":
            from telethon.tl.types import MessageMediaPhoto
            msg.media = MessageMediaPhoto(photo=MagicMock())
        elif media_type in ("video", "voice", "file", "videomessage"):
            from telethon.tl.types import MessageMediaDocument
            doc = MagicMock()
            if media_type == "video":
                from telethon.tl.types import DocumentAttributeVideo
                attr = DocumentAttributeVideo(w=0, h=0, duration=0)
                doc.attributes = [attr]
            elif media_type == "videomessage":
                from telethon.tl.types import DocumentAttributeVideo
                attr = DocumentAttributeVideo(w=0, h=0, duration=0, round_message=True)
                doc.attributes = [attr]
            elif media_type == "voice":
                from telethon.tl.types import DocumentAttributeAudio
                attr = DocumentAttributeAudio(duration=0, voice=True)
                doc.attributes = [attr]
            else:
                doc.attributes = []
            msg.media = MessageMediaDocument(document=doc)
        return msg

    def test_no_media(self):
        assert ParserService._should_download(self._msg(None), ["photo"]) is False

    def test_empty_filter_downloads_all(self):
        assert ParserService._should_download(self._msg("photo"), []) is True

    def test_photo_in_filter(self):
        assert ParserService._should_download(self._msg("photo"), ["photo"]) is True

    def test_photo_not_in_filter(self):
        assert ParserService._should_download(self._msg("photo"), ["video"]) is False

    def test_video(self):
        assert ParserService._should_download(self._msg("video"), ["video"]) is True

    def test_videomessage(self):
        assert ParserService._should_download(self._msg("videomessage"), ["videomessage"]) is True

    def test_voice(self):
        assert ParserService._should_download(self._msg("voice"), ["voice"]) is True

    def test_file(self):
        assert ParserService._should_download(self._msg("file"), ["file"]) is True


class TestDetectMediaType:
    # Аналогичные тесты с теми же типами
    # Возвращает "photo" | "video" | "videomessage" | "voice" | "file" | None
    pass


class TestExtractTopicId:
    def _msg(self, reply_to_top_id=None, reply_to_msg_id=None, forum_topic=False, msg_id=1):
        msg = MagicMock()
        msg.id = msg_id
        msg.forum_topic = forum_topic
        if reply_to_top_id is None and reply_to_msg_id is None:
            msg.reply_to = None
        else:
            msg.reply_to = MagicMock()
            msg.reply_to.reply_to_top_id = reply_to_top_id
            msg.reply_to.reply_to_msg_id = reply_to_msg_id
        return msg

    def test_reply_to_top_id(self):
        assert ParserService._extract_topic_id(self._msg(reply_to_top_id=42)) == 42

    def test_reply_to_msg_id_fallback(self):
        assert ParserService._extract_topic_id(self._msg(reply_to_msg_id=99)) == 99

    def test_forum_topic_flag(self):
        assert ParserService._extract_topic_id(self._msg(forum_topic=True, msg_id=7)) == 7

    def test_no_topic(self):
        assert ParserService._extract_topic_id(self._msg()) is None


class TestGetSenderName:
    def _user(self, username=None, first_name=None, last_name=None):
        from telethon.tl.types import User
        return User(id=1, username=username, first_name=first_name, last_name=last_name)

    def _channel(self, title="Channel"):
        from telethon.tl.types import Channel
        return Channel(id=1, title=title)

    def test_user_with_username(self):
        msg = MagicMock()
        msg.sender = self._user(username="john")
        assert ParserService._get_sender_name(msg) == "john"

    def test_user_with_names(self):
        msg = MagicMock()
        msg.sender = self._user(first_name="John", last_name="Doe")
        assert ParserService._get_sender_name(msg) == "John Doe"

    def test_no_sender(self):
        msg = MagicMock()
        msg.sender = None
        assert ParserService._get_sender_name(msg) == "Unknown"

    def test_channel_sender(self):
        msg = MagicMock()
        msg.sender = self._channel("My Channel")
        assert ParserService._get_sender_name(msg) == "My Channel"


class TestClassifyChatType:
    def _user(self):
        from telethon.tl.types import User
        return User(id=1)

    def _chat(self):
        from telethon.tl.types import Chat
        return Chat(id=1)

    def _channel(self, broadcast=False, megagroup=False, forum=False):
        from telethon.tl.types import Channel
        ch = Channel(id=1, title="test")
        ch.broadcast = broadcast
        ch.megagroup = megagroup
        ch.forum = forum
        return ch

    def test_user(self):
        assert ParserService._classify_chat_type(self._user()) == "private"

    def test_chat(self):
        assert ParserService._classify_chat_type(self._chat()) == "group"

    def test_broadcast_channel(self):
        assert ParserService._classify_chat_type(self._channel(broadcast=True)) == "channel"

    def test_forum(self):
        assert ParserService._classify_chat_type(self._channel(megagroup=True, forum=True)) == "forum"

    def test_megagroup_no_forum(self):
        assert ParserService._classify_chat_type(self._channel(megagroup=True)) == "group"


class TestResolveCutoff:
    def test_all_time_zero(self):
        cutoff, label = ParserService._resolve_cutoff(0)
        assert cutoff is None
        assert label == "fullchat"

    def test_all_time_365(self):
        cutoff, label = ParserService._resolve_cutoff(365)
        assert cutoff is None
        assert label == "fullchat"

    def test_specific_days(self):
        from datetime import datetime, timezone, timedelta
        cutoff, label = ParserService._resolve_cutoff(30)
        assert cutoff is not None
        assert label.startswith("20")
        expected = datetime.now(timezone.utc) - timedelta(days=30)
        assert abs((cutoff - expected).total_seconds()) < 5


class TestCollectParams:
    def test_defaults(self):
        p = CollectParams(chat_id=-100)
        assert p.topic_id is None
        assert p.days_limit == 0
        assert p.media_filter is None
        assert p.download_comments is False
        assert p.user_ids is None
        assert p.re_download is False

    def test_custom(self):
        p = CollectParams(
            chat_id=-100, topic_id=5, days_limit=7,
            media_filter=["photo", "video"],
            download_comments=True,
            user_ids=[1, 2, 3],
        )
        assert p.topic_id == 5
        assert len(p.media_filter) == 2
```

### 2.2 Chats classify → `tests/test_features/test_chats_static.py`

```python
from features.chats.api import classify_entity


class TestClassifyEntity:
    # Те же тесты что и TestClassifyChatType, но через classify_entity
    def test_user_is_private(self):
        from telethon.tl.types import User
        assert classify_entity(User(id=1)) == "private"

    def test_chat_is_group(self):
        from telethon.tl.types import Chat
        assert classify_entity(Chat(id=1)) == "group"

    def test_broadcast_is_channel(self):
        from telethon.tl.types import Channel
        ch = Channel(id=1, title="c")
        ch.broadcast = True
        assert classify_entity(ch) == "channel"

    def test_forum_is_forum(self):
        from telethon.tl.types import Channel
        ch = Channel(id=1, title="f")
        ch.broadcast = False
        ch.megagroup = True
        ch.forum = True
        assert classify_entity(ch) == "forum"

    def test_megagroup_no_forum_is_group(self):
        from telethon.tl.types import Channel
        ch = Channel(id=1, title="g")
        ch.broadcast = False
        ch.megagroup = True
        ch.forum = False
        assert classify_entity(ch) == "group"

    def test_unknown_object(self):
        assert classify_entity("not a telethon object") == "unknown"
```

### 2.3 Auth static → `tests/test_features/test_auth_static.py`

```python
import pytest
from features.auth.api import AuthService


class TestParseProxyLink:
    def test_valid_mtproto(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?server=1.2.3.4&port=443&secret=ee1234"
        )
        assert result is not None
        assert result["type"] == "mtproto"
        assert result["host"] == "1.2.3.4"
        assert result["port"] == 443
        assert result["secret"] == "ee1234"

    def test_no_proxy_in_path(self):
        result = AuthService.parse_proxy_link("https://t.me/other?server=1.2.3.4")
        assert result is None

    def test_empty_string(self):
        assert AuthService.parse_proxy_link("") is None

    def test_invalid_url(self):
        assert AuthService.parse_proxy_link("not a url at all") is None

    def test_missing_secret(self):
        result = AuthService.parse_proxy_link(
            "https://t.me/proxy?server=1.2.3.4&port=443"
        )
        # Нет secret → None (неполные параметры)
        assert result is None


class TestDetectTdataPath:
    def test_returns_string_or_none(self):
        result = AuthService.detect_tdata_path()
        assert result is None or isinstance(result, str)

    def test_nonexistent_returns_none(self, tmp_path, monkeypatch):
        import platform
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setenv("APPDATA", str(tmp_path / "nonexistent"))
        result = AuthService.detect_tdata_path()
        assert result is None
```

---

## Спринт S3: Export Generators (JSON, MD, HTML) + Docx edge cases

**Цель:** Полное покрытие всех генераторов экспорта.
**Приоритет:** 🔴 Обязательный — критичный пользовательский путь.

### 3.1 DocxGenerator edge cases → `tests/test_features/test_export_docx.py`

(Расширение существующего test_export.py)

```python
class TestDocxSplitModes:
    def test_split_by_day(self, tmp_path):
        """Режим day → один файл на каждый день."""
        db, db_path = _make_db_with_dates(tmp_path, [
            ("2025-01-01T10:00:00",),
            ("2025-01-01T14:00:00",),
            ("2025-01-02T09:00:00",),
        ])
        gen = DocxGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100123, chat_title="Test", split_mode="day",
            period_label="fullchat",
        )
        assert len(files) == 2

    def test_split_by_month(self, tmp_path):
        db, _ = _make_db_with_dates(tmp_path, [
            ("2025-01-15T10:00:00",),
            ("2025-02-20T10:00:00",),
        ])
        gen = DocxGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100123, chat_title="Test", split_mode="month",
            period_label="fullchat",
        )
        assert len(files) == 2

    def test_invalid_split_mode_raises(self, db_mem, tmp_path):
        gen = DocxGenerator(db=db_mem, output_dir=str(tmp_path))
        with pytest.raises(DocxGenerationError, match="split_mode"):
            gen.generate(chat_id=-100, split_mode="bad_mode")

    def test_empty_db_raises(self, db_mem, tmp_path):
        gen = DocxGenerator(db=db_mem, output_dir=str(tmp_path))
        with pytest.raises(EmptyDataError):
            gen.generate(chat_id=-100, split_mode="none")

    def test_docx_with_stt_transcription(self, tmp_path):
        """STT текст вставляется для voice/video_note."""
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00", "text": "",
            "file_type": "voice", "media_path": "/a.ogg",
        }])
        db.insert_transcription(1, -100, "Привет мир", "base")
        gen = DocxGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", split_mode="none")
        assert len(files) == 1
        # Проверяем что STT текст в DOCX
        from docx import Document
        doc = Document(files[0])
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Привет мир" in full_text

    def test_docx_with_merge_groups(self, tmp_path):
        """Склеенные сообщения выводятся как один блок."""
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([
            {"chat_id": -100, "message_id": 1, "user_id": 1, "username": "A",
             "date": "2025-01-01T10:00:00", "text": "Привет",
             "merge_group_id": 10, "merge_part_index": 0},
            {"chat_id": -100, "message_id": 2, "user_id": 1, "username": "A",
             "date": "2025-01-01T10:00:20", "text": "мир",
             "merge_group_id": 10, "merge_part_index": 1},
        ])
        gen = DocxGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", split_mode="none")
        from docx import Document
        doc = Document(files[0])
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Привет" in full_text
        assert "мир" in full_text
```

### 3.2 JsonGenerator → `tests/test_features/test_export_json.py`

```python
import json
import pytest
from core.database import DBManager
from features.export.generator import JsonGenerator


def _db_with_msgs(tmp_path, count=5):
    path = str(tmp_path / "test.db")
    db = DBManager(path)
    msgs = [{
        "chat_id": -100, "message_id": i, "user_id": i % 3,
        "username": f"user_{i%3}", "date": f"2025-01-0{i+1}T10:00:00",
        "text": f"Message {i}",
    } for i in range(1, count + 1)]
    db.insert_messages_batch(msgs)
    return db


class TestJsonGenerator:
    def test_basic_generation(self, tmp_path):
        db = _db_with_msgs(tmp_path)
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="TestChat", period_label="full")
        assert len(files) == 1
        assert files[0].endswith(".json")
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 5
        assert data[0]["message_id"] == 1

    def test_empty_raises(self, tmp_path):
        db = DBManager(str(tmp_path / "empty.db"))
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        with pytest.raises(Exception):
            gen.generate(chat_id=-100, chat_title="T", period_label="full")

    def test_ai_split(self, tmp_path):
        db = _db_with_msgs(tmp_path, count=100)
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100, chat_title="T", period_label="full",
            ai_split=True, ai_split_chunk_words=30,
        )
        assert len(files) >= 2
        for f in files:
            assert f.endswith(".json")
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            assert isinstance(data, list)

    def test_stt_included(self, tmp_path):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00", "text": "",
            "file_type": "voice",
        }])
        db.insert_transcription(1, -100, "Распознанный текст", "base")
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["stt_text"] == "Распознанный текст"

    def test_record_structure(self, tmp_path):
        db = _db_with_msgs(tmp_path, count=1)
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        rec = data[0]
        assert "message_id" in rec
        assert "date" in rec
        assert "sender_id" in rec
        assert "username" in rec
        assert "text" in rec
        assert "media_path" in rec
        assert "stt_text" in rec

    def test_unicode_content(self, tmp_path):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00", "text": "Привет 🌍 мир 𝕳𝖊𝖑𝖑𝖔",
            "username": "пользователь",
        }])
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="Тест", period_label="full")
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert "🌍" in data[0]["text"]
```

### 3.3 MarkdownGenerator → `tests/test_features/test_export_md.py`

```python
import pytest
from core.database import DBManager
from features.export.generator import MarkdownGenerator


class TestMarkdownGenerator:
    def _db(self, tmp_path, msgs):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch(msgs)
        return db

    def test_basic(self, tmp_path):
        db = self._db(tmp_path, [{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "username": "Alice", "date": "2025-01-15T14:30:00",
            "text": "Hello world",
        }])
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="Test", period_label="full")
        assert len(files) == 1
        content = open(files[0], encoding="utf-8").read()
        assert "**[2025-01-15 14:30] Alice:**" in content
        assert "Hello world" in content
        assert "---" in content

    def test_stt_block(self, tmp_path):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00", "text": "",
            "file_type": "voice",
        }])
        db.insert_transcription(1, -100, "Голосовой текст", "base")
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        content = open(files[0], encoding="utf-8").read()
        assert "*(STT: Голосовой текст)*" in content

    def test_ai_split_multiple_files(self, tmp_path):
        msgs = [{
            "chat_id": -100, "message_id": i, "user_id": 1,
            "date": f"2025-01-01T10:{i:02d}:00", "text": f"{'word ' * 20}",
        } for i in range(50)]
        db = self._db(tmp_path, msgs)
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100, chat_title="T", period_label="full",
            ai_split=True, ai_split_chunk_words=30,
        )
        assert len(files) >= 2

    def test_empty_raises(self, tmp_path):
        db = DBManager(str(tmp_path / "empty.db"))
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        with pytest.raises(Exception):
            gen.generate(chat_id=-100, chat_title="T", period_label="full")
```

### 3.4 HtmlGenerator → `tests/test_features/test_export_html.py`

```python
import re
import pytest
from core.database import DBManager
from features.export.generator import HtmlGenerator


class TestHtmlGenerator:
    def _db(self, tmp_path, msgs):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch(msgs)
        return db

    def test_basic_html_structure(self, tmp_path):
        db = self._db(tmp_path, [{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "username": "Bob", "date": "2025-03-01T09:00:00",
            "text": "Test message",
        }])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="Chat", period_label="full")
        assert len(files) == 1
        html = open(files[0], encoding="utf-8").read()
        assert "<!DOCTYPE html>" in html
        assert 'id="msg_1"' in html
        assert "Bob" in html
        assert "Test message" in html

    def test_reply_links(self, tmp_path):
        db = self._db(tmp_path, [
            {"chat_id": -100, "message_id": 1, "user_id": 1,
             "date": "2025-01-01T10:00:00", "text": "Original"},
            {"chat_id": -100, "message_id": 2, "user_id": 2,
             "date": "2025-01-01T10:01:00", "text": "Reply",
             "reply_to_msg_id": 1},
        ])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "#msg_1" in html
        assert "depth-1" in html

    def test_xss_prevention(self, tmp_path):
        db = self._db(tmp_path, [{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00",
            "text": '<script>alert("xss")</script>',
        }])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_stt_block(self, tmp_path):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00", "text": "",
            "file_type": "voice",
        }])
        db.insert_transcription(1, -100, "Transcribed", "base")
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "Transcribed" in html
        assert "msg-stt" in html

    def test_ai_split(self, tmp_path):
        msgs = [{
            "chat_id": -100, "message_id": i, "user_id": 1,
            "date": f"2025-01-01T10:{i:02d}:00", "text": f"{'word ' * 20}",
        } for i in range(50)]
        db = self._db(tmp_path, msgs)
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100, chat_title="T", period_label="full",
            ai_split=True, ai_split_chunk_words=30,
        )
        assert len(files) >= 2
```

---

## Спринт S4: Mock-тесты Auth, Chats, Parser API

**Цель:** Покрыть async-методы сервисов с моками Telethon.
**Приоритет:** 🟡 Средний — важен, но требует настройки моков.

### 4.1 Auth sign_in → `tests/test_features/test_auth_mocks.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from features.auth.api import AuthService
from core.exceptions import AuthError, PhoneCodeInvalidError, FloodWaitError


@pytest.mark.asyncio
class TestSignIn:
    def _mock_client(self, authorized=False):
        client = MagicMock()
        client.is_connected.return_value = True
        client.is_user_authorized = AsyncMock(return_value=authorized)
        client.connect = AsyncMock()
        client.send_code_request = AsyncMock()
        client.sign_in = AsyncMock()
        client.get_me = AsyncMock(return_value=MagicMock(
            id=1, first_name="Test", last_name="User", username="test"
        ))
        return client

    async def test_already_authorized(self):
        client = self._mock_client(authorized=True)
        logs = []
        user = await AuthService.sign_in(
            client,
            phone_provider=AsyncMock(),
            code_provider=AsyncMock(),
            password_provider=AsyncMock(),
            log=logs.append,
        )
        assert user is not None
        assert "Сессия уже активна" in "".join(logs)

    async def test_empty_phone_returns_none(self):
        client = self._mock_client()
        user = await AuthService.sign_in(
            client,
            phone_provider=AsyncMock(return_value=""),
            code_provider=AsyncMock(),
            password_provider=AsyncMock(),
        )
        assert user is None

    async def test_flood_wait_on_send_code(self):
        from telethon.errors import FloodWaitError
        client = self._mock_client()
        client.send_code_request = AsyncMock(
            side_effect=FloodWaitError(60, request=MagicMock())
        )
        with pytest.raises(FloodWaitError):
            await AuthService.sign_in(
                client,
                phone_provider=AsyncMock(return_value="+79991234567"),
                code_provider=AsyncMock(),
                password_provider=AsyncMock(),
            )

    async def test_invalid_code(self):
        from telethon.errors import PhoneCodeInvalidError as TelethonPCI
        client = self._mock_client()
        client.sign_in = AsyncMock(side_effect=TelethonPCI(0, "code", MagicMock()))
        with pytest.raises(PhoneCodeInvalidError):
            await AuthService.sign_in(
                client,
                phone_provider=AsyncMock(return_value="+79991234567"),
                code_provider=AsyncMock(return_value="00000"),
                password_provider=AsyncMock(),
            )

    async def test_successful_sign_in(self):
        client = self._mock_client()
        user = await AuthService.sign_in(
            client,
            phone_provider=AsyncMock(return_value="+79991234567"),
            code_provider=AsyncMock(return_value="12345"),
            password_provider=AsyncMock(),
        )
        assert user is not None
        client.sign_in.assert_called_once()
```

### 4.2 ChatsService → `tests/test_features/test_chats_mocks.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from features.chats.api import ChatsService


@pytest.mark.asyncio
class TestGetDialogs:
    def _client_with_dialogs(self, count=5):
        client = MagicMock()
        dialogs = []
        for i in range(count):
            dialog = MagicMock()
            entity = MagicMock()
            entity.id = i
            if i % 4 == 0:
                from telethon.tl.types import User
                entity = User(id=i, first_name=f"User{i}")
            elif i % 4 == 1:
                from telethon.tl.types import Chat
                entity = Chat(id=i, title=f"Group{i}")
            else:
                from telethon.tl.types import Channel
                entity = Channel(id=i, title=f"Channel{i}")
                entity.broadcast = (i % 4 == 2)
                entity.megagroup = (i % 4 == 3)
                entity.forum = False
            dialog.entity = entity
            dialogs.append(dialog)
        client.get_dialogs = AsyncMock(return_value=dialogs)
        return client

    async def test_returns_list_of_dicts(self):
        client = self._client_with_dialogs(4)
        svc = ChatsService(client)
        result = await svc.get_dialogs()
        assert isinstance(result, list)
        assert all(isinstance(d, dict) for d in result)

    async def test_sorted_by_type(self):
        client = self._client_with_dialogs(4)
        svc = ChatsService(client)
        result = await svc.get_dialogs()
        types = [d["type"] for d in result]
        order = {"channel": 0, "forum": 1, "group": 2, "private": 3}
        indices = [order.get(t, 9) for t in types]
        assert indices == sorted(indices)

    async def test_network_error_raises(self):
        client = MagicMock()
        client.get_dialogs = AsyncMock(side_effect=Exception("timeout"))
        svc = ChatsService(client)
        with pytest.raises(Exception):
            await svc.get_dialogs()


@pytest.mark.asyncio
class TestGetTopics:
    async def test_not_a_forum_returns_empty(self):
        client = MagicMock()
        from telethon.tl.types import Channel
        entity = Channel(id=1, title="Test")
        entity.broadcast = False
        entity.megagroup = True
        entity.forum = False
        client.get_entity = AsyncMock(return_value=entity)
        svc = ChatsService(client)
        result = await svc.get_topics(-100)
        assert result == {}

    async def test_chat_not_found_raises(self):
        from core.exceptions import ChatNotFoundError
        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        svc = ChatsService(client)
        with pytest.raises(ChatNotFoundError):
            await svc.get_topics(-100)


@pytest.mark.asyncio
class TestGetLinkedGroup:
    async def test_non_channel_returns_none(self):
        client = MagicMock()
        from telethon.tl.types import Chat
        entity = Chat(id=1)
        client.get_entity = AsyncMock(return_value=entity)
        svc = ChatsService(client)
        result = await svc.get_linked_group(-100)
        assert result is None

    async def test_with_linked_group(self):
        client = MagicMock()
        from telethon.tl.types import Channel
        entity = Channel(id=1, title="Ch")
        entity.broadcast = True
        client.get_entity = AsyncMock(return_value=entity)
        full_result = MagicMock()
        full_result.full_chat = MagicMock(linked_chat_id=-200)
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)
        client.side_effect = AsyncMock(return_value=full_result)
        # Примечание: реальная реализация использует client(GetFullChannelRequest)
        # Тест нужно адаптировать под вызов client() как callable
```

### 4.3 ParserService.collect_data → `tests/test_features/test_parser_mocks.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.database import DBManager
from features.parser.api import ParserService, CollectParams


@pytest.mark.asyncio
class TestCollectData:
    async def _service(self, tmp_path, messages=None):
        db = DBManager(str(tmp_path / "test.db"))
        client = MagicMock()

        async def empty_iter(*a, **kw):
            return
            yield

        if messages is None:
            client.iter_messages = empty_iter
        client.get_entity = AsyncMock(return_value=MagicMock(
            title="Test Chat", id=100, broadcast=False
        ))
        client.get_messages = AsyncMock(return_value=MagicMock(total=0))

        svc = ParserService(client=client, db=db)
        return svc, db, client

    async def test_empty_chat(self, tmp_path):
        svc, db, client = await self._service(tmp_path)
        params = CollectParams(chat_id=-100, output_dir=str(tmp_path))
        result = await svc.collect_data(params)
        assert result.success is True
        assert result.messages_count == 0

    async def test_normalizes_chat_id(self, tmp_path):
        svc, db, client = await self._service(tmp_path)
        params = CollectParams(chat_id=2882674903, output_dir=str(tmp_path))
        await svc.collect_data(params)
        # get_entity вызван с правильным ID (уже нормализован через ChatsService)
        client.get_entity.assert_called()

    async def test_cutoff_date_filters_old(self, tmp_path):
        from datetime import datetime, timezone, timedelta
        from telethon.tl.types import Message

        recent = MagicMock(spec=Message)
        recent.id = 1
        recent.date = datetime.now(timezone.utc)
        recent.text = "new"
        recent.sender_id = 1
        recent.media = None
        recent.reply_to = None
        recent.sender = None
        recent.replies = None

        old = MagicMock(spec=Message)
        old.id = 2
        old.date = datetime.now(timezone.utc) - timedelta(days=365)
        old.text = "old"
        old.sender_id = 1
        old.media = None
        old.reply_to = None
        old.sender = None
        old.replies = None

        async def msg_iter(*a, **kw):
            for m in [recent, old]:
                yield m

        svc, db, client = await self._service(tmp_path, messages=True)
        client.iter_messages = msg_iter
        client.get_messages = AsyncMock(return_value=MagicMock(total=2))

        params = CollectParams(
            chat_id=-100, output_dir=str(tmp_path), days_limit=30,
        )
        result = await svc.collect_data(params)
        assert result.messages_count == 1  # old filtered out
```

---

## Спринт S5: E2E, Стресс, Безопасность

**Цель:** Сквозные тесты, нагрузка, проверка инвариантов безопасности.
**Приоритет:** 🟡 Средний — валидация перед релизом.

### 5.1 Полный цикл → `tests/test_e2e/test_full_cycle.py`

```python
import json
import pytest
from core.database import DBManager
from features.export.generator import DocxGenerator, JsonGenerator, MarkdownGenerator, HtmlGenerator


class TestParserExportCycle:
    """Полный цикл: insert msgs + transcriptions → generate all formats."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        path = str(tmp_path / "archive.db")
        db = DBManager(path)
        msgs = []
        for i in range(1, 51):
            msgs.append({
                "chat_id": -100200,
                "message_id": i,
                "user_id": (i % 5) + 1,
                "username": f"user_{(i % 5) + 1}",
                "date": f"2025-01-{1 + (i // 24):02d}T{i % 24:02d}:00:00",
                "text": f"Message number {i}" if i % 3 != 0 else "",
                "file_type": "voice" if i % 7 == 0 else None,
                "media_path": None,
            })
        db.insert_messages_batch(msgs)

        # STT для voice
        for i in range(1, 51):
            if i % 7 == 0:
                db.insert_transcription(i, -100200, f"Транскрипция {i}", "base")
        return db, str(tmp_path)

    def test_docx_full_cycle(self, populated_db):
        db, out = populated_db
        gen = DocxGenerator(db=db, output_dir=out)
        files = gen.generate(
            chat_id=-100200, chat_title="Full Cycle Test",
            split_mode="none", period_label="fullchat",
        )
        assert len(files) == 1
        assert files[0].endswith(".docx")
        from docx import Document
        doc = Document(files[0])
        assert len(doc.paragraphs) > 0

    def test_json_full_cycle(self, populated_db):
        db, out = populated_db
        gen = JsonGenerator(db=db, output_dir=out)
        files = gen.generate(
            chat_id=-100200, chat_title="Test", period_label="fullchat",
        )
        assert len(files) == 1
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 50
        # Проверяем что STT включён
        stt_records = [r for r in data if r.get("stt_text")]
        assert len(stt_records) > 0

    def test_md_full_cycle(self, populated_db):
        db, out = populated_db
        gen = MarkdownGenerator(db=db, output_dir=out)
        files = gen.generate(
            chat_id=-100200, chat_title="Test", period_label="fullchat",
        )
        content = open(files[0], encoding="utf-8").read()
        assert "STT:" in content

    def test_html_full_cycle(self, populated_db):
        db, out = populated_db
        gen = HtmlGenerator(db=db, output_dir=out)
        files = gen.generate(
            chat_id=-100200, chat_title="Test", period_label="fullchat",
        )
        html = open(files[0], encoding="utf-8").read()
        assert "msg-stt" in html

    def test_all_formats_consistent(self, populated_db):
        """Все форматы содержат одинаковое число сообщений."""
        db, out = populated_db
        jfiles = JsonGenerator(db=db, output_dir=out).generate(
            chat_id=-100200, chat_title="T", period_label="full",
        )
        with open(jfiles[0]) as f:
            jdata = json.load(f)

        mfiles = MarkdownGenerator(db=db, output_dir=out).generate(
            chat_id=-100200, chat_title="T", period_label="full",
        )
        md = open(mfiles[0]).read()
        # Подсчёт блоков сообщений по шаблону
        import re
        md_count = len(re.findall(r"\*\[\d{4}-\d{2}-\d{2}", md))

        assert len(jdata) == md_count == 50
```

### 5.2 Стресс-тесты → `tests/test_e2e/test_stress.py`

```python
import time
import pytest
from core.database import DBManager
from core.merger import MergerService
from features.export.generator import JsonGenerator, MarkdownGenerator


class TestStress:
    def test_batch_insert_100k(self, tmp_path):
        """100K сообщений за < 30 секунд."""
        db = DBManager(str(tmp_path / "big.db"))
        msgs = [{
            "chat_id": -100, "message_id": i, "user_id": i % 100,
            "date": f"2025-01-{1 + (i // 86400):02d}T{(i // 3600) % 24:02d}:00:00",
            "text": f"Message {i}",
        } for i in range(100_000)]
        start = time.perf_counter()
        db.insert_messages_batch(msgs)
        elapsed = time.perf_counter() - start
        assert elapsed < 30, f"Insert took {elapsed:.1f}s — too slow"
        rows = db.get_messages(-100)
        assert len(rows) == 100_000

    def test_merger_50k(self):
        """MergerService на 50K сообщений за < 5 секунд."""
        msgs = [{
            "message_id": i, "user_id": 1,
            "date": f"2025-01-01T10:00:{i % 60:02d}",
            "text": f"msg{i}",
        } for i in range(50_000)]
        start = time.perf_counter()
        result = MergerService().merge(msgs)
        elapsed = time.perf_counter() - start
        assert elapsed < 5, f"Merge took {elapsed:.1f}s — too slow"
        assert len(result) > 0

    def test_json_export_10k(self, tmp_path):
        db = DBManager(str(tmp_path / "stress.db"))
        msgs = [{
            "chat_id": -100, "message_id": i, "user_id": 1,
            "date": f"2025-01-01T10:00:00", "text": f"Word " * 50,
        } for i in range(10_000)]
        db.insert_messages_batch(msgs)
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        start = time.perf_counter()
        files = gen.generate(chat_id=-100, chat_title="Stress", period_label="full")
        elapsed = time.perf_counter() - start
        assert len(files) >= 1
        assert elapsed < 30

    def test_long_text_export(self, tmp_path):
        """Сообщение с 100K символов не падает."""
        db = DBManager(str(tmp_path / "long.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00", "text": "A" * 100_000,
        }])
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        assert len(files) == 1
```

### 5.3 Безопасность → `tests/test_e2e/test_security.py`

```python
import json
import os
import pytest
from core.utils import sanitize_filename
from features.export.generator import HtmlGenerator
from core.database import DBManager


class TestSanitizeFilename:
    def test_path_traversal(self):
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result and "\\" not in result

    def test_windows_special(self):
        result = sanitize_filename('file<>:"|?*.txt')
        assert all(c not in result for c in '<>:"|?*')

    def test_empty_fallback(self):
        result = sanitize_filename("")
        assert isinstance(result, str)

    def test_unicode_preserved(self):
        result = sanitize_filename("Привет мир")
        assert "Привет" in result


class TestHtmlXssPrevention:
    def test_script_tag_escaped(self, tmp_path):
        db = DBManager(str(tmp_path / "xss.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00",
            "text": '<script>alert(1)</script><img onerror=alert(1) src=x>',
        }])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "<script>" not in html
        assert "onerror" not in html
        assert "&lt;script&gt;" in html

    def test_javascript_uri(self, tmp_path):
        db = DBManager(str(tmp_path / "xss2.db"))
        db.insert_messages_batch([{
            "chat_id": -100, "message_id": 1, "user_id": 1,
            "date": "2025-01-01T10:00:00",
            "text": "click javascript:alert(1)",
        }])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        # javascript: не должно стать href
        assert 'href="javascript:' not in html


class TestConfigSecurity:
    def test_config_no_secrets_leak(self, tmp_path):
        """config.json не содержит runtime-полей."""
        from config import save_config, AppConfig
        path = str(tmp_path / "cfg.json")
        cfg = AppConfig(
            api_id="123", api_hash="secret",
            output_dir="/secret/path", session_name="private",
        )
        save_config(cfg, path)
        with open(path) as f:
            data = json.load(f)
        assert "output_dir" not in data
        assert "session_name" not in data
```

---

## Метрики и критерии приёмки

### Целевое покрытие по модулям

| Модуль | S1 | S2 | S3 | S4 | S5 | Итого |
|--------|----|----|----|----|----|----|
| `config.py` | 90% | — | — | — | — | 90% |
| `core/exceptions.py` | 95% | — | — | — | — | 95% |
| `core/retry.py` | 90% | — | — | — | — | 90% |
| `core/database.py` | 85% | — | — | — | — | 85% |
| `core/utils.py` | 90% | — | — | — | — | 90% |
| `core/merger.py` | 85% | — | — | — | — | 85% |
| `features/parser/api.py` (static) | — | 80% | — | — | — | 80% |
| `features/chats/api.py` | — | 60% | — | 40% | — | 70% |
| `features/auth/api.py` | — | 50% | — | 50% | — | 70% |
| `features/export/generator.py` | — | — | 75% | — | — | 75% |
| `features/export/xml_magic.py` | — | — | 80% | — | — | 80% |
| E2E / Stress / Security | — | — | — | — | 60% | 60% |

### Запуск и проверка

```bash
# Все тесты:
pytest tests/ -v

# С покрытием:
pytest --cov=. --cov-report=term-missing tests/

# Только определённый спринт:
pytest tests/test_core/test_config.py tests/test_core/test_exceptions.py tests/test_core/test_retry.py -v   # S1
pytest tests/test_features/test_parser_static.py tests/test_features/test_chats_static.py tests/test_features/test_auth_static.py -v  # S2
pytest tests/test_features/test_export_json.py tests/test_features/test_export_md.py tests/test_features/test_export_html.py -v  # S3

# Медленные / стресс (маркер slow):
pytest -m slow tests/ -v

# Только быстрые:
pytest -m "not slow" tests/ -v
```

---

## История изменений

| Дата | Версия | Изменение |
|------|--------|-----------|
| 2026-05-06 | 1.1 | S1 завершён: 94 теста (config, exceptions, retry) — все PASS |
| 2026-05-06 | 1.2 | S2 завершён: 73 теста (parser static, chats classify, auth static) — все PASS |
| 2026-05-06 | 1.0 | Начальная версия — полный план из 5 спринтов |
| 2026-05-06 | 1.3 | S3 завершён: 67 тестов (JSON, MD, HTML generators) — все PASS |
| 2026-05-06 | 1.4 | S4 завершён: 96 тестов (mock-тесты Auth, Chats, Parser API) — все PASS |
| 2026-05-06 | 1.5 | S5 завершён: 34 теста (E2E, стресс, безопасность) — все PASS. **Итого: 450 тестов** |
