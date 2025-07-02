# Мультисервисная архитектура проекта

## 📁 Структура проекта

```
doom-bot/
├── app/                          # Основной сервис бота
│   ├── Dockerfile               # Dockerfile для бота
│   ├── requirements.txt         # Зависимости бота
│   ├── main.py                  # Основной код бота
│   ├── database.py              # Работа с БД
│   ├── account_analyzer.py      # Анализ аккаунтов
│   ├── llm_api.py               # API для LLM
│   └── image_utils.py           # Утилиты для изображений
├── web-dashboard/               # Веб-дашборд (будущий сервис)
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── api-gateway/                 # API Gateway (будущий сервис)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
├── media/                       # Общие медиафайлы
├── docker-compose.yml           # Основной compose
├── docker-compose.dev.yml       # Разработка
├── docker-compose.prod.yml      # Продакшн
├── init.sql                     # Инициализация БД
├── mine.env                     # Переменные окружения
├── user_session.session         # Сессия пользователя
└── bot_session.session          # Сессия бота
```

## 🐳 Docker Compose конфигурации

### Основной compose (docker-compose.yml)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    # ... конфигурация БД

  doom-bot:
    build: 
      context: ./app
      dockerfile: Dockerfile
    # ... конфигурация бота

  # Будущие сервисы:
  # web-dashboard:
  #   build: ./web-dashboard
  # api-gateway:
  #   build: ./api-gateway
```

### Разработка (docker-compose.dev.yml)
```yaml
version: '3.8'

services:
  doom-bot:
    volumes:
      - ./app:/app  # Hot reload
    environment:
      - DEBUG=true
    command: ["python", "-u", "main.py"]  # Небуферизованный вывод
```

### Продакшн (docker-compose.prod.yml)
```yaml
version: '3.8'

services:
  doom-bot:
    restart: unless-stopped
    environment:
      - DEBUG=false
    volumes:
      - ./media:/app/media:ro  # Только чтение
```

## 🚀 Команды для работы

### Запуск всех сервисов
```bash
docker-compose up -d
```

### Запуск только бота
```bash
docker-compose up doom-bot
```

### Разработка с hot reload
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Продакшн
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Сборка конкретного сервиса
```bash
docker-compose build doom-bot
```

## 📦 Добавление нового сервиса

### 1. Создать папку сервиса
```bash
mkdir new-service
cd new-service
```

### 2. Создать Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### 3. Добавить в docker-compose.yml
```yaml
services:
  new-service:
    build: ./new-service
    depends_on:
      - postgres
    networks:
      - doom_network
```

### 4. Создать .env файл для сервиса
```bash
# new-service/.env
DATABASE_URL=postgresql://doom_user:doom_password@postgres:5432/doom_bot
SERVICE_PORT=8000
```

## 🔧 Переменные окружения

### Общие переменные (mine.env)
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
FORWARD_TO_USER_ID=your_user_id
ALLOWED_CHAT_ID=your_chat_id
DATABASE_URL=postgresql://doom_user:doom_password@postgres:5432/doom_bot
```

### Переменные для разных окружений
```env
# .env.dev
DEBUG=true
LOG_LEVEL=DEBUG

# .env.prod
DEBUG=false
LOG_LEVEL=INFO
```

## 📊 Мониторинг и логи

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f doom-bot

# Последние 100 строк
docker-compose logs --tail=100 doom-bot
```

### Мониторинг ресурсов
```bash
# Использование ресурсов
docker stats

# Информация о контейнерах
docker-compose ps
```

## 🔄 Миграции и обновления

### Обновление сервиса
```bash
# Пересборка и перезапуск
docker-compose up -d --build doom-bot

# Только перезапуск
docker-compose restart doom-bot
```

### Миграции БД
```bash
# Применить миграцию
docker-compose exec postgres psql -d doom_bot -f /docker-entrypoint-initdb.d/migrate_add_check_count.sql
```

## 🛠️ Разработка

### Hot reload для Python
```yaml
# docker-compose.dev.yml
services:
  doom-bot:
    volumes:
      - ./app:/app
    command: ["python", "-u", "main.py"]
```

### Отладка
```bash
# Запуск с отладчиком
docker-compose run --service-ports doom-bot python -m pdb main.py

# Подключение к запущенному контейнеру
docker-compose exec doom-bot bash
```

## 📝 Лучшие практики

1. **Изоляция сервисов** - каждый сервис в своей папке
2. **Общие ресурсы** - БД, Redis, медиафайлы
3. **Переменные окружения** - отдельные файлы для разных сред
4. **Логирование** - централизованные логи
5. **Мониторинг** - отслеживание состояния сервисов
6. **Безопасность** - секреты в .env файлах
7. **Масштабирование** - готовность к горизонтальному масштабированию 