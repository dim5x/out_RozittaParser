"""
apply_date_filter_patch.py
──────────────────────────
Патч для исправления BUG: «Даты не применяются при экспорте».

Запускать из корня проекта:
    python apply_date_filter_patch.py

Что делает скрипт:
    1. core/database.py          — добавляет date_from/date_to в get_messages()
    2. features/export/generator.py — прокидывает параметры во все 4 генератора
    3. features/export/ui.py     — добавляет поля в ExportParams + в вызовы .generate()
    4. ui/main_window.py         — читает даты из params и кладёт в ExportParams

Скрипт идемпотентен: повторный запуск обнаружит, что NEW уже стоит, и пропустит.
"""

import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def apply(path: Path, old: str, new: str, label: str) -> bool:
    """
    Заменяет old → new в файле path.
    Возвращает True если замена была сделана, False если old не найден
    (предполагается, что патч уже применён).
    """
    src = read(path)

    if new.strip() in src:
        print(f"  ⏭  {label}: уже применён, пропускаем")
        return False

    if old not in src:
        print(f"  ✗  {label}: OLD-блок не найден — проверьте файл вручную")
        print(f"     Файл: {path}")
        return False

    count = src.count(old)
    if count > 1:
        print(f"  ⚠  {label}: OLD-блок найден {count} раз — берём первое вхождение")

    write(path, src.replace(old, new, 1))
    print(f"  ✓  {label}")
    return True


def check_file(path: Path) -> bool:
    if not path.exists():
        print(f"  ✗  Файл не найден: {path}")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# ПАТЧ 1 — core/database.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_database(root: Path) -> None:
    path = root / "core" / "database.py"
    print(f"\n[1/4] {path.relative_to(root)}")
    if not check_file(path):
        return

    # 1а — сигнатура get_messages
    apply(
        path,
        old="""\
    def get_messages(
        self,
        chat_id:          int,
        *,
        topic_id:         Optional[int] = None,
        user_id:          Optional[int] = None,
        include_comments: bool          = False,
    ) -> List[sqlite3.Row]:""",
        new="""\
    def get_messages(
        self,
        chat_id:          int,
        *,
        topic_id:         Optional[int] = None,
        user_id:          Optional[int] = None,
        include_comments: bool          = False,
        date_from:        Optional[str] = None,   # "YYYY-MM-DD"
        date_to:          Optional[str] = None,   # "YYYY-MM-DD" (включительно)
    ) -> List[sqlite3.Row]:""",
        label="get_messages: сигнатура",
    )

    # 1б — WHERE-условия в теле
    apply(
        path,
        old="""\
        if not include_comments:
            conditions.append("is_comment = 0")

        where_clause = " AND ".join(conditions)""",
        new="""\
        if not include_comments:
            conditions.append("is_comment = 0")

        if date_from is not None:
            conditions.append("date >= ?")
            params.append(date_from)               # "2026-04-10" < "2026-04-10 07:00" ✅

        if date_to is not None:
            conditions.append("date <= ?")
            params.append(date_to + " 23:59:59")   # включаем весь последний день

        where_clause = " AND ".join(conditions)""",
        label="get_messages: WHERE date_from/date_to",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ПАТЧ 2 — features/export/generator.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_generator(root: Path) -> None:
    path = root / "features" / "export" / "generator.py"
    print(f"\n[2/4] {path.relative_to(root)}")
    if not check_file(path):
        return

    # 2а — DocxGenerator.generate() сигнатура
    apply(
        path,
        old="""\
    def generate(
        self,
        chat_id:          int,
        chat_title:       str           = "",
        split_mode:       str           = "none",
        topic_id:         Optional[int] = None,
        user_id:          Optional[int] = None,
        include_comments: bool          = False,
        period_label:     str           = "fullchat",
        log:              _LogCallback  = None,
    ) -> List[str]:""",
        new="""\
    def generate(
        self,
        chat_id:          int,
        chat_title:       str           = "",
        split_mode:       str           = "none",
        topic_id:         Optional[int] = None,
        user_id:          Optional[int] = None,
        include_comments: bool          = False,
        period_label:     str           = "fullchat",
        date_from:        Optional[str] = None,
        date_to:          Optional[str] = None,
        log:              _LogCallback  = None,
    ) -> List[str]:""",
        label="DocxGenerator.generate: сигнатура",
    )

    # 2б — DocxGenerator.generate() тело: _generate_by_posts + get_messages
    apply(
        path,
        old="""\
            if split_mode == "post":
                files = self._generate_by_posts(
                    chat_id          = chat_id,
                    topic_id         = topic_id,
                    user_id          = user_id,
                    include_comments = include_comments,
                )
            else:
                messages = self._db.get_messages(
                    chat_id          = chat_id,
                    topic_id         = topic_id,
                    user_id          = user_id,
                    include_comments = include_comments,
                )""",
        new="""\
            if split_mode == "post":
                files = self._generate_by_posts(
                    chat_id          = chat_id,
                    topic_id         = topic_id,
                    user_id          = user_id,
                    include_comments = include_comments,
                    date_from        = date_from,
                    date_to          = date_to,
                )
            else:
                messages = self._db.get_messages(
                    chat_id          = chat_id,
                    topic_id         = topic_id,
                    user_id          = user_id,
                    include_comments = include_comments,
                    date_from        = date_from,
                    date_to          = date_to,
                )""",
        label="DocxGenerator.generate: вызовы _generate_by_posts и get_messages",
    )

    # 2в — DocxGenerator._generate_by_posts сигнатура + внутренний get_messages
    apply(
        path,
        old="""\
    def _generate_by_posts(
        self,
        chat_id:          int,
        topic_id:         Optional[int],
        user_id:          Optional[int],
        include_comments: bool,
    ) -> List[str]:
        \"\"\"Режим "post" — по одному файлу на каждый пост.\"\"\"
        posts = self._db.get_messages(
            chat_id          = chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = False,
        )""",
        new="""\
    def _generate_by_posts(
        self,
        chat_id:          int,
        topic_id:         Optional[int],
        user_id:          Optional[int],
        include_comments: bool,
        date_from:        Optional[str] = None,
        date_to:          Optional[str] = None,
    ) -> List[str]:
        \"\"\"Режим "post" — по одному файлу на каждый пост.\"\"\"
        posts = self._db.get_messages(
            chat_id          = chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = False,
            date_from        = date_from,
            date_to          = date_to,
        )""",
        label="_generate_by_posts: сигнатура + get_messages",
    )

    # 2г — JsonGenerator.generate() сигнатура
    apply(
        path,
        old="""\
    def generate(
        self,
        chat_id:              int,
        chat_title:           str,
        *,
        topic_id:             Optional[int]  = None,      # ← задача 2
        user_id:              Optional[int]  = None,
        include_comments:     bool           = False,
        ai_split:             bool           = False,
        period_label:         str            = "fullchat", # ← задача 3
        ai_split_chunk_words: int            = 300_000,    # ← задача 4
        log:                  _LogCallback   = lambda _: None,
    ) -> List[str]:
        \"\"\"
        Основная точка входа. Строит JSON и сохраняет на диск.""",
        new="""\
    def generate(
        self,
        chat_id:              int,
        chat_title:           str,
        *,
        topic_id:             Optional[int]  = None,      # ← задача 2
        user_id:              Optional[int]  = None,
        include_comments:     bool           = False,
        ai_split:             bool           = False,
        period_label:         str            = "fullchat", # ← задача 3
        ai_split_chunk_words: int            = 300_000,    # ← задача 4
        date_from:            Optional[str]  = None,
        date_to:              Optional[str]  = None,
        log:                  _LogCallback   = lambda _: None,
    ) -> List[str]:
        \"\"\"
        Основная точка входа. Строит JSON и сохраняет на диск.""",
        label="JsonGenerator.generate: сигнатура",
    )

    # 2д — JsonGenerator.generate() — get_messages внутри
    apply(
        path,
        old="""\
        log("📋 Загружаю сообщения из БД для JSON-экспорта...")
        rows = self._db.get_messages(
            chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = include_comments,
        )

        if not rows:
            raise EmptyDataError(f"Нет сообщений для чата {chat_id}")

        log(f"📊 Строк получено: {len(rows)}")

        stt_map:   dict[int, str] = self._db.get_transcriptions_for_chat(chat_id)""",
        new="""\
        log("📋 Загружаю сообщения из БД для JSON-экспорта...")
        rows = self._db.get_messages(
            chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = include_comments,
            date_from        = date_from,
            date_to          = date_to,
        )

        if not rows:
            raise EmptyDataError(f"Нет сообщений для чата {chat_id}")

        log(f"📊 Строк получено: {len(rows)}")

        stt_map:   dict[int, str] = self._db.get_transcriptions_for_chat(chat_id)""",
        label="JsonGenerator.generate: get_messages",
    )

    # 2е — MarkdownGenerator.generate() сигнатура
    apply(
        path,
        old="""\
    def generate(
        self,
        chat_id:              int,
        chat_title:           str,
        *,
        topic_id:             Optional[int]  = None,      # ← задача 2
        user_id:              Optional[int]  = None,
        include_comments:     bool           = False,
        ai_split:             bool           = False,
        period_label:         str,
        ai_split_chunk_words: int            = 300_000,    # ← задача 4
        log:                  _LogCallback   = lambda _: None,
    ) -> List[str]:
        \"\"\"
        Основная точка входа. Строит Markdown и сохраняет на диск.""",
        new="""\
    def generate(
        self,
        chat_id:              int,
        chat_title:           str,
        *,
        topic_id:             Optional[int]  = None,      # ← задача 2
        user_id:              Optional[int]  = None,
        include_comments:     bool           = False,
        ai_split:             bool           = False,
        period_label:         str,
        ai_split_chunk_words: int            = 300_000,    # ← задача 4
        date_from:            Optional[str]  = None,
        date_to:              Optional[str]  = None,
        log:                  _LogCallback   = lambda _: None,
    ) -> List[str]:
        \"\"\"
        Основная точка входа. Строит Markdown и сохраняет на диск.""",
        label="MarkdownGenerator.generate: сигнатура",
    )

    # 2ж — MarkdownGenerator.generate() — get_messages внутри
    apply(
        path,
        old="""\
        log("📋 Загружаю сообщения из БД для Markdown-экспорта...")
        rows = self._db.get_messages(
            chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = include_comments,
        )

        if not rows:
            raise EmptyDataError(f"Нет сообщений для чата {chat_id}")

        log(f"📊 Строк получено: {len(rows)}")

        stt_map:    dict[int, str] = self._db.get_transcriptions_for_chat(chat_id)""",
        new="""\
        log("📋 Загружаю сообщения из БД для Markdown-экспорта...")
        rows = self._db.get_messages(
            chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = include_comments,
            date_from        = date_from,
            date_to          = date_to,
        )

        if not rows:
            raise EmptyDataError(f"Нет сообщений для чата {chat_id}")

        log(f"📊 Строк получено: {len(rows)}")

        stt_map:    dict[int, str] = self._db.get_transcriptions_for_chat(chat_id)""",
        label="MarkdownGenerator.generate: get_messages",
    )

    # 2з — HtmlGenerator.generate() сигнатура
    apply(
        path,
        old="""\
    def generate(
        self,
        chat_id:              int,
        chat_title:           str,
        *,
        topic_id:             Optional[int]  = None,
        user_id:              Optional[int]  = None,
        include_comments:     bool           = False,
        ai_split:             bool           = False,
        period_label:         str            = "fullchat",
        ai_split_chunk_words: int            = 300_000,
        log:                  _LogCallback   = lambda _: None,
    ) -> List[str]:
        \"\"\"
        Основная точка входа. Строит HTML и сохраняет на диск.""",
        new="""\
    def generate(
        self,
        chat_id:              int,
        chat_title:           str,
        *,
        topic_id:             Optional[int]  = None,
        user_id:              Optional[int]  = None,
        include_comments:     bool           = False,
        ai_split:             bool           = False,
        period_label:         str            = "fullchat",
        ai_split_chunk_words: int            = 300_000,
        date_from:            Optional[str]  = None,
        date_to:              Optional[str]  = None,
        log:                  _LogCallback   = lambda _: None,
    ) -> List[str]:
        \"\"\"
        Основная точка входа. Строит HTML и сохраняет на диск.""",
        label="HtmlGenerator.generate: сигнатура",
    )

    # 2и — HtmlGenerator.generate() — get_messages внутри
    apply(
        path,
        old="""\
        log("📋 Загружаю сообщения из БД для HTML-экспорта...")
        rows = self._db.get_messages(
            chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = include_comments,
        )

        if not rows:
            raise EmptyDataError(f"Нет сообщений для чата {chat_id}")

        log(f"📊 Строк получено: {len(rows)}")

        stt_map:    dict[int, str] = self._db.get_transcriptions_for_chat(chat_id)""",
        new="""\
        log("📋 Загружаю сообщения из БД для HTML-экспорта...")
        rows = self._db.get_messages(
            chat_id,
            topic_id         = topic_id,
            user_id          = user_id,
            include_comments = include_comments,
            date_from        = date_from,
            date_to          = date_to,
        )

        if not rows:
            raise EmptyDataError(f"Нет сообщений для чата {chat_id}")

        log(f"📊 Строк получено: {len(rows)}")

        stt_map:    dict[int, str] = self._db.get_transcriptions_for_chat(chat_id)""",
        label="HtmlGenerator.generate: get_messages",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ПАТЧ 3 — features/export/ui.py
# Этот файл не был предоставлен для анализа, поэтому используем
# гибкий regex-поиск вместо точного str.replace.
# ─────────────────────────────────────────────────────────────────────────────

def patch_export_ui(root: Path) -> None:
    path = root / "features" / "export" / "ui.py"
    print(f"\n[3/4] {path.relative_to(root)}")
    if not check_file(path):
        return

    src = read(path)
    changed = False

    # 3а — добавить date_from/date_to в ExportParams после ai_split_chunk_words
    if "date_from:" in src and "date_to:" in src:
        print("  ⏭  ExportParams date_from/date_to: уже применён, пропускаем")
    else:
        # Ищем последнее поле перед концом dataclass.
        # Ориентир — строка с ai_split_chunk_words (она точно последняя по плану).
        pattern = re.compile(
            r'([ \t]+ai_split_chunk_words\s*:\s*int\s*=\s*[\d_]+)',
        )
        m = pattern.search(src)
        if m:
            indent = re.match(r'([ \t]+)', m.group(1)).group(1)
            insertion = (
                f"\n{indent}date_from:            Optional[str] = None"
                f"   # \"YYYY-MM-DD\""
                f"\n{indent}date_to:              Optional[str] = None"
                f"   # \"YYYY-MM-DD\" (включительно)"
            )
            src = src[:m.end()] + insertion + src[m.end():]
            changed = True
            print("  ✓  ExportParams: добавлены date_from/date_to")

            # Проверяем наличие Optional в импортах
            if "Optional" not in src:
                src = src.replace(
                    "from typing import",
                    "from typing import Optional, ",
                    1,
                )
                print("  ✓  ExportParams: добавлен импорт Optional")
        else:
            print("  ✗  ExportParams: поле ai_split_chunk_words не найдено — "
                  "добавьте date_from/date_to вручную в конец dataclass ExportParams")

    # 3б — добавить date_from/date_to в каждый вызов .generate() внутри ExportWorker.run()
    # Стратегия: находим вызовы .generate( с параметром ai_split= и дописываем после него.
    # Маркер «уже применено» — наличие date_from= в вызове generate.
    GEN_PATTERN = re.compile(
        r'(\.generate\([^)]*?ai_split_chunk_words\s*=\s*\w+[^)]*?)'
        r'(\s*,?\s*log\s*=)',
        re.DOTALL,
    )

    def add_date_params(m: re.Match) -> str:
        body = m.group(1)
        log_part = m.group(2)
        if "date_from" in body:
            return m.group(0)   # уже есть
        # Определяем отступ по последней строке body
        last_line = body.rstrip().split("\n")[-1]
        indent = re.match(r'([ \t]*)', last_line).group(1)
        return (
            body
            + f"\n{indent}    date_from        = params.date_from,"
            + f"\n{indent}    date_to          = params.date_to,"
            + log_part
        )

    new_src, n = GEN_PATTERN.subn(add_date_params, src)
    if n:
        if new_src != src:
            src = new_src
            changed = True
            print(f"  ✓  ExportWorker.run: date_from/date_to добавлены в {n} вызов(а) .generate()")
        else:
            print(f"  ⏭  ExportWorker.run: вызовы .generate() уже содержат date_from/date_to")
    else:
        # Запасной вариант: ищем вызовы generate без ai_split_chunk_words
        # (например, DocxGenerator — у него нет ai_split)
        GEN_PATTERN2 = re.compile(
            r'(\.generate\([^)]*?period_label\s*=\s*\w+[^)]*?)'
            r'(\s*,?\s*log\s*=)',
            re.DOTALL,
        )
        new_src2, n2 = GEN_PATTERN2.subn(add_date_params, src)
        if n2 and new_src2 != src:
            src = new_src2
            changed = True
            print(f"  ✓  ExportWorker.run: date_from/date_to добавлены в {n2} вызов(а) .generate() (запасной паттерн)")
        else:
            print("  ⚠  ExportWorker.run: не удалось найти вызовы .generate() автоматически.")
            print("     Добавьте вручную строки:")
            print("         date_from = params.date_from,")
            print("         date_to   = params.date_to,")
            print("     в каждый вызов <generator>.generate() внутри ExportWorker.run()")

    if changed:
        write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# ПАТЧ 4 — ui/main_window.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_main_window(root: Path) -> None:
    path = root / "ui" / "main_window.py"
    print(f"\n[4/4] {path.relative_to(root)}")
    if not check_file(path):
        return

    # 4а — читаем date_from/date_to из params
    apply(
        path,
        old="""\
        chat = self._settings_screen._current_chat or {}
        params = self._settings_screen.get_params()
        split_mode = params.split_mode if params else "none"

        chat_title = (""",
        new="""\
        chat = self._settings_screen._current_chat or {}
        params = self._settings_screen.get_params()
        split_mode    = params.split_mode  if params else "none"
        date_from_str = str(params.date_from) if (params and params.date_from) else None
        date_to_str   = str(params.date_to)   if (params and params.date_to)   else None

        chat_title = (""",
        label="_run_export: читаем date_from/date_to из params",
    )

    # 4б — передаём в ExportParams
    apply(
        path,
        old="""\
            ai_split=self._settings_screen.get_ai_split(),
            ai_split_chunk_words=self._settings_screen.get_ai_split_chunk_words() if hasattr(self._settings_screen, 'get_ai_split_chunk_words') else 300_000,
        )""",
        new="""\
            ai_split=self._settings_screen.get_ai_split(),
            ai_split_chunk_words=self._settings_screen.get_ai_split_chunk_words() if hasattr(self._settings_screen, 'get_ai_split_chunk_words') else 300_000,
            date_from=date_from_str,
            date_to=date_to_str,
        )""",
        label="_run_export: date_from/date_to в ExportParams",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ТОЧКА ВХОДА
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    root = Path(__file__).parent.resolve()
    print(f"Корень проекта: {root}")
    print("=" * 60)

    patch_database(root)
    patch_generator(root)
    patch_export_ui(root)
    patch_main_window(root)

    print("\n" + "=" * 60)
    print("Готово. Проверьте строки с '✗' или '⚠' выше — они требуют ручного вмешательства.")
    print("Строки '✓' — патч применён успешно.")
    print("Строки '⏭' — патч уже был применён ранее (идемпотентность).")


if __name__ == "__main__":
    main()
