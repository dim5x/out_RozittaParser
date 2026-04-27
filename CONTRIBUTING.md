# Руководство для контрибьюторов

Rozitta Parser — проект в формате vibe coding. Любая помощь приветствуется, от тестирования до пул-реквестов.

## Как помочь

1. **Сообщить о баге** – создайте [Issue](https://github.com/Nynchezyabka/RozittaParser/issues). Укажите:
   - что делали,
   - что произошло,
   - логи (если есть),
   - версию ОС и приложения.
2. **Предложить исправление** – создайте Pull Request. Ориентиры:
   - основные сценарии использования описаны в `ARCHITECTURE.md`.
   - баги с наивысшим приоритетом – там же, в плане действий.
3. **Протестировать** – скачайте сборку из [Releases](https://github.com/Nynchezyabka/RozittaParser/releases) и проверьте на своих чатах.

## Разработка

- **Бинарные сборки** создаются через GitHub Actions (workflow `Build desktop binaries`). Локальный PyInstaller не используется.
- Чтобы запустить версию из исходников (для экспериментов):
  ```bash
  git clone https://github.com/Nynchezyabka/RozittaParser.git
  cd RozittaParser
  python -m venv .venv
  .venv\Scripts\activate        # Windows
  source .venv/bin/activate     # Linux/macOS
  pip install -r requirements.txt
  python main.py
Кодстайл
Проект написан в формате «vibe coding» – нет жёстких правил. Старайтесь не ломать существующую логику и не добавлять лишних зависимостей.

Где искать задачи
Issues с метками bug, enhancement, help wanted.

Три приоритетные проблемы описаны в ARCHITECTURE.md (фильтрация дат, большие видео, STT в .exe).

Спасибо за интерес!
