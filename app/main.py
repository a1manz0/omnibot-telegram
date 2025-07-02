import os
from pathlib import Path
import json
import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import PeerUser
from telethon.tl.types import Channel, Chat, PeerChannel
from telethon.tl.functions.channels import GetFullChannelRequest
from dotenv import load_dotenv
from account_analyzer import (
    get_last_messages, get_personal_channel_and_posts, get_message_context,
    download_profile_photo, download_media, build_account_json
)
from telethon.tl.custom import Button  # Импортируем Button для inline-кнопок
from llm_api import analyze_account_with_llm, moderate_message_with_llm
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch, User
from image_utils import encode_image_to_base64
from database import db


# load_dotenv("mine.env")

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

TOTAL_ACCOUT_CHECKS = 1
IGNORED_USER_IDS = [8045161528, 7347675444, -1001705454724]

session_dir = Path("/data/session")
session_dir.mkdir(parents=True, exist_ok=True)

user_session = session_dir / "user"
bot_session = session_dir / "bot"

user_client = TelegramClient(str(user_session), TELEGRAM_API_ID, TELEGRAM_API_HASH)

bot_client = TelegramClient(str(bot_session), TELEGRAM_API_ID, TELEGRAM_API_HASH).start(bot_token=BOT_TOKEN)

# ID пользователя, которому пересылать сообщения
# Замените на ID пользователя или админа
forward_to_user_id = int(os.getenv('FORWARD_TO_USER_ID', "0"))
# Замените на ID пользователя или админа
allowed_chat_id = int(os.getenv('ALLOWED_CHAT_ID', "0"))
ALLOWED_CHAT_IDS = [
    allowed_chat_id,
    -1001864529853
    # -1001393881014
]


def delete_local_files(file_paths):
    """Удаляет список локальных файлов."""
    for path in file_paths:
        try:
            if Path(path).exists() and Path(path).is_file():
                os.remove(path)
                print(f"Удален локальный файл: {path}")
            else:
                print(
                    f"Файл не найден или не является файлом, пропуск удаления: {path}")
        except Exception as e:
            print(f"Ошибка при удалении файла {path}: {e}")


async def get_linked_chat_or_channel(client, chat):
    if isinstance(chat, Channel):
        try:
            full = await client(GetFullChannelRequest(chat))
            if full.full_chat.linked_chat_id:
                # Это значит, что у канала есть связанная группа (обсуждение)
                linked = await client.get_entity(PeerChannel(full.full_chat.linked_chat_id))
                return linked
        except Exception as e:
            print(f"Ошибка при получении привязанного чата: {e}")
    return None


async def resolve_user_info(client, event):
    """
    Возвращает информацию об отправителе сообщения:
    - username
    - полное имя
    - user_id
    - user-объект (если нашли)
    Если не удалось — вернёт только user_id.
    """
    user = None

    # 1. Пробуем получить напрямую
    try:
        user = await event.get_sender()
    except:
        pass

    # 2. Если не удалось — ищем среди участников
    if not user or not isinstance(user, User):
        try:
            chat = await event.get_chat()
            offset = 0
            limit = 200

            while True:
                participants = await client(GetParticipantsRequest(
                    channel=chat,
                    filter=ChannelParticipantsSearch(""),
                    offset=offset,
                    limit=limit,
                    hash=0
                ))

                if not participants.users:
                    break

                for u in participants.users:
                    if u.id == event.sender_id:
                        user = u
                        break

                if user:
                    break

                offset += len(participants.users)

        except Exception as e:
            print(f"Ошибка при поиске участника в чате: {e}")

    # 3. Собираем информацию
    if user and isinstance(user, User):
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return {
            "user_id": user.id,
            "username": f"@{user.username}" if user.username else None,
            "full_name": full_name if full_name else None,
            "user": user
        }
    else:
        return {
            "user_id": event.sender_id,
            "username": None,
            "full_name": None,
            "user": None
        }

# @user_client.on(events.NewMessage(incoming=True, chats=ALLOWED_CHAT_IDS))


@user_client.on(events.NewMessage(chats=ALLOWED_CHAT_IDS))
async def handler(event):
    user_id = event.sender_id
    chat_id = event.chat_id
    message_text = event.raw_text

    if chat_id not in ALLOWED_CHAT_IDS:
        return

    if int(user_id) in IGNORED_USER_IDS:
        print('Игнорируем')
        return

    chat = await event.get_chat()
    linked_channel = await get_linked_chat_or_channel(user_client, chat)
    if linked_channel:
        print(f"Привязанный канал: {linked_channel.title}")
    else:
        print('Нет привязки')

    # Создание контекста диалога
    dialog_context = ""
    if event.reply_to:
        dialog_context = await get_message_context(event)
    if dialog_context:
        print(f"Найдено {len(dialog_context)} сообщений контекста")

    # Формируем контекст для промпта
    context_text = ""
    if dialog_context:
        context_text = ""
        for i, msg in enumerate(dialog_context, 1):
            if msg['sender_name'] != None:
                context_text += f"""\nОт {msg['sender_name']
                                        }: {msg['text'][:100]}"""
            else:
                context_text += f"""\nОт {msg['sender_name']
                                        }: {msg['text'][:100]}"""

    files_to_delete = []
    message_media_base64 = None
    if event.media and hasattr(event.media, 'photo'):
        # Скачиваем изображение во временный файл
        temp_image_path = f"media/message_{event.id}_media.jpg"
        files_to_delete.append(temp_image_path)
        await download_media(user_client, event.message, temp_image_path)
        # Конвертируем в base64
        message_media_base64 = encode_image_to_base64(temp_image_path)


    # Получаем информацию о пользователе
    user_data = await resolve_user_info(user_client, event)
    full_name = user_data['full_name']
    username = user_data['username']
    user = user_data['user']

    name_for_current_user = None
    if full_name:
        name_for_current_user = full_name
    elif username:
        name_for_current_user = username
    else:
        name_for_current_user = user_id

    # Проверяем, есть ли пользователь в базе данных
    existing_user = await db.get_user_with_data(user_id)
    is_bot = False

    if existing_user:


        if await db.should_check_user(user_id):
            print('Доп. проверка')

            await db.save_user_message(user_id, chat_id, event.id, message_text, context_text, message_media_base64 or "")

            updated_user_data = await db.get_user_with_data(user_id)
            messages = existing_user.get('messages', [])

            if updated_user_data:

                # Анализируем с LLM
                llm_result = await analyze_account_with_llm(updated_user_data)
                try:
                    llm_result_json = json.loads(llm_result)
                except Exception:
                    print('Ошибка парсинга антиспам JSON')
                    llm_result_json = {"thoughts": llm_result,
                                       "is_bot": False, "confidence": 0}
                # Сохраняем сообщение в базу данных
                # Обновляем результаты анализа
                await db.update_user_analysis(
                    user_id,
                    llm_result_json.get("is_bot", False),
                    llm_result_json.get("confidence", 0),
                    llm_result_json.get("thoughts", "")
                )
                is_bot = llm_result_json.get("is_bot", False)
        else:
            print('Доп. проверка не требуется')
            # Используем существующие данные
            is_bot = existing_user.get('is_bot', False)
    else:

        print(f'Пользователь не найден в базе данных, анализируем...')

        # Собираем информацию об аккаунте
        try:
            channel, posts = await get_personal_channel_and_posts(user_client, user_id, n_posts=2)
        except Exception as e:
            print('ОШИБКА ПРИ ПОЛУЧЕНИИ КАНАЛА И ПОСТОВ', e)
            channel, posts = None, []

        # Скачиваем и конвертируем изображения в base64
        user_photo_base64 = None
        if user:
            user_photo_path = f"media/user_{user_id}_photo.jpg"
            files_to_delete.append(user_photo_path)
            await download_profile_photo(user_client, user, user_photo_path)
            user_photo_base64 = encode_image_to_base64(user_photo_path)

        channel_photo_base64 = None
        if channel:
            channel_photo_path = f"media/channel_{channel.id}_photo.jpg"
            files_to_delete.append(channel_photo_path)
            await download_profile_photo(user_client, channel, channel_photo_path)
            channel_photo_base64 = encode_image_to_base64(channel_photo_path)

        # Обрабатываем посты
        posts_with_media = []
        for post in posts:
            post_data = {'text': post['text'], 'media_base64': None}
            if post["media"]:
                post_media_path = f"media/post_{post['id']}_media.jpg"
                files_to_delete.append(post_media_path)
                msg_obj = await user_client.get_messages(channel, ids=post["id"])
                await download_media(user_client, msg_obj, post_media_path)
                post_data['media_base64'] = encode_image_to_base64(
                    post_media_path)
            posts_with_media.append(post_data)

        # Формируем данные пользователя
        user_data_for_db = {
            'user_id': user_id,
            'username': username,
            'full_name': full_name,
            'profile_photo_base64': user_photo_base64,
            'personal_channel': {
                'title': channel.title if channel else None,
                'username': channel.username if channel else None,
                'photo_base64': channel_photo_base64,
                'last_posts': posts_with_media
            }
        }

        # Сохраняем пользователя в базу данных
        await db.save_user(user_data_for_db)

        await db.save_user_message(user_id, chat_id, event.id, message_text, context_text, message_media_base64 or "")
        # Получаем полные данные для анализа
        account_json = await db.get_user_with_data(user_id)
        if account_json:
            llm_result = await analyze_account_with_llm(account_json)
            try:
                llm_result_json = json.loads(llm_result)
            except Exception:
                print('Ошибка парсинга антиспам JSON')
                llm_result_json = {"thoughts": llm_result,
                                   "is_bot": False, "confidence": 0}

            # Обновляем результаты анализа
            await db.update_user_analysis(
                user_id,
                llm_result_json.get("is_bot", False),
                llm_result_json.get("confidence", 0),
                llm_result_json.get("thoughts", "")
            )
            is_bot = llm_result_json.get("is_bot", False)


    # Модерация сообщения
    moderation_result = await moderate_message_with_llm(
        message_text,
        name_for_current_user,
        image_path=None,  # Теперь изображение уже в base64 в БД
        is_bot=is_bot,
        dialog_context=dialog_context,
        channel_name=linked_channel
    )
    try:
        moderation_json = json.loads(moderation_result)
    except Exception:
        print('Ошибка парсинга модерации JSON')
        moderation_json = {"thoughts": moderation_result,
                           "is_violating": False, "action": "", "moderation_message": ""}

    # Удаляем временные файлы
    if len(files_to_delete) > 0:
        delete_local_files(files_to_delete)

    # Обработка результатов модерации
    violating_user_id = user_id
    violating_chat_id = chat_id
    if is_bot:
        # Получаем актуальные данные пользователя для отображения
        current_user = await db.get_user_with_data(user_id)
        reason = current_user.get(
            'thoughts', 'Причина не указана') if current_user else 'Причина не указана'
        confidence = current_user.get('confidence', 0) if current_user else 0
        original_text = event.message.text

        if event.chat_id:
            chat_entity = await event.get_chat()
            if hasattr(chat_entity, 'username') and chat_entity.username:
                message_link = f"""https://t.me/{
                    chat_entity.username}/{event.id}"""
            else:
                chat_id_clean = str(event.chat_id).replace(
                    '-100', '') if str(event.chat_id).startswith('-100') else str(event.chat_id)
                message_link = f"https://t.me/c/{chat_id_clean}/{event.id}"

        if original_text != "":
            forward_message_text = (
                f"🚨 **Обнаружен спам-бот!** 🚨\n"
                f"**Причина:** `{reason}`\n"
                f"**Уверенность:** `{confidence}`\n"
                f"**Действие модератора:** `Удалить сообщение и забанить`\n"
                f"\n**Оригинальное сообщение:**\n"
                f"```{original_text}\n```\n"
                f"🔗 [Перейти к сообщению]({message_link})" if message_link else ""
                f"\n\n**Действия:**"
            )
        else:
            forward_message_text = (
                f"🚨 **Обнаружено нарушение!** 🚨\n"
                f"**Причина:** `{reason}`\n"
                f"**Действие модератора:** `Удалить сообщение и забанить`\n"
                f"\n🔗 [Перейти к сообщению]({message_link})" if message_link else ""
                f"\n\n**Действия:**"
            )

        buttons = [
            [
                Button.inline("❌ Забанить", data=f"ban_{violating_user_id}_{violating_chat_id}"),
                Button.inline("🔇 Замьютить (1ч)", data=f"mute_1h_{violating_user_id}_{violating_chat_id}")
            ],
            [
                Button.inline("⚠️ Предупредить", data=f"warn_{violating_user_id}_{violating_chat_id}"),
                Button.inline("🔄 Сбросить счетчик", data=f"reset_warn_{violating_user_id}_{violating_chat_id}") # Новая кнопка
            ]
        ]

        await bot_client.send_message(
            forward_to_user_id,
            forward_message_text,
            parse_mode='md',
            buttons=buttons
        )

    elif moderation_json['is_violating']:
        action = moderation_json.get("action", "Неизвестное действие")
        reason = moderation_json.get("thoughts", 'Причина отсутствует')
        moderation_message = moderation_json.get("moderation_message", "Сообщение модератора отсутствует")
        original_text = event.message.text
        current_warnings = 0

        if event.chat_id:
            chat_entity = await event.get_chat()
            if hasattr(chat_entity, 'username') and chat_entity.username:
                message_link = f"""https://t.me/{
                    chat_entity.username}/{event.id}"""
            else:
                chat_id_clean = str(event.chat_id).replace(
                    '-100', '') if str(event.chat_id).startswith('-100') else str(event.chat_id)
                message_link = f"https://t.me/c/{chat_id_clean}/{event.id}"

        if original_text != "":
            forward_message_text = (
                f"🚨 **Обнаружено нарушение!** 🚨\n"
                f"**Причина:** `{reason}`\n"
                f"**Текущие предупреждения:** `{current_warnings}`\n"
                f"**Действие модератора:** `{action}`\n"
                f"**Сообщение модератора:** `{moderation_message}`\n"
                f"\n**Оригинальное сообщение:**\n"
                f"```{original_text}\n```\n"
                f"""🔗 [Перейти к сообщению]({
                    message_link})""" if message_link else ""
                f"\n\n**Действия:**"
            )
        else:
            forward_message_text = (
                f"🚨 **Обнаружено нарушение!** 🚨\n"
                f"**Причина:** `{reason}`\n"

                f"**Действие модератора:** `{action}`\n"
                f"**Сообщение модератора:** `{moderation_message}`\n"
                f"\n🔗 [Перейти к сообщению]({message_link})" if message_link else ""
                f"\n\n**Действия:**"
            )

        buttons = [
            [
                Button.inline("❌ Забанить", data=f"ban_{violating_user_id}_{violating_chat_id}"),
                Button.inline("🔇 Замьютить (1ч)", data=f"mute_1h_{violating_user_id}_{violating_chat_id}")
            ],
            [
                Button.inline("⚠️ Предупредить", data=f"warn_{violating_user_id}_{violating_chat_id}"),
                Button.inline("🔄 Сбросить счетчик", data=f"reset_warn_{violating_user_id}_{violating_chat_id}") # Новая кнопка
            ]
        ]

        await bot_client.send_message(
            forward_to_user_id,
            forward_message_text,
            parse_mode='md',
            buttons=buttons
        )

async def main():
    # Подключаемся к базе данных
    await db.connect()
    print("Подключение к базе данных установлено")

    # Запускаем клиенты
    await user_client.start()
    await bot_client.start()

    try:
        await asyncio.gather(
            user_client.run_until_disconnected(),  # Держим user_client активным
            bot_client.run_until_disconnected()   # Держим bot_client активным
        )
    finally:
        # Закрываем соединение с базой данных
        await db.close()
        print("Соединение с базой данных закрыто")

if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
