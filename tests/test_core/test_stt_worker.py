"""
tests/test_core/test_stt_worker.py

Тесты: STTWorker — init, _transcribe_all логика, run() error handling.
Требует QApplication (PySide6) для работы QThread signals.
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from core.exceptions import STTError


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _candidate(msg_id, media_path="/voice.ogg", file_type="voice"):
    return {
        "message_id": msg_id,
        "media_path": media_path,
        "file_type": file_type,
    }


def _make_worker(db_path="/db.db", chat_id=-100, **kwargs):
    from core.stt.worker import STTWorker
    w = STTWorker(db_path, chat_id, **kwargs)
    return w


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestSTTWorkerInit:
    def test_default_parameters(self, qapp):
        w = _make_worker()
        assert w._model_size == "small"
        assert w._language == "ru"

    def test_custom_parameters(self, qapp):
        w = _make_worker(model_size="base", language="en")
        assert w._model_size == "base"
        assert w._language == "en"


# ---------------------------------------------------------------------------
# _transcribe_all — WhisperManager not available
# ---------------------------------------------------------------------------

class TestTranscribeAllNotAvailable:
    def test_install_succeeds_raises_restart(self, qapp):
        w = _make_worker()
        with patch("core.stt.worker.WhisperManager.is_available", return_value=False):
            with patch("core.stt.worker.WhisperManager.install", return_value=True):
                with pytest.raises(STTError, match="перезапустите"):
                    w._transcribe_all()

    def test_install_fails_raises_not_installed(self, qapp):
        w = _make_worker()
        with patch("core.stt.worker.WhisperManager.is_available", return_value=False):
            with patch("core.stt.worker.WhisperManager.install", return_value=False):
                with pytest.raises(STTError, match="не установлен"):
                    w._transcribe_all()

    def test_log_messages_emitted(self, qapp):
        w = _make_worker()
        with patch.object(w, "log_message") as mock_log:
            with patch("core.stt.worker.WhisperManager.is_available", return_value=False):
                with patch("core.stt.worker.WhisperManager.install", return_value=False):
                    try:
                        w._transcribe_all()
                    except STTError:
                        pass
            assert mock_log.emit.call_count > 0


# ---------------------------------------------------------------------------
# _transcribe_all — no candidates
# ---------------------------------------------------------------------------

class TestTranscribeAllNoCandidates:
    def test_emits_progress_100(self, qapp):
        w = _make_worker()
        with patch("core.stt.worker.WhisperManager.is_available", return_value=True):
            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = []
                MockDB.return_value = mock_db
                with patch.object(w, "progress") as mock_progress:
                    w._transcribe_all()
                    mock_progress.emit.assert_called_with(100)

    def test_emits_log_no_candidates(self, qapp):
        w = _make_worker()
        with patch("core.stt.worker.WhisperManager.is_available", return_value=True):
            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = []
                MockDB.return_value = mock_db
                with patch.object(w, "log_message") as mock_log:
                    w._transcribe_all()
                    log_calls = [c[0][0] for c in mock_log.emit.call_args_list]
                    assert any("нет голосовых" in msg for msg in log_calls)


# ---------------------------------------------------------------------------
# _transcribe_all — with candidates
# ---------------------------------------------------------------------------

class TestTranscribeAllWithCandidates:
    def test_success_saves_to_db(self, qapp):
        w = _make_worker()
        mgr = MagicMock()
        mgr.transcribe.return_value = "Привет мир"

        with patch("core.stt.worker.WhisperManager") as MockWM:
            MockWM.is_available.return_value = True
            MockWM.instance.return_value = mgr

            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = [_candidate(1)]
                MockDB.return_value = mock_db

                with patch.object(w, "log_message"), patch.object(w, "progress"), patch.object(w, "transcription_ready"):
                    w._transcribe_all()

                mock_db.insert_transcription.assert_called_once_with(
                    message_id=1, peer_id=-100, text="Привет мир", model_type="small",
                )

    def test_success_emits_ready(self, qapp):
        w = _make_worker()
        mgr = MagicMock()
        mgr.transcribe.return_value = "Текст"

        with patch("core.stt.worker.WhisperManager") as MockWM:
            MockWM.is_available.return_value = True
            MockWM.instance.return_value = mgr

            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = [_candidate(42)]
                MockDB.return_value = mock_db

                with patch.object(w, "log_message"), patch.object(w, "progress"):
                    with patch.object(w, "transcription_ready") as mock_ready:
                        w._transcribe_all()
                        mock_ready.emit.assert_called_once_with(42, "Текст")

    def test_empty_text_no_save(self, qapp):
        w = _make_worker()
        mgr = MagicMock()
        mgr.transcribe.return_value = ""

        with patch("core.stt.worker.WhisperManager") as MockWM:
            MockWM.is_available.return_value = True
            MockWM.instance.return_value = mgr

            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = [_candidate(1)]
                MockDB.return_value = mock_db

                with patch.object(w, "log_message") as mock_log, patch.object(w, "progress"):
                    w._transcribe_all()

                mock_db.insert_transcription.assert_not_called()
                log_calls = [c[0][0] for c in mock_log.emit.call_args_list]
                assert any("тишина" in msg for msg in log_calls)

    def test_error_continues(self, qapp):
        w = _make_worker()
        mgr = MagicMock()
        mgr.transcribe.side_effect = [STTError("fail"), "ok"]

        with patch("core.stt.worker.WhisperManager") as MockWM:
            MockWM.is_available.return_value = True
            MockWM.instance.return_value = mgr

            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = [_candidate(1), _candidate(2)]
                MockDB.return_value = mock_db

                with patch.object(w, "log_message"), patch.object(w, "progress"):
                    with patch.object(w, "transcription_ready") as mock_ready:
                        w._transcribe_all()

                assert mgr.transcribe.call_count == 2
                assert mock_ready.emit.call_count == 1

    def test_progress_tracking(self, qapp):
        w = _make_worker()
        mgr = MagicMock()
        mgr.transcribe.return_value = "text"

        with patch("core.stt.worker.WhisperManager") as MockWM:
            MockWM.is_available.return_value = True
            MockWM.instance.return_value = mgr

            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = [_candidate(i) for i in range(1, 4)]
                MockDB.return_value = mock_db

                with patch.object(w, "log_message"):
                    with patch.object(w, "progress") as mock_progress:
                        w._transcribe_all()

                progress_values = [c[0][0] for c in mock_progress.emit.call_args_list]
                assert 5 in progress_values
                assert 100 in progress_values

    def test_summary_log(self, qapp):
        w = _make_worker()
        mgr = MagicMock()
        mgr.transcribe.return_value = "text"

        with patch("core.stt.worker.WhisperManager") as MockWM:
            MockWM.is_available.return_value = True
            MockWM.instance.return_value = mgr

            with patch("core.stt.worker.DBManager") as MockDB:
                mock_db = MagicMock()
                mock_db.__enter__ = MagicMock(return_value=mock_db)
                mock_db.__exit__ = MagicMock(return_value=False)
                mock_db.get_stt_candidates.return_value = [_candidate(1)]
                MockDB.return_value = mock_db

                with patch.object(w, "log_message") as mock_log:
                    with patch.object(w, "progress"):
                        w._transcribe_all()

                log_calls = [c[0][0] for c in mock_log.emit.call_args_list]
                assert any("распознано" in msg for msg in log_calls)


# ---------------------------------------------------------------------------
# run() — error propagation
# ---------------------------------------------------------------------------

class TestWorkerRunMethod:
    def test_stt_error_emits_error_signal(self, qapp):
        w = _make_worker()
        with patch.object(w, "_transcribe_all", side_effect=STTError("stt fail")):
            with patch("core.stt.worker.WhisperManager") as MockWM:
                MockWM.instance.return_value.unload = MagicMock()
                with patch.object(w, "error") as mock_error, patch.object(w, "finished") as mock_finished:
                    w.run()
                    mock_error.emit.assert_called_once()
                    assert "stt fail" in mock_error.emit.call_args[0][0]
                    mock_finished.emit.assert_called_once()

    def test_generic_exception_emits_error(self, qapp):
        w = _make_worker()
        with patch.object(w, "_transcribe_all", side_effect=RuntimeError("unexpected")):
            with patch("core.stt.worker.WhisperManager") as MockWM:
                MockWM.instance.return_value.unload = MagicMock()
                with patch.object(w, "error") as mock_error, patch.object(w, "finished"):
                    w.run()
                    assert "неожиданная" in mock_error.emit.call_args[0][0]

    def test_finished_always_emitted(self, qapp):
        w = _make_worker()
        with patch.object(w, "_transcribe_all", side_effect=STTError("err")):
            with patch("core.stt.worker.WhisperManager") as MockWM:
                MockWM.instance.return_value.unload = MagicMock()
                with patch.object(w, "error"), patch.object(w, "finished") as mock_finished:
                    w.run()
                    mock_finished.emit.assert_called_once()

    def test_unload_called_after_run(self, qapp):
        w = _make_worker()
        mock_unload = MagicMock()

        with patch.object(w, "_transcribe_all"):
            with patch("core.stt.worker.WhisperManager") as MockWM:
                MockWM.instance.return_value.unload = mock_unload
                with patch.object(w, "error"), patch.object(w, "finished"):
                    w.run()

        mock_unload.assert_called_once_with(force=False)
