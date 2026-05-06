"""
tests/test_core/test_whisper_manager.py

Тесты: WhisperManager — singleton, is_available, install, transcribe, _postprocess, unload.
Все внешние зависимости мокаются.
"""
import pytest
from unittest.mock import patch, MagicMock

from core.stt.whisper_manager import WhisperManager
from core.exceptions import STTError


@pytest.fixture(autouse=True)
def reset_singleton():
    """Сброс singleton между тестами."""
    WhisperManager._instance = None
    yield
    WhisperManager._instance = None


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestIsAvailable:
    @patch("importlib.util.find_spec", return_value=MagicMock())
    def test_available_when_spec_found(self, mock_spec):
        assert WhisperManager.is_available() is True

    @patch("importlib.util.find_spec", return_value=None)
    def test_not_available_when_spec_none(self, mock_spec):
        assert WhisperManager.is_available() is False

    @patch("importlib.util.find_spec", side_effect=ImportError)
    def test_not_available_on_import_error(self, mock_spec):
        assert WhisperManager.is_available() is False

    @patch("importlib.util.find_spec", side_effect=AttributeError)
    def test_not_available_on_attr_error(self, mock_spec):
        assert WhisperManager.is_available() is False


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

class TestInstall:
    @patch("subprocess.run")
    def test_install_success(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        mock_run.return_value = result
        assert WhisperManager.install() is True

    @patch("subprocess.run")
    def test_install_failure_returncode(self, mock_run):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "error"
        mock_run.return_value = result
        assert WhisperManager.install() is False

    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("pip", 300))
    def test_install_timeout(self, mock_run):
        assert WhisperManager.install() is False

    @patch("subprocess.run")
    def test_frozen_exe_returns_false(self, mock_run):
        import sys
        old = getattr(sys, "frozen", None)
        sys.frozen = True
        try:
            assert WhisperManager.install() is False
            mock_run.assert_not_called()
        finally:
            if old is None:
                delattr(sys, "frozen")
            else:
                sys.frozen = old

    @patch("subprocess.run")
    def test_log_callback_called(self, mock_run):
        result = MagicMock()
        result.returncode = 0
        mock_run.return_value = result
        logs = []
        WhisperManager.install(log_callback=logs.append)
        assert len(logs) > 0
        assert any("установ" in l.lower() or "whisper" in l.lower() for l in logs)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_instance_returns_same_object(self):
        a = WhisperManager.instance()
        b = WhisperManager.instance()
        assert a is b

    def test_instance_creates_new_after_reset(self):
        a = WhisperManager.instance()
        WhisperManager._instance = None
        b = WhisperManager.instance()
        assert a is not b


# ---------------------------------------------------------------------------
# _postprocess (regex, no mocking)
# ---------------------------------------------------------------------------

class TestPostprocess:
    def test_empty_string(self):
        assert WhisperManager._postprocess("") == ""

    def test_none_input(self):
        assert WhisperManager._postprocess(None) is None

    def test_multiple_spaces_normalized(self):
        assert WhisperManager._postprocess("hello   world") == "hello world"

    def test_leading_trailing_spaces_stripped(self):
        assert WhisperManager._postprocess("  hello  ") == "hello"

    def test_word_repeat_removed(self):
        result = WhisperManager._postprocess("спасибо спасибо спасибо")
        assert result == "спасибо"

    def test_word_repeat_case_insensitive(self):
        result = WhisperManager._postprocess("Да да да")
        assert result.strip() == "Да"

    def test_two_repeats_kept(self):
        result = WhisperManager._postprocess("да да")
        assert "да да" in result

    def test_phrase_repeat_removed(self):
        result = WhisperManager._postprocess(
            "как дела как дела как дела"
        )
        assert result.count("как дела") == 1

    def test_combined_normalization(self):
        result = WhisperManager._postprocess(
            "  спасибо   спасибо   спасибо  "
        )
        assert result == "спасибо"


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------

class TestTranscribe:
    def _make_manager(self):
        mgr = WhisperManager()
        mgr._model = MagicMock()
        return mgr

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model")
    def test_transcribe_success(self, mock_ensure):
        mgr = self._make_manager()
        seg1 = MagicMock()
        seg1.text = "  Привет мир  "
        seg2 = MagicMock()
        seg2.text = "  Как дела  "
        info = MagicMock()
        info.language = "ru"
        info.language_probability = 0.99
        mgr._model.transcribe.return_value = ([seg1, seg2], info)

        result = mgr.transcribe("/voice.ogg")
        assert "Привет" in result
        assert "Как дела" in result

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model")
    def test_transcribe_empty_result(self, mock_ensure):
        mgr = self._make_manager()
        info = MagicMock()
        info.language = "ru"
        info.language_probability = 0.0
        mgr._model.transcribe.return_value = ([], info)

        result = mgr.transcribe("/silence.ogg")
        assert result == ""

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model",
           side_effect=STTError("faster-whisper не установлен"))
    def test_import_error_raises_stt_error(self, mock_ensure):
        mgr = WhisperManager()
        with pytest.raises(STTError, match="faster-whisper"):
            mgr.transcribe("/voice.ogg")

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model")
    def test_generic_exception_wrapped(self, mock_ensure):
        mgr = self._make_manager()
        mgr._model.transcribe.side_effect = RuntimeError("boom")
        with pytest.raises(STTError, match="Ошибка транскрибации"):
            mgr.transcribe("/voice.ogg")

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model")
    def test_uses_initial_prompt_for_ru(self, mock_ensure):
        mgr = self._make_manager()
        info = MagicMock()
        info.language = "ru"
        info.language_probability = 0.99
        mgr._model.transcribe.return_value = ([], info)

        mgr.transcribe("/voice.ogg", language="ru")
        call_kwargs = mgr._model.transcribe.call_args[1]
        assert call_kwargs["initial_prompt"] is not None
        assert "русском" in call_kwargs["initial_prompt"]

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model")
    def test_no_prompt_for_unknown_language(self, mock_ensure):
        mgr = self._make_manager()
        info = MagicMock()
        info.language = "xx"
        info.language_probability = 0.5
        mgr._model.transcribe.return_value = ([], info)

        mgr.transcribe("/voice.ogg", language="xx")
        call_kwargs = mgr._model.transcribe.call_args[1]
        assert call_kwargs["initial_prompt"] is None

    @patch("core.stt.whisper_manager.WhisperManager._ensure_model")
    def test_transcribe_stt_error_has_media_path(self, mock_ensure):
        mgr = self._make_manager()
        mgr._model.transcribe.side_effect = RuntimeError("fail")
        with pytest.raises(STTError) as exc_info:
            mgr.transcribe("/my_voice.ogg")
        assert exc_info.value.media_path == "/my_voice.ogg"


# ---------------------------------------------------------------------------
# unload
# ---------------------------------------------------------------------------

class TestUnload:
    def test_noop_without_force(self):
        mgr = WhisperManager()
        mgr._model = MagicMock()
        mgr._model_size = "small"
        mgr.unload(force=False)
        assert mgr._model is not None
        assert mgr._model_size == "small"

    def test_clears_with_force(self):
        mgr = WhisperManager()
        mgr._model = MagicMock()
        mgr._model_size = "small"
        mgr.unload(force=True)
        assert mgr._model is None
        assert mgr._model_size is None
