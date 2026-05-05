"""
tests/test_e2e/test_stress.py

Стресс-тесты: производительность БД, склейки, экспорта при больших объёмах.
"""
import time

import pytest

from core.database import DBManager
from core.merger import MergerService
from features.export.generator import JsonGenerator, MarkdownGenerator


CHAT_ID = -100


def _msg(i, chat_id=CHAT_ID, text=None):
    return {
        "chat_id": chat_id,
        "message_id": i,
        "topic_id": None,
        "user_id": i % 100,
        "username": f"user_{i % 100}",
        "date": f"2025-01-{1 + (i // 86400):02d}T{(i // 3600) % 24:02d}:00:00",
        "text": text or f"Message {i}",
        "media_path": None,
        "file_type": None,
        "file_size": None,
        "reply_to_msg_id": None,
        "post_id": None,
        "is_comment": 0,
        "from_linked_group": 0,
    }


class TestBatchInsert:
    @pytest.mark.slow
    def test_batch_insert_100k(self, tmp_path):
        db = DBManager(str(tmp_path / "big.db"))
        msgs = [_msg(i) for i in range(100_000)]

        start = time.perf_counter()
        db.insert_messages_batch(msgs)
        elapsed = time.perf_counter() - start

        assert elapsed < 30, f"Insert took {elapsed:.1f}s — too slow"
        rows = db.get_messages(CHAT_ID)
        assert len(rows) == 100_000


class TestMergerStress:
    @pytest.mark.slow
    def test_merger_50k(self, tmp_path):
        db = DBManager(str(tmp_path / "merge.db"))
        msgs = [{
            "chat_id": CHAT_ID, "message_id": i, "topic_id": None,
            "user_id": 1, "username": "user_1",
            "date": f"2025-01-01T10:00:{i % 60:02d}",
            "text": f"msg{i}", "media_path": None, "file_type": None,
            "file_size": None, "reply_to_msg_id": None, "post_id": None,
            "is_comment": 0, "from_linked_group": 0,
        } for i in range(50_000)]
        db.insert_messages_batch(msgs)

        svc = MergerService()
        start = time.perf_counter()
        stats = svc.run_merge(db, CHAT_ID)
        elapsed = time.perf_counter() - start

        assert elapsed < 10, f"Merge took {elapsed:.1f}s — too slow"
        assert stats.total_msgs == 50_000
        assert stats.groups_count + stats.singles_count > 0


class TestExportStress:
    @pytest.mark.slow
    def test_json_export_10k(self, tmp_path):
        db = DBManager(str(tmp_path / "stress.db"))
        msgs = [_msg(i, text="Word " * 50) for i in range(10_000)]
        db.insert_messages_batch(msgs)

        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        start = time.perf_counter()
        files = gen.generate(chat_id=CHAT_ID, chat_title="Stress", period_label="full")
        elapsed = time.perf_counter() - start

        assert len(files) >= 1
        assert elapsed < 30

    @pytest.mark.slow
    def test_md_export_10k(self, tmp_path):
        db = DBManager(str(tmp_path / "stress_md.db"))
        msgs = [_msg(i, text="Word " * 50) for i in range(10_000)]
        db.insert_messages_batch(msgs)

        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        start = time.perf_counter()
        files = gen.generate(chat_id=CHAT_ID, chat_title="Stress", period_label="full")
        elapsed = time.perf_counter() - start

        assert len(files) >= 1
        assert elapsed < 30


class TestEdgeCases:
    def test_long_text_export(self, tmp_path):
        db = DBManager(str(tmp_path / "long.db"))
        db.insert_messages_batch([_msg(1, text="A" * 100_000)])
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=CHAT_ID, chat_title="T", period_label="full")
        assert len(files) == 1
        content = open(files[0], encoding="utf-8").read()
        assert len(content) > 100_000

    def test_empty_text_messages(self, tmp_path):
        db = DBManager(str(tmp_path / "empty.db"))
        msgs = [_msg(i, text="") for i in range(100)]
        db.insert_messages_batch(msgs)
        gen = JsonGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=CHAT_ID, chat_title="T", period_label="full")
        assert len(files) >= 1

    def test_unicode_heavy_export(self, tmp_path):
        db = DBManager(str(tmp_path / "unicode.db"))
        msgs = [_msg(i, text=f"Привет мир 🌍 日本語 테스트 {i}") for i in range(50)]
        db.insert_messages_batch(msgs)
        gen = MarkdownGenerator(db=db, output_dir=str(tmp_path))
        files = gen.generate(chat_id=CHAT_ID, chat_title="T", period_label="full")
        content = open(files[0], encoding="utf-8").read()
        assert "Привет мир" in content
