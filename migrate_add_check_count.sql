-- Миграция для добавления поля check_count в таблицу users
-- Выполните эту миграцию если у вас уже есть база данных

-- Добавляем поле check_count если его нет
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'check_count') THEN
        ALTER TABLE users ADD COLUMN check_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Поле check_count добавлено в таблицу users';
    ELSE
        RAISE NOTICE 'Поле check_count уже существует в таблице users';
    END IF;
END $$;

-- Создаем индекс для оптимизации запросов по check_count
CREATE INDEX IF NOT EXISTS idx_users_check_count ON users(check_count);

-- Обновляем существующих пользователей, устанавливая check_count = 1
-- (предполагаем, что они уже были проверены хотя бы один раз)
UPDATE users SET check_count = 1 WHERE check_count = 0; 