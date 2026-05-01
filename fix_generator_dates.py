"""
fix_generator_dates.py
──────────────────────
Добавляет date_from / date_to во все 4 генератора в features/export/generator.py
с помощью регулярных выражений — не зависит от точных комментариев в строках.

Запускать из корня проекта:
    python fix_generator_dates.py

Что делает:
  A) Вставляет параметры date_from/date_to перед параметром `log:` в сигнатуре
     generate() каждого из 4 генераторов (Docx/Json/Markdown/Html).
  B) Добавляет date_from/date_to в каждый вызов self._db.get_messages(),
     если их там ещё нет.
"""

import re
import sys
from pathlib import Path


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# A. Вставить date_from/date_to в сигнатуру generate() перед параметром log:
#
# Ищем паттерн:
#     <indent>log: <type> = <default>,
# и вставляем перед ним два новых параметра, если их ещё нет.
# ─────────────────────────────────────────────────────────────────────────────

_SIG_PATTERN = re.compile(
    r'(?m)^([ \t]+)(log\s*:\s*_LogCallback\s*=)',
)

def patch_signatures(src: str) -> tuple[str, int]:
    """
    Для каждого вхождения строки `    log: _LogCallback = ...`
    вставляет перед ней date_from/date_to если их ещё нет.
    Возвращает (новый текст, число вставок).
    """
    insertions = 0

    def replacer(m: re.Match) -> str:
        nonlocal insertions
        indent = m.group(1)
        log_line = m.group(2)

        # Проверяем, нет ли уже date_from в 500 символах перед этим местом
        before = src[:m.start()]
        # Ищем начало ближайшей def generate( выше
        last_def = before.rfind("def generate(")
        snippet = before[last_def:] if last_def != -1 else before[-500:]
        if "date_from" in snippet:
            return m.group(0)   # уже есть

        insertions += 1
        return (
            f"{indent}date_from:            Optional[str] = None,"
            f"   # \"YYYY-MM-DD\"\n"
            f"{indent}date_to:              Optional[str] = None,"
            f"   # \"YYYY-MM-DD\" включительно\n"
            f"{indent}{log_line}"
        )

    result = _SIG_PATTERN.sub(replacer, src)
    return result, insertions


# ─────────────────────────────────────────────────────────────────────────────
# B. Добавить date_from/date_to в вызовы self._db.get_messages(...)
#
# Ищем:
#     self._db.get_messages(
#         ...
#         include_comments = ...,    ← последний аргумент перед )
#     )
# и вставляем date_from/date_to после include_comments.
# ─────────────────────────────────────────────────────────────────────────────

_CALL_PATTERN = re.compile(
    r'(self\._db\.get_messages\([^)]*?)'      # открытие вызова
    r'([ \t]+include_comments\s*=\s*\S+,?)'   # строка include_comments
    r'(\s*\))',                                # закрытие
    re.DOTALL,
)

def patch_calls(src: str) -> tuple[str, int]:
    """
    В каждый вызов self._db.get_messages() добавляет date_from/date_to
    после include_comments, если их ещё нет.
    Возвращает (новый текст, число вставок).
    """
    insertions = 0

    def replacer(m: re.Match) -> str:
        nonlocal insertions
        opening     = m.group(1)
        inc_line    = m.group(2)
        closing     = m.group(3)

        if "date_from" in opening:
            return m.group(0)   # уже есть

        # Определяем отступ по строке include_comments
        stripped = inc_line.lstrip()
        indent   = " " * (len(inc_line.rstrip("\n")) - len(inc_line.strip()))
        # Более надёжный способ: берём ведущие пробелы строки inc_line
        indent_match = re.match(r'(\s+)', inc_line)
        indent = indent_match.group(1) if indent_match else "            "

        # Убедимся, что inc_line заканчивается запятой
        ic = inc_line.rstrip()
        if not ic.endswith(","):
            ic += ","

        insertions += 1
        return (
            opening
            + ic + "\n"
            + f"{indent}date_from        = date_from,\n"
            + f"{indent}date_to          = date_to,"
            + closing
        )

    result = _CALL_PATTERN.sub(replacer, src)
    return result, insertions


# ─────────────────────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    root = Path(__file__).parent.resolve()
    path = root / "features" / "export" / "generator.py"

    print(f"Файл: {path.relative_to(root)}")
    print("=" * 60)

    if not path.exists():
        print(f"✗ Файл не найден: {path}")
        sys.exit(1)

    src = read(path)
    original = src

    # A — сигнатуры
    src, n_sig = patch_signatures(src)
    if n_sig:
        print(f"✓ Сигнатуры: date_from/date_to добавлены в {n_sig} метод(а) generate()")
    else:
        print("⏭  Сигнатуры: date_from/date_to уже присутствуют во всех generate()")

    # B — вызовы get_messages
    src, n_calls = patch_calls(src)
    if n_calls:
        print(f"✓ Вызовы get_messages: date_from/date_to добавлены в {n_calls} вызов(а)")
    else:
        print("⏭  Вызовы get_messages: date_from/date_to уже присутствуют")

    if src != original:
        write(path, src)
        print(f"\n✅ Файл сохранён: {path}")
    else:
        print("\n⏭  Файл не изменён (все патчи уже применены)")

    print("=" * 60)

    # ── Быстрая проверка: считаем сколько generate() получили date_from ──
    generators = ["DocxGenerator", "JsonGenerator", "MarkdownGenerator", "HtmlGenerator"]
    result_src = read(path)
    print("\nПроверка результата:")
    for cls in generators:
        # Ищем def generate( внутри каждого класса
        cls_pos = result_src.find(f"class {cls}")
        if cls_pos == -1:
            print(f"  ? {cls}: класс не найден")
            continue
        next_cls = result_src.find("\nclass ", cls_pos + 1)
        chunk = result_src[cls_pos: next_cls if next_cls != -1 else len(result_src)]
        has_sig  = "date_from:            Optional[str]" in chunk or "date_from:" in chunk
        has_call = ("date_from        = date_from" in chunk or
                    "date_from=date_from" in chunk)
        sig_mark  = "✓" if has_sig  else "✗"
        call_mark = "✓" if has_call else "✗"
        print(f"  {cls}: сигнатура {sig_mark}  get_messages() {call_mark}")


if __name__ == "__main__":
    main()