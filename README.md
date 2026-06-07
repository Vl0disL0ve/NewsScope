# NewsScope

Курсовой проект по ООП. Агрегатор новостей с суммаризацией и категоризацией.

---

## Авторы

| ФИО | Модули |
|-----|--------|
| **Ряжапов Даниил Ринатович** | `parser` (базовый парсер, RSS-парсер, веб-скрапер, менеджер парсеров), `ai_agent` (суммаризатор, промпты, клиент LLM) |
| **Арямнов Владислав Андреевич** | `frontend` (админка, история, логин, главная, общие компоненты), `telegram_bot` (бот, хендлеры, клавиатуры, middleware) |
| **Общие модули** | `database` (сессия БД, модели, репозитории), `backend` (API, сервисы, ядро, фоновые задачи, middleware) — разрабатываются совместно |

## Структура проекта

- **backend** — основной контроллер приложения
  - принимает запросы от пользователей через фронтенд и Telegram-бота
  - управляет работой парсера и взаимодействием с базой данных
  - содержит бизнес-логику суммаризации, категоризации и обработки новостей
  - `main.py` — точка входа для запуска веб-сервера (FastAPI/Uvicorn)
  - `core/`
    - `config.py` — все настройки приложения: секреты, URL базы данных, ключи API
    - `orchestrator.py` — главный дирижёр процессов: запуск парсинга → суммаризация → сохранение → уведомление
    - `scheduler.py` — планировщик фоновых задач по расписанию (cron-правила)
    - `dependencies.py` — внедрение зависимостей FastAPI (получение сессии БД, сервисов)
  - `api/`
    - `router.py` — сборка всех эндпоинтов в единый API-роутер
    - `endpoints/`
      - `news.py` — получение списка новостей и конкретной новости по ID
      - `summary.py` — получение последней сводки и запуск генерации новой
      - `auth.py` — аутентификация (логин, пароль, JWT-токены)
      - `sources.py` — управление источниками новостей (добавить, удалить, список)
      - `health.py` — проверка живости сервиса для мониторинга
    - `schemas/`
      - `news.py` — Pydantic-схемы: формат ответа со списком новостей
      - `summary.py` — схемы запроса на генерацию и ответа со сводкой
      - `auth.py` — схемы для логина и токенов
      - `common.py` — общие схемы: пагинация, статус-сообщения, ошибки
    - `middleware/`
      - `auth_middleware.py` — проверка JWT-токена перед запросом
      - `cors_middleware.py` — правила CORS для доступа веб-фронтенда
      - `logging_middleware.py` — логирование всех входящих HTTP-запросов
  - `services/`
    - `news_service.py` — бизнес-логика фильтрации, пагинации и поиска новостей
    - `summary_service.py` — управление процессом суммаризации (получить текст → отправить в ai_agent → сохранить)
    - `source_service.py` — CRUD-операции для источников новостей
    - `notification_service.py` — рассылка уведомлений (дёргает Telegram-бота, почту)
  - `tasks/`
    - `worker.py` — настройка фонового воркера (Celery / ARQ)
    - `parsing_task.py` — фоновая задача «запустить парсер для источника X»
    - `summary_task.py` — фоновая задача «сгенерировать сводку за сегодня»
  - `utils/`
    - `logger.py` — единый логгер для всего приложения
    - `exceptions.py` — кастомные исключения (новость не найдена, ошибка ИИ-сервиса)

- **frontend** — веб-сайт агрегатора
  - отображает ленту новостей, категории, графики кластеров
  - взаимодействует с backend через API
  - `admin/` — админ-панель управления
    - `admin.html`, `admin.css`, `admin.js`
  - `common/` — общие ресурсы для всех страниц
    - `common.css`, `common.js`
    - `components/` — переиспользуемые UI-компоненты (карточка новости, кнопка)
  - `history/` — страница истории новостей
    - `history.html`, `history.css`, `history.js`
  - `login/` — страница входа в систему
    - `login.html`, `login.css`, `login.js`
  - `main/` — главная страница с лентой и дайджестом
    - `main.html`, `main.css`, `main.js`
  - `static/` — скомпилированные или внешние статические файлы

- **telegram_bot** — интерфейс доступа через Telegram
  - принимает команды и отправляет новости, сводки, озвучку
  - обращается к backend за данными
  - `bot.py` — главный файл бота: инициализация, диспетчер, запуск поллинга
  - `handlers/`
    - `start.py` — обработчик команды /start
    - `latest.py` — обработчик команды /latest (последний дайджест)
    - `subscribe.py` — обработчик команды /subscribe (подписка на рассылку)
  - `keyboards/`
    - `main_menu.py` — клавиатуры с кнопками главного меню
  - `middlewares/`
    - `logging.py` — логирование входящих сообщений от пользователей

- **parser** — сборщик новостей из внешних источников
  - парсер внешних сайтов
  - парсер Telegram-каналов
  - `base_parser.py` — абстрактный класс парсера с общим интерфейсом
  - `rss_parser.py` — парсер RSS-лент (XML → список новостей)
  - `web_scraper.py` — парсер HTML-страниц (Playwright / BeautifulSoup)
  - `parser_manager.py` — управление запуском всех парсеров по расписанию
  - `test.py` — тесты парсера на контрольных URL

- **database** — хранение данных
  - новости, категории, кластеры, хронология, аудиофайлы озвучки
  - `session.py` — настройка подключения к БД (engine, SessionLocal)
  - `models.py` — ORM-модели таблиц (News, Summary, User, Source)
  - `repository/`
    - `base.py` — базовый репозиторий с общими CRUD-операциями
    - `news_repo.py` — специфические запросы к таблице новостей

- **ai_agent** — модуль искусственного интеллекта для обработки контента
  - `summarizer.py` — основная логика суммаризации: приём текста → формирование промпта → вызов LLM → возврат сжатого текста
  - `prompts.py` — шаблоны промптов для разных задач (суммаризация, выделение ключевых тем, категоризация)
  - `llm_client.py` — клиент для общения с API языковых моделей (OpenAI, Anthropic, локальная LLM)

## Чеклист текущих фич
- [x] Completed
- [ ] In Progress

- [ ] Реализация backend
  - [ ] main.py
  - [ ] core
    - [ ] config.py
    - [ ] orchestrator.py
    - [ ] scheduler.py
    - [ ] dependencies.py
  - [ ] api
    - [ ] router.py
    - [ ] endpoints
      - [ ] news.py
      - [ ] summary.py
      - [ ] auth.py
      - [ ] sources.py
      - [ ] health.py
    - [ ] schemas
      - [ ] news.py
      - [ ] summary.py
      - [ ] auth.py
      - [ ] common.py
    - [ ] middleware
      - [ ] auth_middleware.py
      - [ ] cors_middleware.py
      - [ ] logging_middleware.py
  - [ ] services
    - [ ] news_service.py
    - [ ] summary_service.py
    - [ ] source_service.py
    - [ ] notification_service.py
  - [ ] tasks
    - [ ] worker.py
    - [ ] parsing_task.py
    - [ ] summary_task.py
  - [ ] utils
    - [ ] logger.py
    - [ ] exceptions.py

- [ ] Реализация frontend
  - [ ] admin
    - [ ] admin.html
    - [ ] admin.css
    - [ ] admin.js
  - [ ] common
    - [ ] common.css
    - [ ] common.js
    - [ ] components
  - [ ] history
    - [ ] history.html
    - [ ] history.css
    - [ ] history.js
  - [ ] login
    - [ ] login.html
    - [ ] login.css
    - [ ] login.js
  - [ ] main
    - [ ] main.html
    - [ ] main.css
    - [ ] main.js
  - [ ] static

- [ ] Реализация telegram_bot
  - [ ] bot.py
  - [ ] handlers
    - [ ] start.py
    - [ ] latest.py
    - [ ] subscribe.py
  - [ ] keyboards
    - [ ] main_menu.py
  - [ ] middlewares
    - [ ] logging.py

- [ ] Реализация parser
  - [ ] base_parser.py
  - [ ] rss_parser.py
  - [ ] web_scraper.py
  - [ ] parser_manager.py
  - [ ] test.py

- [ ] Реализация database
  - [ ] session.py
  - [ ] models.py
  - [ ] repository
    - [ ] base.py
    - [ ] news_repo.py

- [ ] Реализация ai_agent
  - [ ] summarizer.py
  - [ ] prompts.py
  - [ ] llm_client.py