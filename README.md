# News Aggregator — проект за ночь

## ✅ Прогресс (отмечать по мере готовности)

### База данных (SQLite)
- [X] Модели User, UserSettings, News, Cluster, NewsCluster, UserHistory, EntryLog
- [X] Асинхронный CRUD (классы UserCRUD, SettingsCRUD, NewsCRUD, ClusterCRUD, HistoryCRUD, StatsCRUD)
- [X] Инициализация БД (init_db.py)
- [X] Создание первого админа с автоматическим паролем

### Бэкенд (FastAPI)
- [X] main.py + CORS настроен
- [X] Health check эндпоинт (/api/health)
- [X] AuthService (логин, роли, блокировка после 5 попыток) — через werkzeug
- [X] API эндпоинты:
  - [X] POST /api/auth/login
  - [X] POST /api/auth/register
  - [X] POST /api/auth/login/tg
  - [X] GET /api/auth/settings
  - [X] POST /api/auth/settings
  - [X] GET /api/news/sources
  - [X] POST /api/parser/tg
  - [X] POST /api/clusters/run/{user_id}
  - [X] POST /api/clusters/cluster (для фронта)
  - [X] GET /api/clusters/results/{user_id}
  - [X] GET /api/clusters/
  - [X] GET /api/clusters/search
  - [X] DELETE /api/clusters/history
  - [X] POST /api/clusters/{cluster_id}/tts
  - [X] POST /api/clusters/{cluster_id}/plot
  - [X] POST /api/clusters/{cluster_id}/chronology
  - [X] POST /api/clusters/plot
  - [X] GET /api/admin/stats/database
  - [X] GET /api/admin/stats/visits
  - [X] GET /api/admin/stats/users
  - [X] GET /api/admin/users/search
- [X] ParserService
  - [X] TelegramParser (работает через Telethon, нужны API ключи)
  - [ ] LentaParser (НЕ РАБОТАЕТ — требует доработки селекторов)
  - [X] Сохранение только новых новостей
- [X] AIService (SentenceTransformer + кластеризация через sklearn)
- [ ] LLMService (требуется Ollama)
- [X] TTSService (edge_tts)
- [ ] StatsService (графики matplotlib в разработке)

### Web интерфейс (HTML/CSS/JS)
- [X] Страница логина (/login)
- [X] Дашборд (/main)
- [X] История (/history)
- [X] Админ-панель (/admin)
- [X] Настройки (количество кластеров, выбор каналов, период)
- [X] Семантический поиск
- [X] Просмотр саммари кластеров
- [ ] TTS плеер (кнопка есть, требуется интеграция)
- [ ] График кластеров (кнопка есть, заглушка)
- [ ] Хронология (кнопка есть, заглушка)

### Telegram бот (aiogram 3.x)
- [ ] Команда /start (логин)
- [ ] Выбор каналов, количества кластеров
- [ ] Запуск саммари
- [ ] Прослушать подкаст
- [ ] История, хронология
- [ ] Админ-команды

### Интеграция
- [X] Сессии через localStorage (web)
- [X] Сохранение истории пользователя
- [ ] Пользовательские папки data/users/user_{id}/

### Деплой и демо
- [X] README по запуску
- [ ] Видео работы (скринкаст)
- [ ] Презентация (5-7 слайдов)

## 🚨 ТЕКУЩИЕ НЕДОЧЁТЫ (TODO)

### Критические (без них не работает основной функционал)
1. **Нет новостей в БД** — парсеры не запускаются автоматически. Нужно вручную нажать кнопку "Загрузить" для Telegram или Lenta на странице /main
2. **LentaParser не работает** — селекторы устарели. Нужно обновить CSS классы в lenta_parser.py
3. **TelegramParser требует авторизации** — при первом запуске нужно ввести номер телефона и код в консоли

### Средней важности
4. **API эндпоинт /api/clusters/cluster** добавлен, но фронт ожидает его с параметрами — работает
5. **Статистика пользователей /api/admin/stats/users** — эндпоинт добавлен
6. **TTS работает, но файлы не проигрываются** — нужно проверить путь к audio_url

### Низкой важности (косметика)
7. **Графики кластеров** — пока заглушки (HTML страницы)
8. **Хронология** — пока заглушка
9. **Ollama LLM** — не установлен, кластеризация работает без него

## 🧪 Тестирование

### Запуск всех тестов:
python tests/run_tests.py

### Отдельные тесты:
python tests/run_tests.py crud       # CRUD операции
python tests/run_tests.py parser     # Парсеры новостей
python tests/run_tests.py clustering # Кластеризация

### Структура тестов:
tests/
├── test_crud.py       # Тестирование БД и CRUD операций
├── test_parser.py     # Тестирование парсеров (Lenta, Telegram)
├── test_clustering.py # Тестирование AI кластеризации
└── run_tests.py       # Единый запускатор

### Текущий статус (2026-06-10):
| Компонент | Статус |
|-----------|--------|
| База данных (SQLite) | ✅ Работает |
| CRUD операции | ✅ Работает |
| Парсер Telegram | ✅ Работает (после авторизации) |
| Парсер Lenta.ru | ❌ Требует доработки селекторов |
| Эмбеддинги (SentenceTransformer) | ✅ Работает |
| Кластеризация (sklearn) | ✅ Работает |
| LLM (Ollama) | ❌ Не установлен (опционально) |
| API сервер | ✅ Работает на :8000 |
| Web интерфейс | ✅ Работает (кроме TTS/графиков) |
| Тест CRUD | ✅ Пройден |
| Тест парсера | ⚠️ Telegram OK, Lenta нет |
| Тест кластеризации | ✅ Пройден |

## 🚀 Запуск проекта

### 1. Установка зависимостей:
pip install -r requirements.txt

### 2. Настройка .env:
Скопируй .env.example в .env и заполни:
- TG_API_ID, TG_API_HASH (для Telegram парсера)
- BOT_TOKEN (для Telegram бота, опционально)

### 3. Инициализация БД и создание админа:
python -m app.database.init_db
# Логин: admin, Пароль: As612aj$

### 4. Запуск API сервера:
python -m app.main
# Открыть http://localhost:8000/login

### 5. Первый вход (важно!):
- Авторизуйся как admin
- На странице /main выбери каналы
- Нажми "Загрузить" для Telegram (потребуется авторизация в консоли)
- ИЛИ нажми "Сделать саммари" если новости уже есть

### 6. Запуск тестов:
python tests/run_tests.py

## 📁 Структура проекта
news_aggregator/
├── app/
│   ├── api/               # API роутеры (web, telegram)
│   │   └── web/           # Web эндпоинты (auth, clusters, news, admin, parser)
│   ├── database/          # Сессии и CRUD
│   ├── models/            # SQLAlchemy модели
│   ├── services/          # Бизнес-логика
│   │   ├── parser/        # Парсеры новостей (lenta, telegram)
│   │   ├── ai_service.py  # Эмбеддинги и кластеризация
│   │   ├── auth_service.py
│   │   ├── cluster_service.py
│   │   ├── parser_service.py
│   │   └── tts_service.py
│   ├── static/            # CSS/JS (common, login, main, history, admin)
│   ├── templates/         # HTML (login, main, history, admin, index)
│   ├── config.py
│   └── main.py            # FastAPI приложение
├── tests/                 # Тесты
├── data/                  # БД (news.db) и пользовательские файлы
├── ml_models/             # Кэш моделей AI (SentenceTransformer)
└── requirements.txt

## 🔧 Как исправить недочёты

### 1. Загрузить новости (срочно):
- Открыть http://localhost:8000/main
- Выбрать каналы (например, ТАСС, РБК)
- Нажать кнопку "Загрузить" под полем "Telegram-канал"
- Дождаться авторизации в консоли (ввести номер телефона и код)

### 2. Починить Lenta.ru:
- Открыть lenta.ru в браузере
- Найти актуальные CSS классы для статей
- Заменить в app/services/parser/lenta_parser.py селекторы

### 3. Запустить кластеризацию:
- После загрузки новостей нажать "Сделать саммари"
- Выбрать период и количество кластеров
- Дождаться результата

## 📝 Примечания

- Для работы Telegram парсера нужны API ключи от my.telegram.org
- При первом запуске Telegram парсера потребуется авторизация в консоли
- Эмбеддинги работают на CPU, модель ~470 MB (скачивается автоматически)
- Для работы TTS нужен интернет (edge_tts использует Azure)