#!/bin/bash

# Скрипт для запуска Doom Bot в разных окружениях

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Doom Bot - Launcher Script${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Функция для проверки зависимостей
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен. Установите Docker и попробуйте снова."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
        exit 1
    fi
}

# Функция для проверки файлов конфигурации
check_config_files() {
    if [ ! -f "mine.env" ]; then
        print_warning "Файл mine.env не найден. Создайте его с необходимыми переменными окружения."
        exit 1
    fi
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "Файл docker-compose.yml не найден. Убедитесь, что вы находитесь в корневой папке проекта."
        exit 1
    fi
}

# Функция для запуска в продакшн режиме
start_production() {
    print_message "Запуск в продакшн режиме..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    print_message "Сервисы запущены в продакшн режиме!"
    print_message "Для просмотра логов: docker-compose logs -f"
}

# Функция для запуска в режиме разработки
start_development() {
    print_message "Запуск в режиме разработки..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
    print_message "Сервисы запущены в режиме разработки!"
}

# Функция для запуска только бота
start_bot_only() {
    print_message "Запуск только бота..."
    docker-compose up doom-bot
}

# Функция для простого запуска
start_simple() {
    print_message "Простой запуск..."
    docker-compose up -d
    print_message "Сервисы запущены!"
}

# Функция для остановки
stop_services() {
    print_message "Остановка сервисов..."
    docker-compose down
    print_message "Сервисы остановлены!"
}

# Функция для пересборки
rebuild_services() {
    print_message "Пересборка сервисов..."
    docker-compose up -d --build
    print_message "Сервисы пересобраны и запущены!"
}

# Функция для просмотра логов
show_logs() {
    print_message "Просмотр логов..."
    docker-compose logs -f
}

# Функция для показа статуса
show_status() {
    print_message "Статус сервисов..."
    docker-compose ps
}

# Функция для показа помощи
show_help() {
    echo "Использование: $0 [команда]"
    echo ""
    echo "Команды:"
    echo "  prod, production    - Запуск в продакшн режиме"
    echo "  dev, development    - Запуск в режиме разработки"
    echo "  bot                 - Запуск только бота"
    echo "  simple              - Простой запуск"
    echo "  stop                - Остановка сервисов"
    echo "  rebuild             - Пересборка и запуск"
    echo "  logs                - Просмотр логов"
    echo "  status              - Статус сервисов"
    echo "  help                - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 prod             # Запуск в продакшн"
    echo "  $0 dev              # Запуск для разработки"
    echo "  $0 logs             # Просмотр логов"
}

# Основная логика
main() {
    print_header
    
    # Проверка зависимостей
    check_dependencies
    check_config_files
    
    # Обработка аргументов
    case "${1:-help}" in
        "prod"|"production")
            start_production
            ;;
        "dev"|"development")
            start_development
            ;;
        "bot")
            start_bot_only
            ;;
        "simple")
            start_simple
            ;;
        "stop")
            stop_services
            ;;
        "rebuild")
            rebuild_services
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Неизвестная команда: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Запуск основной функции
main "$@" 