# Doom Bot

Telegram бот для модерации чатов с использованием AI анализа пользователей.

## Структура проекта

```
doom-bot/
├── app/                    # Основной сервис бота
│   ├── main.py            # Основной файл бота
│   ├── account_analyzer.py # Анализ аккаунтов
│   ├── llm_api.py         # API для работы с LLM
│   ├── image_utils.py     # Утилиты для работы с изображениями
│   ├── database.py        # Работа с PostgreSQL
│   ├── Dockerfile         # Docker образ для бота
│   ├── requirements.txt   # Python зависимости
│   └── .dockerignore      # Исключения для Docker
├── media/                 # Временные медиа файлы
├── docker-compose.yml     # Основной Docker Compose
├── docker-compose.dev.yml # Конфигурация для разработки
├── docker-compose.prod.yml # Конфигурация для продакшн
├── init.sql              # Инициализация базы данных
├── mine.env              # Переменные окружения
├── user_session.session  # Сессия пользователя Telegram
├── bot_session.session   # Сессия бота Telegram
└── migrate_json_to_postgres.py # Скрипт миграции данных
```

## 🚀 Быстрый запуск

### 1. Подготовка

Убедитесь, что у вас установлены:
- Docker
- Docker Compose

### 2. Настройка переменных окружения

Отредактируйте файл `mine.env`:
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=your_phone
OPENAI_API_KEY=your_openai_key
FORWARD_TO_USER_ID=your_admin_id
BOT_TOKEN=your_bot_token
ALLOWED_CHAT_ID=your_chat_id
```

### 3. Запуск

```bash
# Продакшн (с оптимизацией и мониторингом)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Разработка с hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Только бот (если БД уже запущена)
docker-compose up doom-bot

# Простой запуск (без дополнительных настроек)
docker-compose up -d
```

### 4. Остановка

```bash
docker-compose down
```

## 🛠️ Разработка

### Локальная разработка

```bash
# Запуск только PostgreSQL
docker-compose up postgres -d

# Установка зависимостей
cd app
pip install -r requirements.txt

# Запуск бота локально
python main.py
```

### Hot reload в Docker

```bash
# Запуск с автоматической перезагрузкой при изменении кода
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Отладка

```bash
# Подключение к контейнеру
docker-compose exec doom-bot bash

# Просмотр логов
docker-compose logs -f doom-bot
```

## 📊 Мониторинг

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Только бот
docker-compose logs -f doom-bot

# Последние 100 строк
docker-compose logs --tail=100 doom-bot
```

### Состояние сервисов

```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats
```

## 🗄️ База данных

Приложение использует PostgreSQL для хранения:
- Информации о пользователях
- Сообщений пользователей
- Настроек чатов
- Персональных каналов и постов
- **Изображений в формате base64** (с автоматической очисткой после N проверок)

### Оптимизация памяти

Бот автоматически очищает изображения пользователей после 5 проверок для экономии памяти:
- Экономия ~4.7GB на 1000 пользователей
- Улучшение производительности запросов
- Логичное управление данными

### Миграции

```bash
# Применить миграцию для добавления счетчика проверок
docker-compose exec postgres psql -d doom_bot -f /docker-entrypoint-initdb.d/migrate_add_check_count.sql
```

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `TELEGRAM_API_ID` | ID приложения Telegram | ✅ |
| `TELEGRAM_API_HASH` | Hash приложения Telegram | ✅ |
| `BOT_TOKEN` | Токен бота | ✅ |
| `FORWARD_TO_USER_ID` | ID админа для уведомлений | ✅ |
| `ALLOWED_CHAT_ID` | ID разрешенного чата | ✅ |
| `DATABASE_URL` | URL базы данных | ❌ (авто) |
| `DEBUG` | Режим отладки | ❌ |
| `LOG_LEVEL` | Уровень логирования | ❌ |

### Окружения

- **Разработка**: `docker-compose.dev.yml` - hot reload, отладка
- **Продакшн**: `docker-compose.prod.yml` - оптимизация, мониторинг

#### Различия между окружениями:

**Разработка (`docker-compose.dev.yml`):**
- Hot reload кода (изменения применяются автоматически)
- Подробные логи и отладка
- Интерактивный режим для отладчика
- Монтирование кода для быстрой разработки

**Продакшн (`docker-compose.prod.yml`):**
- Автоматический перезапуск сервисов
- Ограничения ресурсов (память, CPU)
- Только чтение для медиафайлов (безопасность)
- Оптимизированные настройки логирования
- Использование переменных окружения для паролей

## 📦 Добавление новых сервисов

Проект готов к мультисервисной архитектуре. Для добавления нового сервиса:

1. Создайте папку сервиса: `mkdir new-service`
2. Добавьте Dockerfile в папку сервиса
3. Обновите `docker-compose.yml`:

```yaml
services:
  new-service:
    build: ./new-service
    depends_on:
      - postgres
    networks:
      - doom_network
```

Подробная документация: [README_MULTI_SERVICE.md](README_MULTI_SERVICE.md)

## 🔄 Обновления

```bash
# Пересборка и перезапуск (продакшн)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Обновление только бота (продакшн)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build doom-bot

# Обновление в режиме разработки
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Простое обновление (без дополнительных настроек)
docker-compose up -d --build

# Применение миграций БД
docker-compose exec postgres psql -d doom_bot -f /docker-entrypoint-initdb.d/init.sql
```

## 📝 Структура базы данных

### Таблицы:
- `users` - основная информация о пользователях
- `personal_channels` - персональные каналы пользователей
- `channel_posts` - посты из каналов
- `user_messages` - сообщения пользователей
- `chats` - настройки чатов

### Особенности:
- Автоматическая очистка изображений после N проверок
- Счетчик проверок пользователей
- Оптимизированные индексы для производительности 