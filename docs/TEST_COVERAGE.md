# TEST_COVERAGE.md — Rozitta Parser: отчёт по покрытию тестами

**Дата:** 2026-05-06
**Всего тестов:** 641
**Время прогона:** ~6.2s
**Общее покрытие строк:** 58%

---

## Сводка по спринтам

| Спринт | Фокус | Тестов | Статус |
|--------|-------|--------|--------|
| S1–S5 | Core + features базовые | 450 | ✅ |
| S6 | STT: audio_converter, whisper_manager, worker | 66 | ✅ |
| S7 | Export: participants, xml_magic | 41 | ✅ |
| S8 | Config edge cases + retry advanced | 27 | ✅ |
| S9 | UI: styles, widgets (properties) | 46 | ✅ |
| S10 | finish_takeout async | 10 | ✅ |
| **Итого** | | **641** | |

---

## Покрытие по модулям

### Хорошо покрыто (>=80%)

| Модуль | Строк | Покрытие | Непокрытые строки |
|--------|-------|----------|-------------------|
| `finish_takeout.py` | 29 | **97%** | 55 |
| `core/merger.py` | 82 | **98%** | 307–309 |
| `config.py` | 112 | **96%** | 36, 50–54 |
| `core/stt/worker.py` | 87 | **95%** | 84–85, 151–152 |
| `core/stt/whisper_manager.py` | 100 | **83%** | 129–131, 154–179 |

### Среднее покрытие (50–79%)

| Модуль | Строк | Покрытие | Основные пробелы |
|--------|-------|----------|------------------|
| `core/ui_shared/styles.py` | 130 | **82%** | chat_icon_qss варианты, константы |
| `core/utils.py` | 108 | **78%** | format_size, safe_filename, format_duration |
| `features/chats/api.py` | 244 | **78%** | media download, batch edge cases |
| `features/export/generator.py` | 584 | **77%** | split export, media embed, progress |
| `core/database.py` | 332 | **59%** | export queries, reactions, media, advanced search |
| `core/ui_shared/widgets.py` | 533 | **58%** | paint events, составные виджеты |
| `features/auth/api.py` | 234 | **57%** | login flow, QR, code verification |
| `features/parser/api.py` | 552 | **56%** | parsing logic, progress, batch processing |
| `features/export/ui.py` | 97 | **39%** | диалог экспорта, callbacks |

### Не покрыто (0%) — нецелевые

| Модуль | Строк | Причина |
|--------|-------|---------|
| `ui/main_window.py` | 1033 | Чистый PySide6 GUI, тестируется руками |
| `features/auth/ui.py` | 623 | GUI |
| `features/chats/ui.py` | 551 | GUI |
| `features/parser/ui.py` | 474 | GUI |
| `core/ui_shared/calendar.py` | 163 | GUI (QCalendarWidget) |
| `main.py` | 78 | Точка входа, склейка |
| `core/logger.py` | 77 | Настройка логирования |
| `socks.py` | 446 | Сторонняя библиотека |
| `sockshandler.py` | 82 | Сторонняя библиотека |

---

## Что можно ещё покрыть (приоритет)

### Приоритет 1: бизнес-логика (~80–100 тестов)

**`core/database.py`** (59% → ~85%)
- `get_export_messages()`, `get_media_files()`, `get_reactions()`
- `search_messages()` — полнотекстовый поиск
- `get_chat_stats()`, `get_top_senders()`
- `export_to_json()`, `export_to_csv()` — через существующие тестовые утилиты

**`features/parser/api.py`** (56% → ~80%)
- `_parse_message()` — вложения, forwarding, replies
- `_download_media()` — фото, видео, документы
- Progress tracking, batch processing edge cases

**`features/auth/api.py`** (57% → ~80%)
- Login flow: phone → code → 2FA
- QR-login
- Session save/load
- Error handling: FloodWait, PhoneCodeInvalid

### Приоритет 2: расширение существующих (~40–60 тестов)

**`features/export/generator.py`** (77% → ~90%)
- Split-mode экспорт (day/month)
- Media embed (inline images)
- Progress callbacks

**`core/ui_shared/widgets.py`** (58% → ~75%)
- `LogWidget.filter()`, `ChatListItem`
- `MediaPicker` — selection, limits
- `SplitModeSelector`

**`core/utils.py`** (78% → ~95%)
- `format_size()` — edge cases
- `safe_filename()` — спецсимволы, unicode
- `format_duration()` — часы, дни

---

## Потенциал следующего этапа

| Приоритет | Модули | ~Тестов | Покрытие строк |
|-----------|--------|---------|----------------|
| P1 | database, parser/api, auth/api | ~80–100 | 58% → ~70% |
| P2 | generator, widgets, utils | ~40–60 | 70% → ~75% |
| **Итого** | | **~120–160** | **~75%** |

Текущее покрытие без учёта GUI-модулей и сторонних библиотек: **~75%**.
С P1+P2: **~85%**.

---

## Верификация

```bash
pytest tests/ -v --tb=short          # 641 passed
pytest tests/ --cov=. --cov-report=term-missing --tb=no -q
```

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-05-06 | Начальный отчёт: 641 тест, 58% покрытия |
