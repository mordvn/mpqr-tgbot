# MPQR Telegram Bot

<p>
  <img src="./media/icon.gif" width="220" alt="MPQR Bot Icon">
</p>

Минималистичный Telegram-бот для:

- поддержки клиентов в topic-based менеджерской группе;
- запроса и валидации отзыва;
- выдачи подарка после проверки менеджером.

## Stack

- `Python 3.13+`
- `aiogram 3`
- `aiogram-dialog`
- `uv`
- `SQLite (aiosqlite)`
- `loguru`
- Docker / Docker Compose

## Основной флоу

- `/start` -> главное меню (`Получить подарок` / `Написать продавцу`)
- Поддержка:
  - выбор категории;
  - сообщения клиента попадают в менеджерский topic;
  - ответы менеджера доставляются клиенту;
  - менеджер может нажать `Решено, запросить отзыв`.
- Отзыв и подарок:
  - запрос номера телефона (ввод или share contact);
  - подтверждение номера;
  - отправка скриншота отзыва;
  - менеджер `Бонус отправлен` / `Отклонить`;
  - клиент получает итоговый статус.

## Команды

- `/start` — главное меню
- `/help` — сразу в поддержку
- `/review` — сразу в подарок за отзыв

## Быстрый старт (локально)

```bash
cp .env.examples .env
# заполни .env
uv sync
uv run -m app.main
```

## Запуск через Docker

```bash
docker compose up -d --build
```

## Конфиг (`.env`)

Обязательные переменные:

- `TG_BOT_TOKEN`
- `MANAGERS_GROUP_ID` (forum supergroup, обычно `-100...`)

Дополнительно:

- `BOT_USERNAME`
- `SQLITE_PATH`
- `LOG_LEVEL`
- `TZ`

## Структура проекта

```text
app/
  main.py
  config.py
  context.py
  db.py
  keyboards.py
  states.py
  texts.py
  validators.py
  telegram_safe.py
  handlers/
    user.py
    manager.py
```

## Надежность

- state и бизнес-этапы сохраняются в SQLite;
- отправки в Telegram обернуты safe-wrapper с retry для временных network/flood ошибок;
- обработаны сценарии blocked user / bad request без падения всего процесса.

## Лицензия

Проект распространяется по лицензии [GNU AGPL-3.0](./LICENSE).
