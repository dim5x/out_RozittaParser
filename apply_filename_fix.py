"""
Патч: информативные имена файлов медиа в features/parser/api.py

PATCH 1 — добавляет DocumentAttributeFilename в импорты из telethon.tl.types

PATCH 2 — добавляет хелпер _get_original_filename(message) после _build_media_dir:
    Извлекает оригинальное имя из DocumentAttributeFilename.
    Возвращает None если атрибута нет (фото, голосовые).

PATCH 3 — заменяет строку формирования filename в _process_message:
    Было:  {chat_id}_{message.id}_{timestamp}
    Стало: {message.id}_{original_name}   если есть оригинальное имя
           {message.id}_{timestamp}       если нет (фото и т.п.)
    chat_id убран — файлы лежат в папке конкретного чата, он избыточен.

Побочные эффекты: уже скачанные файлы не переименовываются.
Новые файлы получат новые имена — DownloadTracker отслеживает по message_id,
а не по имени файла, поэтому инкрементальный режим не ломается.

Run: python apply_filename_fix.py
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
# PATCH 1: добавляем DocumentAttributeFilename в импорты
# ---------------------------------------------------------------------------
OLD_1 = """\
from telethon.tl.types import (
    Channel,
    Chat,
    DocumentAttributeAudio,
    DocumentAttributeVideo,
    Message,
    MessageMediaDocument,
    MessageMediaPhoto,
    User,
)"""

NEW_1 = """\
from telethon.tl.types import (
    Channel,
    Chat,
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    Message,
    MessageMediaDocument,
    MessageMediaPhoto,
    User,
)"""

if OLD_1 not in src:
    print("WARN: PATCH 1 — блок импортов не найден, пропускаем")
else:
    src = src.replace(OLD_1, NEW_1, 1)
    print("OK:   PATCH 1 — DocumentAttributeFilename добавлен в импорты")

# ---------------------------------------------------------------------------
# PATCH 2: хелпер _get_original_filename после _build_media_dir
# ---------------------------------------------------------------------------
OLD_2 = """\
    @staticmethod
    def _classify_chat_type(entity: object) -> str:"""

NEW_2 = """\
    @staticmethod
    def _get_original_filename(message: Message) -> Optional[str]:
        \"\"\"
        Возвращает оригинальное имя файла из DocumentAttributeFilename.

        Присутствует только у документов (видео, файлы, голосовые загруженные
        как файл). У фото и стандартных голосовых (.ogg) атрибута нет — вернёт None.

        Имя очищается через sanitize_filename() для безопасного использования
        в пути файловой системы.
        \"\"\"
        if not isinstance(message.media, MessageMediaDocument):
            return None
        doc = message.media.document
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeFilename) and attr.file_name:
                return sanitize_filename(attr.file_name)
        return None

    @staticmethod
    def _classify_chat_type(entity: object) -> str:"""

if OLD_2 not in src:
    print("WARN: PATCH 2 — маркер _classify_chat_type не найден, пропускаем")
else:
    src = src.replace(OLD_2, NEW_2, 1)
    print("OK:   PATCH 2 — хелпер _get_original_filename добавлен")

# ---------------------------------------------------------------------------
# PATCH 3: новая логика формирования filename в _process_message
# ---------------------------------------------------------------------------
OLD_3 = """\
            filename = f\"{chat_id}_{message.id}_{int(message.date.timestamp())}\"
            target   = os.path.join(media_dir, filename)"""

NEW_3 = """\
            original_name = self._get_original_filename(message)
            if original_name:
                # Оригинальное имя есть — используем его с префиксом msg_id
                # чтобы избежать коллизий при одинаковых именах в чате
                filename = f\"{message.id}_{original_name}\"
            else:
                # Фото и файлы без имени — timestamp как раньше (без chat_id:
                # файлы лежат в папке чата, он избыточен)
                filename = f\"{message.id}_{int(message.date.timestamp())}\"
            target   = os.path.join(media_dir, filename)"""

if OLD_3 not in src:
    print("WARN: PATCH 3 — строка формирования filename не найдена, пропускаем")
else:
    src = src.replace(OLD_3, NEW_3, 1)
    print("OK:   PATCH 3 — логика формирования filename обновлена")

# ---------------------------------------------------------------------------
# Сохраняем
# ---------------------------------------------------------------------------
if src != original:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"\n✅ Сохранено: {PATH}")
else:
    print("\n⚠️  Изменений не сделано — проверьте предупреждения выше")
