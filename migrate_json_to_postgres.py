#!/usr/bin/env python3
"""
Скрипт для миграции данных из accounts_db.json в PostgreSQL
"""

import json
import asyncio
import os
from dotenv import load_dotenv
from app.database import db
from app.image_utils import encode_image_to_base64

load_dotenv("mine.env")

async def migrate_json_to_postgres():
    """Мигрирует данные из JSON файла в PostgreSQL"""
    
    # Подключаемся к базе данных
    await db.connect()
    print("Подключение к базе данных установлено")
    
    try:
        # Загружаем JSON данные
        with open('accounts_db.json', 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
        
        print(f"Найдено {len(accounts_data)} пользователей для миграции")
        
        migrated_count = 0
        error_count = 0
        
        for user_id_str, user_data in accounts_data.items():
            try:
                user_id = int(user_id_str)
                
                # Конвертируем изображения в base64
                profile_photo_base64 = None
                if user_data.get('profile_photo') and os.path.exists(user_data['profile_photo']):
                    try:
                        profile_photo_base64 = encode_image_to_base64(user_data['profile_photo'])
                    except Exception as e:
                        print(f"Ошибка конвертации фото профиля для {user_id}: {e}")
                
                # Обрабатываем персональный канал
                personal_channel = user_data.get('personal_channel', {})
                channel_photo_base64 = None
                if personal_channel.get('photo') and os.path.exists(personal_channel['photo']):
                    try:
                        channel_photo_base64 = encode_image_to_base64(personal_channel['photo'])
                    except Exception as e:
                        print(f"Ошибка конвертации фото канала для {user_id}: {e}")
                
                # Обрабатываем посты канала
                posts_with_media = []
                for post in personal_channel.get('last_posts', []):
                    post_data = {'text': post.get('text', ''), 'media_base64': None}
                    if post.get('media') and os.path.exists(post['media']):
                        try:
                            post_data['media_base64'] = encode_image_to_base64(post['media'])
                        except Exception as e:
                            print(f"Ошибка конвертации медиа поста для {user_id}: {e}")
                    posts_with_media.append(post_data)
                
                # Подготавливаем данные для базы
                db_user_data = {
                    'user_id': user_id,
                    'username': user_data.get('username'),
                    'first_name': user_data.get('first_name'),
                    'last_name': user_data.get('last_name'),
                    'full_name': user_data.get('full_name'),
                    'profile_photo_base64': profile_photo_base64,
                    'is_bot': user_data.get('is_bot', False),
                    'confidence': user_data.get('confidence'),
                    'thoughts': user_data.get('thoughts'),
                    'personal_channel': {
                        'title': personal_channel.get('title'),
                        'username': personal_channel.get('username'),
                        'photo_base64': channel_photo_base64,
                        'last_posts': posts_with_media
                    }
                }
                
                # Сохраняем пользователя
                await db.save_user(db_user_data)
                
                # Сохраняем сообщения
                messages = user_data.get('messages', [])
                for i, message in enumerate(messages):
                    # Парсим сообщение для извлечения контекста
                    context = None
                    text = message
                    
                    if message.startswith('Контекст:'):
                        parts = message.split('\nСообщение:', 1)
                        if len(parts) == 2:
                            context = parts[0].replace('Контекст:', '').strip()
                            text = parts[1].strip()
                        else:
                            parts = message.split('\nСообщение аккаунта:', 1)
                            if len(parts) == 2:
                                context = parts[0].replace('Контекст:', '').strip()
                                text = parts[1].strip()
                    
                    await db.save_user_message(
                        user_id=user_id,
                        chat_id=-1002160698263,  # Используем дефолтный чат
                        message_id=i + 1,
                        text=text,
                        context=context,
                        media_base64=None  # В старых данных нет медиа сообщений
                    )
                
                migrated_count += 1
                print(f"Мигрирован пользователь {user_id}")
                
            except Exception as e:
                error_count += 1
                print(f"Ошибка при миграции пользователя {user_id_str}: {e}")
        
        print(f"\nМиграция завершена!")
        print(f"Успешно мигрировано: {migrated_count}")
        print(f"Ошибок: {error_count}")
        
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
    
    finally:
        # Закрываем соединение с базой данных
        await db.close()
        print("Соединение с базой данных закрыто")

if __name__ == "__main__":
    asyncio.run(migrate_json_to_postgres()) 