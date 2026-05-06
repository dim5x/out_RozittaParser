"""
tests/test_core/test_exceptions.py

Тесты: полная иерархия исключений — наследование, атрибуты, строковое представление.
"""
import pytest
from core.exceptions import (
    RozittaError,
    ConfigError,
    AuthError,
    SessionExpiredError,
    PhoneCodeInvalidError,
    DatabaseError,
    DatabaseLockedError,
    TelegramError,
    ChatNotFoundError,
    ForumTopicsError,
    FloodWaitError,
    LinkedGroupNotFoundError,
    MediaDownloadError,
    STTError,
    ExportError,
    DocxGenerationError,
    EmptyDataError,
)


# ──────────────────────────────────────────────────────────────────────────────
# Иерархия наследования
# ──────────────────────────────────────────────────────────────────────────────

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

    @pytest.mark.parametrize("cls,parent", [
        (ConfigError, RozittaError),
        (AuthError, RozittaError),
        (SessionExpiredError, AuthError),
        (PhoneCodeInvalidError, AuthError),
        (DatabaseError, RozittaError),
        (DatabaseLockedError, DatabaseError),
        (TelegramError, RozittaError),
        (ChatNotFoundError, TelegramError),
        (ForumTopicsError, TelegramError),
        (FloodWaitError, TelegramError),
        (LinkedGroupNotFoundError, TelegramError),
        (MediaDownloadError, TelegramError),
        (STTError, RozittaError),
        (ExportError, RozittaError),
        (DocxGenerationError, ExportError),
        (EmptyDataError, ExportError),
    ])
    def test_direct_parent(self, cls, parent):
        assert cls in parent.__subclasses__() or issubclass(cls, parent)

    def test_catch_all_via_base(self):
        errors = [
            ConfigError("cfg"),
            ChatNotFoundError(123),
            FloodWaitError(60),
            EmptyDataError(chat_id=-100),
        ]
        for err in errors:
            with pytest.raises(RozittaError):
                raise err


# ──────────────────────────────────────────────────────────────────────────────
# Строковое представление (базовые)
# ──────────────────────────────────────────────────────────────────────────────

class TestStrRepresentation:
    def test_rozitta_error_with_message(self):
        e = RozittaError("test msg")
        assert str(e) == "test msg"

    def test_rozitta_error_without_message(self):
        e = RozittaError()
        assert str(e) == "RozittaError"

    def test_config_error_message(self):
        e = ConfigError("bad config")
        assert str(e) == "bad config"

    def test_auth_error_message(self):
        e = AuthError("auth failed")
        assert str(e) == "auth failed"


# ──────────────────────────────────────────────────────────────────────────────
# Специальные атрибуты
# ──────────────────────────────────────────────────────────────────────────────

class TestSpecialAttributes:
    def test_chat_not_found_stores_id(self):
        e = ChatNotFoundError(-100123)
        assert e.chat_id == -100123
        assert "-100123" in str(e)

    def test_chat_not_found_custom_message(self):
        e = ChatNotFoundError(-100, message="Нет доступа")
        assert e.chat_id == -100
        assert "Нет доступа" in str(e)

    def test_forum_topics_stores_id(self):
        e = ForumTopicsError(-200)
        assert e.chat_id == -200
        assert "-200" in str(e)

    def test_flood_wait_stores_seconds(self):
        e = FloodWaitError(300)
        assert e.seconds == 300
        assert "300" in str(e)

    def test_flood_wait_custom_message(self):
        e = FloodWaitError(60, message="Подождите")
        assert e.seconds == 60
        assert "Подождите" in str(e)

    def test_linked_group_stores_channel_id(self):
        e = LinkedGroupNotFoundError(channel_id=-100200)
        assert e.channel_id == -100200
        assert "-100200" in str(e)

    def test_media_download_error_fields(self):
        e = MediaDownloadError(message_id=42)
        assert e.message_id == 42
        assert "42" in str(e)
        assert e.original is None

    def test_media_download_error_with_original(self):
        orig = OSError("network timeout")
        e = MediaDownloadError(message_id=7, message="Сбой", original=orig)
        assert e.original is orig
        result = str(e)
        assert "Сбой" in result
        assert "network timeout" in result

    def test_media_download_error_without_original(self):
        e = MediaDownloadError(message_id=42, message="Ошибка #42")
        assert str(e) == "Ошибка #42"

    def test_database_error_with_original(self):
        original = OSError("disk full")
        e = DatabaseError("write failed", original=original)
        assert e.original is original
        assert "disk full" in str(e)

    def test_database_error_without_original(self):
        e = DatabaseError("simple error")
        assert e.original is None
        assert str(e) == "simple error"

    def test_docx_gen_error_stores_path(self):
        e = DocxGenerationError(file_path="/out/a.docx")
        assert e.file_path == "/out/a.docx"

    def test_docx_gen_error_with_original(self):
        orig = RuntimeError("xml fail")
        e = DocxGenerationError(file_path="x.docx", message="bad", original=orig)
        result = str(e)
        assert "bad" in result
        assert "xml fail" in result

    def test_docx_gen_error_without_original(self):
        e = DocxGenerationError(file_path="x.docx", message="Ошибка")
        assert str(e) == "Ошибка"

    def test_empty_data_with_topic(self):
        e = EmptyDataError(chat_id=-100, topic_id=5)
        assert e.chat_id == -100
        assert e.topic_id == 5
        assert "5" in str(e)

    def test_empty_data_without_topic(self):
        e = EmptyDataError(chat_id=-100)
        assert e.topic_id is None
        assert "-100" in str(e)

    def test_empty_data_custom_message(self):
        e = EmptyDataError(chat_id=-100, message="Пусто")
        assert "Пусто" in str(e)

    def test_stt_error_fields(self):
        e = STTError("fail", media_path="/a.ogg", message_id=7)
        assert e.media_path == "/a.ogg"
        assert e.message_id == 7
        assert str(e) == "fail"

    def test_stt_error_defaults(self):
        e = STTError()
        assert e.media_path is None
        assert e.message_id is None

    def test_session_expired_error(self):
        e = SessionExpiredError("Сессия устарела")
        assert isinstance(e, AuthError)
        assert "устарела" in str(e)

    def test_phone_code_invalid_error(self):
        e = PhoneCodeInvalidError("Неверный код")
        assert isinstance(e, AuthError)
        assert "Неверный код" in str(e)

    def test_database_locked_error_is_database_error(self):
        e = DatabaseLockedError("БД заблокирована")
        assert isinstance(e, DatabaseError)
        assert isinstance(e, RozittaError)
