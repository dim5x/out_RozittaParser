"""
Патч: надёжное скачивание больших файлов в features/parser/api.py

Что меняется (3 хирургических изменения):

PATCH 1 — добавляет `import glob`

PATCH 2 — добавляет модульную функцию `_cleanup_partial(target_path)`:
    Удаляет все файлы target_path.* (частично скачанные).
    Telethon пишет сразу с финальным расширением (.mp4, .jpg, ...),
    поэтому partial file = файл с правильным именем но неполным размером.

PATCH 3 — переписывает тело `_download_media`:
    - Перед стартом: если target_path.* существует и >= expected_size → return,
      иначе удаляем (cleanup_partial).
    - На TimeoutError: cleanup_partial + raise OSError → @async_retry сделает повтор.
    - На CancelledError (batch-таймаут из _flush_tasks): cleanup_partial + re-raise.
    - После успеха: сравниваем os.path.getsize() с document.size.
      Если файл неполный → удаляем → raise OSError → @async_retry повторит.

PATCH 4 — увеличивает wait_for-таймаут в _flush_tasks с 300s → 3600s.
    300s может убить batch с несколькими 1GB файлами ещё до первого retry.
    3600s = страховочная сетка от полного зависания при отсутствии прогресса.

Побочные эффекты: нет. Логика retry, DB, tracker не затронуты.

Run: python apply_download_fix.py
"""

import re
import sys

PATH = "features/parser/api.py"

try:
    with open(PATH, encoding="utf-8") as f:
        src = f.read()
except FileNotFoundError:
    print(f"ERROR: файл не найден — {PATH}")
    sys.exit(1)

original = src

# ---------------------------------------------------------------------------
# PATCH 1: добавляем `import glob`
# ---------------------------------------------------------------------------
OLD_1 = """\
import asyncio
import logging
import os
import time"""

NEW_1 = """\
import asyncio
import glob
import logging
import os
import time"""

if OLD_1 not in src:
    print("WARN: PATCH 1 — блок import не найден, пропускаем")
else:
    src = src.replace(OLD_1, NEW_1, 1)
    print("OK:   PATCH 1 — добавлен `import glob`")


# ---------------------------------------------------------------------------
# PATCH 2: добавляем _cleanup_partial перед классом CollectParams
# ---------------------------------------------------------------------------
OLD_2 = """\
# ==============================================================================
# Датакласс параметров сбора
# =============================================================================="""

NEW_2 = """\
def _cleanup_partial(target_path: str) -> None:
    \"\"\"
    Удаляет все файлы вида target_path.* (частично скачанные Telethon'ом).

    Telethon не использует временный .part-суффикс: он пишет сразу в файл
    с финальным расширением (.mp4, .jpg, ...). Поэтому «частичный» файл
    отличается от полного только размером, а не именем.
    \"\"\"
    for fpath in glob.glob(target_path + ".*"):
        try:
            os.remove(fpath)
            logger.debug("[cleanup_partial] удалён: %s", fpath)
        except OSError as _e:
            logger.debug("[cleanup_partial] не удалось удалить %s: %s", fpath, _e)


# ==============================================================================
# Датакласс параметров сбора
# =============================================================================="""

if OLD_2 not in src:
    print("WARN: PATCH 2 — маркер CollectParams не найден, пропускаем")
else:
    src = src.replace(OLD_2, NEW_2, 1)
    print("OK:   PATCH 2 — добавлена функция _cleanup_partial")


# ---------------------------------------------------------------------------
# PATCH 3: переписываем тело _download_media через regex (метод длинный)
# ---------------------------------------------------------------------------
OLD_3_MARKER = "        # Семафор ограничивает число параллельных сетевых скачиваний"

NEW_3_BODY = """\
        # Ожидаемый размер файла — только для документов (не для фото)
        expected_size: Optional[int] = None
        if isinstance(message.media, MessageMediaDocument):
            expected_size = getattr(message.media.document, "size", None)

        # Если полный файл уже лежит на диске — возвращаем без повторной загрузки.
        # (target_path без расширения; Telethon добавит .mp4/.jpg/... сам)
        if expected_size:
            for _existing in glob.glob(target_path + ".*"):
                if os.path.getsize(_existing) >= expected_size:
                    logger.debug(
                        "[DIAG] download_media: файл уже полный, пропускаем: %s", _existing
                    )
                    return _existing

        # Удаляем любые оставшиеся частичные файлы перед стартом
        _cleanup_partial(target_path)

        logger.debug(
            "[DIAG] download_media start: msg_id=%s media=%s path=%s expected_size=%s",
            message.id, type(message.media).__name__, target_path, expected_size,
        )

        downloaded_path: Optional[str] = None
        async with self._sem:
            try:
                downloaded_path = await asyncio.wait_for(
                    message.download_media(file=target_path),
                    timeout=1200.0,
                )
            except asyncio.TimeoutError:
                # Удаляем partial file и бросаем OSError →
                # @async_retry перехватит и сделает повторную попытку.
                _cleanup_partial(target_path)
                raise OSError(
                    f"download_media timeout (20 мин) msg_id={message.id} — "
                    f"частичный файл удалён, будет повторная попытка"
                )
            except asyncio.CancelledError:
                # Задача отменена batch-таймаутом из _flush_tasks.
                # Чистим файл, но НЕ ретраим (CancelledError пробрасываем).
                _cleanup_partial(target_path)
                raise

        # Проверка целостности: реальный размер должен совпадать с document.size
        if downloaded_path and os.path.exists(downloaded_path) and expected_size:
            actual_size = os.path.getsize(downloaded_path)
            if actual_size < expected_size:
                os.remove(downloaded_path)
                raise OSError(
                    f"Неполный файл msg_id={message.id}: "
                    f"{actual_size}/{expected_size} байт — удалён, будет повторная попытка"
                )

        logger.debug(
            "[DIAG] download_media done: msg_id=%s → %s", message.id, downloaded_path
        )
        return downloaded_path"""

# Ищем старое тело метода от маркера до конца метода (следующий def на том же уровне)
pattern_3 = (
    r"        # Семафор ограничивает число параллельных сетевых скачиваний\n"
    r"        logger\.debug\(\s*\n"
    r"            \"\[DIAG\] download_media start.*?\n"
    r"        \)\n"
    r"        async with self\._sem:.*?"
    r"        logger\.debug\(\"\[DIAG\] download_media done.*?\)\n"
    r"        return result"
)

match_3 = re.search(pattern_3, src, re.DOTALL)
if not match_3:
    print("WARN: PATCH 3 — тело _download_media не найдено через regex, пробуем прямой поиск")
    if OLD_3_MARKER not in src:
        print("WARN: PATCH 3 — маркер тоже не найден, пропускаем")
    else:
        print("INFO: PATCH 3 — маркер найден, но regex не сработал. Проверьте отступы вручную.")
else:
    src = src[:match_3.start()] + NEW_3_BODY + "\n" + src[match_3.end():]
    print("OK:   PATCH 3 — тело _download_media заменено (cleanup + integrity check)")


# ---------------------------------------------------------------------------
# PATCH 4: увеличиваем таймаут _flush_tasks 300.0 → 3600.0
# ---------------------------------------------------------------------------
OLD_4 = """\
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=300.0,
            )
        except asyncio.TimeoutError:
            logger.error(
                "[DIAG] _flush_tasks TIMEOUT: %d задач зависли, принудительно пропускаем",
                len(tasks),
            )
            results = [TimeoutError(f"download_media timeout (batch of {len(tasks)})")] * len(tasks)"""

NEW_4 = """\
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=3600.0,  # 1 час — страховка от полного зависания;
                                 # 300s было слишком мало для нескольких 1GB файлов
            )
        except asyncio.TimeoutError:
            logger.error(
                "[DIAG] _flush_tasks TIMEOUT (1ч): %d задач зависли, принудительно пропускаем",
                len(tasks),
            )
            results = [TimeoutError(f"download_media timeout (batch of {len(tasks)})")] * len(tasks)"""

if OLD_4 not in src:
    print("WARN: PATCH 4 — блок wait_for в _flush_tasks не найден, пропускаем")
else:
    src = src.replace(OLD_4, NEW_4, 1)
    print("OK:   PATCH 4 — таймаут _flush_tasks увеличен 300s → 3600s")


# ---------------------------------------------------------------------------
# Сохраняем
# ---------------------------------------------------------------------------
if src != original:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"\n✅ Сохранено: {PATH}")
else:
    print("\n⚠️  Изменений не сделано — проверьте предупреждения выше")
