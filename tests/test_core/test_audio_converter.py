"""
tests/test_core/test_audio_converter.py

Тесты: AudioConverter.convert_to_wav / cleanup.
Все внешние вызовы (subprocess, os, tempfile) мокаются.
"""
import os
import subprocess

import pytest
from unittest.mock import patch, MagicMock, call

from core.stt.audio_converter import AudioConverter
from core.exceptions import STTError


class TestConvertToWavSuccess:
    """Успешная конвертация в WAV."""

    @patch("core.stt.audio_converter.os.path.getsize", return_value=1024)
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    @patch("core.stt.audio_converter.subprocess.run")
    def test_basic_returns_output_path(self, mock_run, mock_exists, mock_size):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result

        path = AudioConverter.convert_to_wav("/in.ogg", "/out.wav")
        assert path == "/out.wav"

    @patch("core.stt.audio_converter.os.path.getsize", return_value=1024)
    @patch("core.stt.audio_converter.os.path.exists", side_effect=lambda p: p == "/in.ogg" or p.startswith("/tmp"))
    @patch("core.stt.audio_converter.subprocess.run")
    @patch("core.stt.audio_converter.tempfile.mkstemp", return_value=(99, "/tmp/audio.wav"))
    @patch("core.stt.audio_converter.os.close")
    def test_auto_temp_file(self, mock_close, mock_mkstemp, mock_run, mock_exists, mock_size):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result

        path = AudioConverter.convert_to_wav("/in.ogg")
        mock_mkstemp.assert_called_once_with(suffix=".wav")
        mock_close.assert_called_once_with(99)
        assert path == "/tmp/audio.wav"

    @patch("core.stt.audio_converter.os.path.getsize", return_value=1024)
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    @patch("core.stt.audio_converter.subprocess.run")
    def test_ffmpeg_command_structure(self, mock_run, mock_exists, mock_size):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result

        AudioConverter.convert_to_wav("/in.ogg", "/out.wav")
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert "/in.ogg" in cmd
        assert "-ar" in cmd and "16000" in cmd
        assert "-ac" in cmd and "1" in cmd
        assert "-acodec" in cmd and "pcm_s16le" in cmd
        assert "-y" in cmd
        assert "/out.wav" in cmd

    @patch("core.stt.audio_converter.os.path.getsize", return_value=1024)
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    @patch("core.stt.audio_converter.subprocess.run")
    def test_subprocess_timeout_120(self, mock_run, mock_exists, mock_size):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result

        AudioConverter.convert_to_wav("/in.ogg", "/out.wav")
        assert mock_run.call_args[1]["timeout"] == 120

    @patch("core.stt.audio_converter.os.path.getsize", return_value=1024)
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    @patch("core.stt.audio_converter.subprocess.run")
    def test_custom_output_path_no_tempfile(self, mock_run, mock_exists, mock_size):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        mock_run.return_value = result

        with patch("core.stt.audio_converter.tempfile.mkstemp") as mock_tmp:
            AudioConverter.convert_to_wav("/in.ogg", "/custom/path.wav")
            mock_tmp.assert_not_called()


class TestConvertToWavErrors:
    """Ошибки конвертации."""

    def test_missing_input_file_raises_stt_error(self):
        with patch("core.stt.audio_converter.os.path.exists", return_value=False):
            with pytest.raises(STTError, match="не найден"):
                AudioConverter.convert_to_wav("/missing.ogg")

    def test_missing_input_sets_media_path(self):
        with patch("core.stt.audio_converter.os.path.exists", return_value=False):
            with pytest.raises(STTError) as exc_info:
                AudioConverter.convert_to_wav("/missing.ogg")
            assert exc_info.value.media_path == "/missing.ogg"

    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_ffmpeg_not_found_raises_stt_error(self, mock_exists):
        with patch("core.stt.audio_converter.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(STTError, match="FFmpeg не найден"):
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")

    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_ffmpeg_not_found_sets_media_path(self, mock_exists):
        with patch("core.stt.audio_converter.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(STTError) as exc_info:
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")
            assert exc_info.value.media_path == "/in.ogg"

    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_ffmpeg_timeout_raises_stt_error(self, mock_exists):
        with patch(
            "core.stt.audio_converter.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120),
        ):
            with pytest.raises(STTError, match="120"):
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")

    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_ffmpeg_bad_return_code(self, mock_exists):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "Error details here"
        with patch("core.stt.audio_converter.subprocess.run", return_value=result):
            with pytest.raises(STTError, match="Error details here"):
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")

    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_stderr_truncated_at_300(self, mock_exists):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "X" * 500
        with patch("core.stt.audio_converter.subprocess.run", return_value=result):
            with pytest.raises(STTError) as exc_info:
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")
            err_msg = str(exc_info.value)
            assert len(err_msg) < 500

    @patch("core.stt.audio_converter.os.path.exists", side_effect=lambda p: p == "/in.ogg")
    def test_empty_output_raises_stt_error(self, mock_exists):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        with patch("core.stt.audio_converter.subprocess.run", return_value=result):
            with pytest.raises(STTError, match="пустой"):
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")

    @patch("core.stt.audio_converter.os.path.getsize", return_value=0)
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_zero_size_output_raises_stt_error(self, mock_exists, mock_size):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        with patch("core.stt.audio_converter.subprocess.run", return_value=result):
            with pytest.raises(STTError, match="пустой"):
                AudioConverter.convert_to_wav("/in.ogg", "/out.wav")

    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_all_errors_have_media_path(self, mock_exists):
        """Все ошибки конвертации содержат media_path."""
        with patch("core.stt.audio_converter.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(STTError) as exc_info:
                AudioConverter.convert_to_wav("/test.ogg", "/out.wav")
            assert exc_info.value.media_path == "/test.ogg"


class TestCleanup:
    """Удаление временного WAV-файла."""

    @patch("core.stt.audio_converter.os.remove")
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_removes_existing_file(self, mock_exists, mock_remove):
        AudioConverter.cleanup("/tmp/audio.wav")
        mock_remove.assert_called_once_with("/tmp/audio.wav")

    def test_noop_for_empty_path(self):
        AudioConverter.cleanup("")
        # Не должно быть исключений

    def test_noop_for_none(self):
        AudioConverter.cleanup(None)

    @patch("core.stt.audio_converter.os.path.exists", return_value=False)
    def test_noop_for_nonexistent(self, mock_exists):
        with patch("core.stt.audio_converter.os.remove") as mock_remove:
            AudioConverter.cleanup("/nonexistent.wav")
            mock_remove.assert_not_called()

    @patch("core.stt.audio_converter.os.remove", side_effect=OSError("permission denied"))
    @patch("core.stt.audio_converter.os.path.exists", return_value=True)
    def test_swallows_os_error(self, mock_exists, mock_remove):
        AudioConverter.cleanup("/locked.wav")
        # OSError перехватывается, не пробрасывается
