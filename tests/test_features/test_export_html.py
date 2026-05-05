"""
tests/test_features/test_export_html.py

Тесты: HtmlGenerator — генерация HTML-архива.
"""
import os
import pytest
from core.database import DBManager
from core.exceptions import EmptyDataError
from features.export.generator import HtmlGenerator


def _msg(chat_id=-100, msg_id=1, user_id=1, username="user1",
         date="2025-01-01T10:00:00", text="hello", **kw):
    """Фабрика сообщения со всеми обязательными полями."""
    return {
        "chat_id": chat_id, "message_id": msg_id, "user_id": user_id,
        "username": username, "date": date, "text": text,
        "topic_id": None, "media_path": None, "file_type": None,
        "file_size": None, "reply_to_msg_id": None, "post_id": None,
        "is_comment": 0, "from_linked_group": 0,
        **kw,
    }


def _db_with_msgs(tmp_path, msgs):
    db = DBManager(str(tmp_path / "test.db"))
    db.insert_messages_batch(msgs)
    return db


class TestHtmlBasic:
    def test_generates_html_file(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(username="Bob", date="2025-03-01T09:00:00", text="Test message")])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="Chat", period_label="full")
        assert len(files) == 1
        assert files[0].endswith(".html")

    def test_html_structure(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(username="Bob", date="2025-03-01T09:00:00", text="Test message")])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="Chat", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "<!DOCTYPE html>" in html
        assert 'id="msg_1"' in html
        assert "Bob" in html
        assert "Test message" in html

    def test_title_in_header(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg()])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="My Channel", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "My Channel" in html

    def test_message_count_in_stats(self, tmp_path):
        msgs = [_msg(msg_id=i, text=f"msg{i}", date=f"2025-01-01T10:{i:02d}:00") for i in range(1, 4)]
        db = _db_with_msgs(tmp_path, msgs)
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "3 сообщений" in html

    def test_empty_db_raises(self, tmp_path):
        db = DBManager(str(tmp_path / "empty.db"))
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        with pytest.raises(EmptyDataError):
            gen.generate(chat_id=-100, chat_title="T", period_label="full")


class TestHtmlReplyLinks:
    def test_reply_has_link(self, tmp_path):
        db = _db_with_msgs(tmp_path, [
            _msg(msg_id=1, text="Original"),
            _msg(msg_id=2, text="Reply", reply_to_msg_id=1),
        ])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "#msg_1" in html

    def test_reply_has_depth_class(self, tmp_path):
        db = _db_with_msgs(tmp_path, [
            _msg(msg_id=1, text="Original"),
            _msg(msg_id=2, text="Reply", reply_to_msg_id=1),
        ])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "depth-1" in html

    def test_no_reply_depth_zero(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(text="Standalone")])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "depth-0" in html


class TestHtmlXss:
    def test_script_escaped(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(text='<script>alert("xss")</script>')])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        # HTML template has its own <script> tags — check message area only
        assert "&lt;script&gt;" in html
        # No unescaped script tag in msg-text div
        assert 'msg-text">&lt;script&gt;' in html

    def test_html_entities_escaped(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(text='<img src=x onerror=alert(1)>')])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "&lt;" in html


class TestHtmlStt:
    def test_stt_block_present(self, tmp_path):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([_msg(text="", file_type="voice")])
        db.insert_transcription(1, -100, "Transcribed text", "base")
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "Transcribed text" in html
        assert "msg-stt" in html


class TestHtmlAiSplit:
    def test_ai_split_creates_multiple_files(self, tmp_path):
        msgs = [_msg(msg_id=i, text=f"{'word ' * 20}", date=f"2025-01-01T10:{i:02d}:00")
                for i in range(50)]
        db = _db_with_msgs(tmp_path, msgs)
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100, chat_title="T", period_label="full",
            ai_split=True, ai_split_chunk_words=30,
        )
        assert len(files) >= 2

    def test_ai_split_all_files_valid_html(self, tmp_path):
        msgs = [_msg(msg_id=i, text=f"{'word ' * 20}", date=f"2025-01-01T10:{i:02d}:00")
                for i in range(50)]
        db = _db_with_msgs(tmp_path, msgs)
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100, chat_title="T", period_label="full",
            ai_split=True, ai_split_chunk_words=30,
        )
        for f in files:
            html = open(f, encoding="utf-8").read()
            assert "<!DOCTYPE html>" in html

    def test_no_ai_split_single_file(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(msg_id=i, text=f"msg{i}", date=f"2025-01-01T10:{i:02d}:00")
                                       for i in range(5)])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(
            chat_id=-100, chat_title="T", period_label="full",
            ai_split=False,
        )
        assert len(files) == 1


class TestHtmlTopicSuffix:
    def test_filename_with_topic(self, tmp_path):
        db = DBManager(str(tmp_path / "test.db"))
        db.insert_messages_batch([_msg(text="hi", topic_id=5)])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full", topic_id=5)
        assert "_topic5" in files[0]

    def test_filename_without_topic(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg()])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="T", period_label="full")
        assert "_topic" not in os.path.basename(files[0])


class TestHtmlUnicode:
    def test_unicode_in_html(self, tmp_path):
        db = _db_with_msgs(tmp_path, [_msg(username="Алексей", text="Привет мир")])
        gen = HtmlGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=-100, chat_title="Тест", period_label="full")
        html = open(files[0], encoding="utf-8").read()
        assert "Привет мир" in html
        assert "Алексей" in html
