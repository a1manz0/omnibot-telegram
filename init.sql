-- Создание таблиц для бота

-- Таблица чатов (настройки бота для чата)
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    title VARCHAR(255),
    username VARCHAR(255),
    prompt TEXT,
    lang VARCHAR(10) DEFAULT 'ru',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    full_name VARCHAR(500),
    profile_photo_base64 TEXT, -- Изображение в base64
    is_bot BOOLEAN DEFAULT false,
    confidence DECIMAL(3,2),
    thoughts TEXT,
    check_count INTEGER NOT NULL DEFAULT 0, -- Количество проверок пользователя
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- Добавляем поле check_count если его нет (для существующих БД)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'users' AND column_name = 'check_count') THEN
        ALTER TABLE users ADD COLUMN check_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- Таблица персональных каналов пользователей
CREATE TABLE IF NOT EXISTS personal_channels (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    username VARCHAR(255),
    photo_base64 TEXT, -- Изображение в base64
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица постов из каналов
CREATE TABLE IF NOT EXISTS channel_posts (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER REFERENCES personal_channels(id) ON DELETE CASCADE,
    post_id BIGINT,
    text TEXT,
    media_base64 TEXT, -- Изображение в base64
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица сообщений пользователей
CREATE TABLE IF NOT EXISTS user_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    chat_id BIGINT,
    message_id BIGINT,
    text TEXT,
    context TEXT,
    media_base64 TEXT, -- Изображение сообщения в base64
    created_at TIMESTAMP DEFAULT NOW()
);

-- Создание индексов для производительности
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_bot ON users(is_bot);
CREATE INDEX IF NOT EXISTS idx_user_messages_user_id ON user_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_user_messages_chat_id ON user_messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_user_messages_created_at ON user_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_channel_posts_channel_id ON channel_posts(channel_id);
CREATE INDEX IF NOT EXISTS idx_personal_channels_user_id ON personal_channels(user_id);

-- Вставка начальных данных для чатов (если нужно)
INSERT INTO chats (id, title, prompt, lang) VALUES 
    (-1002160698263, 'Основной чат', 'Ты помощник в чате. Модерируй сообщения и помогай пользователям.', 'ru')
ON CONFLICT (id) DO NOTHING; 
