"""
tests/test_e2e/test_security.py

Безопасность: sanitize_filename, HTML XSS, конфигурация.
"""
import json

from core.database import DBManager
from core.utils import sanitize_filename
from features.export.generator import HtmlGenerator


def _msg(text, chat_id=-100, msg_id=1):
    return {
        "chat_id": chat_id, "message_id": msg_id, "topic_id": None,
        "user_id": 1, "username": "user_1", "date": "2025-01-01T10:00:00",
        "text": text, "media_path": None, "file_type": None,
        "file_size": None, "reply_to_msg_id": None, "post_id": None,
        "is_comment": 0, "from_linked_group": 0,
    }


class TestSanitizeFilenameSecurity:
    def test_path_traversal_no_separators(self):
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result

    def test_windows_special_chars(self):
        result = sanitize_filename('file<>:"|?*.txt')
        for c in '<>:"|?*':
            assert c not in result

    def test_empty_fallback(self):
        result = sanitize_filename("")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_none_fallback(self):
        result = sanitize_filename(None)
        assert result == "chat"

    def test_unicode_preserved(self):
        result = sanitize_filename("Привет мир")
        assert "Привет" in result

    def test_only_dots_stripped(self):
        result = sanitize_filename("...")
        assert result == "chat"


class TestHtmlXssPrevention:
    def test_script_tag_escaped(self, tmp_path):
        db = DBManager(str(tmp_path / "xss.db"))
        db.insert_messages_batch([_msg('<script>alert(1)</script>')])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "&lt;script&gt;" in html
        assert 'msg-text">&lt;script&gt;' in html

    def test_img_onerror_escaped(self, tmp_path):
        db = DBManager(str(tmp_path / "xss2.db"))
        db.insert_messages_batch([_msg('<img onerror=alert(1) src=x>')])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "&lt;" in html
        assert "&gt;" in html

    def test_javascript_uri_in_text(self, tmp_path):
        db = DBManager(str(tmp_path / "xss3.db"))
        db.insert_messages_batch([_msg("click javascript:alert(1)")])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert 'href="javascript:' not in html


class TestConfigSecurity:
    def test_config_no_runtime_fields(self, tmp_path):
        from config import AppConfig, save_config

        path = str(tmp_path / "cfg.json")
        cfg = AppConfig(
            api_id="123", api_hash="secret_hash",
            output_dir="/secret/path", session_name="private_session",
        )
        save_config(cfg, path)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert "output_dir" not in data
        assert "session_name" not in data

    def test_config_has_required_fields(self, tmp_path):
        from config import AppConfig, save_config

        path = str(tmp_path / "cfg.json")
        cfg = AppConfig(api_id="123", api_hash="abc", phone="+79990001111")
        save_config(cfg, path)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["api_id"] == "123"
        assert data["api_hash"] == "abc"
        assert data["phone"] == "+79990001111"

    def test_config_api_hash_not_in_session(self, tmp_path):
        from config import AppConfig, save_config

        path = str(tmp_path / "cfg2.json")
        cfg = AppConfig(api_id="999", api_hash="my_secret_hash_1234567890abcdef")
        save_config(cfg, path)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["api_hash"] == "my_secret_hash_1234567890abcdef"
        assert "session_path" not in data
