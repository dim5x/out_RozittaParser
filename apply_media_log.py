"""
Патч: логирование ошибок скачивания медиа в реальном времени.

PATCH 1 — _process_message: сразу пишет в self._log при ошибке скачивания.
PATCH 2 — collect_data: итоговая сводка перед return CollectResult.

Побочные эффекты: нет. Только добавление self._log() вызовов.

Run: python apply_media_log.py
"""
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
# PATCH 1: логируем media_error сразу в _process_message
# ---------------------------------------------------------------------------
OLD_1 = """\
            except (OSError, RPCError) as exc:
                media_error = (
                    f"Медиа msg_id={message.id} не скачано после {_MAX_RETRIES} попыток: {exc}"
                )
                logger.warning("parser: %s", media_error)"""

NEW_1 = """\
            except (OSError, RPCError) as exc:
                media_error = (
                    f"Медиа msg_id={message.id} не скачано после {_MAX_RETRIES} попыток: {exc}"
                )
                logger.warning("parser: %s", media_error)
                self._log(f"⚠️ {media_error}")"""

if OLD_1 not in src:
    print("WARN: PATCH 1 — блок except в _process_message не найден, пропускаем")
else:
    src = src.replace(OLD_1, NEW_1, 1)
    print("OK:   PATCH 1 — self._log добавлен в _process_message")

# ---------------------------------------------------------------------------
# PATCH 2: итоговая сводка перед return CollectResult
# ---------------------------------------------------------------------------
OLD_2 = """\
        self._progress_cb(100)
        logger.info(
            "parser: collect_data done: msgs=%d comments=%d media=%d errors=%d",
            self._msg_count, self._comment_count, self._media_count, len(errors),
        )

        return CollectResult("""

NEW_2 = """\
        self._progress_cb(100)
        logger.info(
            "parser: collect_data done: msgs=%d comments=%d media=%d errors=%d",
            self._msg_count, self._comment_count, self._media_count, len(errors),
        )

        if errors:
            self._log(f"⚠️ Не удалось скачать файлов: {len(errors)} — подробности выше в логе")

        return CollectResult("""

if OLD_2 not in src:
    print("WARN: PATCH 2 — блок перед return CollectResult не найден, пропускаем")
else:
    src = src.replace(OLD_2, NEW_2, 1)
    print("OK:   PATCH 2 — итоговая сводка добавлена")

# ---------------------------------------------------------------------------
# Сохраняем
# ---------------------------------------------------------------------------
if src != original:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"\n✅ Сохранено: {PATH}")
else:
    print("\n⚠️  Изменений не сделано — проверьте предупреждения выше")
