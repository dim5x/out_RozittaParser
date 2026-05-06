# TESTS_EXTENSION_PLAN.md — Rozitta Parser Test Extension (S6–S10)

**Дата:** 2026-05-06
**Версия:** 1.0
**Статус:** ✅ Complete
**Предпосылка:** S1–S5 завершены (450 тестов, все проходят)
**Результат:** 191 новых тестов, 5 спринтов завершены

---

## Обзор спринтов

| Спринт | Фокус | Тестов | Зависимости | Статус |
|--------|-------|--------|-------------|--------|
| **S6** | STT: audio_converter, whisper_manager, worker | 66 | S1 | ✅ Done |
| **S7** | Export: participants.py, xml_magic.py | 41 | S1, S3 | ✅ Done |
| **S8** | Config edge cases + retry advanced | 27 | S1 | ✅ Done |
| **S9** | UI: styles.py, widgets.py (properties) | 46 | S1 | ✅ Done |
| **S10** | finish_takeout.py async | 10 | S1, S4 | ✅ Done |
| **Итого** | | **191** | | |

---

## S6: STT Module

### test_audio_converter.py (~18 тестов)
- `AudioConverter.convert_to_wav()` — мок subprocess.run, os.path.exists
  - Успешная конвертация, автотемп, структура FFmpeg-команды, timeout=120
  - Ошибки: файл не найден → STTError, FFmpeg не установлен, timeout, bad return code, пустой вывод
- `AudioConverter.cleanup()` — удаление, noop для несуществующих, swallow OSError

### test_whisper_manager.py (~25 тестов)
- `is_available()` — find_spec возвращает/не возвращает
- `install()` — subprocess.run success/fail/timeout, sys.frozen, log_callback
- `instance()` — singleton, reset
- `_postprocess()` (regex) — пустая строка, множественные пробелы, повторы слов/фраз
- `transcribe()` — мок WhisperModel, STTError при ошибке загрузки, initial_prompt для ru
- `unload()` — noop без force, очистка с force

### test_stt_worker.py (~17 тестов)
- Init параметры по умолчанию/кастомные
- Whisper не доступен → install success/fail
- Нет кандидатов → progress 100
- Транскрипция: сохранение в БД, empty text, ошибка продолжается, progress tracking
- Worker run: STTError/generic error → error signal, finished всегда, unload в finally

## S7: Export Extras

### test_participants.py (~20 тестов)
- Создание DOCX, валидный файл, имя файла
- Содержимое: заголовок, таблица, имена, колонки
- Сортировка по message_count desc
- Ссылки: @username → t.me, нет username → tg://user?id=
- Edge: пустой список, unicode, спецсимволы, 1 пользователь, создание директории

### test_xml_magic.py (~25 тестов)
- `reset_counter()` — сброс, инкремент, между документами
- `add_bookmark()` — XML-элементы (bookmarkStart/End), имя, ID, уникальность
- `add_internal_hyperlink()` — XML, anchor, текст, цвет, underline
- `add_external_hyperlink()` — relationship, r:id, URL, текст
- `write_text_with_links()` — plain text, 1/2 URL, URL only, empty, query params

## S8: Config + Retry (расширение существующих)

### test_config.py (+15 тестов)
- split_mode: valid (none/day/month/post), invalid (weekly/NONE/"")
- Corrupted JSON: пустой файл, extra keys, non-dict JSON
- Properties: is_all_time (364/365/366), db_path с вложенными путями, proxy fields

### test_retry.py (+12 тестов)
- max_attempts < 1 → ValueError
- backoff: delay расчёт (0.1, 0.3, 0.9)
- flood_cls: seconds=120 + buffer=3, custom buffer, seconds=0
- flood_cls=None: нет спец-обработки
- max_attempts=1: sleep не вызывается
- mixed flood + retry, return value preserved

## S9: UI Logic

### test_styles.py (~20 тестов)
- `_STYLE_REGISTRY`: ключи, все значения — строки, кол-во >= 20
- `get_style()`: known → string, unknown → ValueError
- `combine_styles()`: 2 стиля, 1 стиль, unknown → ValueError, порядок
- `chat_icon_qss()`: channel/group/forum/private/unknown, содержит QLabel
- Константы: hex-формат, positive int

### test_widgets.py (~25 тестов) — нужен QApplication fixture
- `FilterButton`: filter_key, checkable
- `UserTag`: user_id, is_all, текст
- `StepperWidget`: default 0, set_active, custom steps
- `LogWidget`: append stores, append_info/error, clear, filter, multiple levels
- `MediaButton`: media_type, active
- `ChipButton`: media_type, setActive toggle
- `SplitModeButton`: mode property

## S10: finish_takeout.py

### test_finish_takeout.py (~15 тестов)
- Authorized: FinishTakeoutSessionRequest вызван, disconnect, get_me, success message
- Not authorized: early return, message
- Errors: NO_TAKEOUT_IN_PROGRESS, generic exception, disconnect при ошибке
- Session path, env vars (TG_API_ID/HASH), client creation params

---

## Итого: 450 + 191 = 641 тест

## Верификация
```bash
pytest tests/ -v --tb=short
# 641 passed in 6.34s
```

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-05-06 | Начальный план S6–S10 |
| 1.1 | 2026-05-06 | Все спринты S6–S10 завершены: 191 тест, итого 641 |
