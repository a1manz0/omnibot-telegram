import os
import aiofiles
from telethon.tl.types import PeerUser
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest


async def get_last_messages(client, user_id, n=5):
    messages = []
    async for msg in client.iter_messages(PeerUser(user_id), limit=n):
        messages.append({
            "id": msg.id,
            "text": msg.text,
            "date": msg.date.isoformat(),
            "media": msg.media is not None
        })
    return messages


async def get_message_context(event, depth=3):
    """Получает контекст сообщения - предыдущие сообщения в цепочке ответов"""
    context_messages = []
    current_event = event
    for _ in range(depth):
        if not current_event.reply_to:
            break
            
        try:
            # Получаем сообщение, на которое отвечали
            replied_message = await current_event.get_reply_message()

            sender = await replied_message.get_sender()
            sender_name = None
            if sender:
                if hasattr(sender, 'title') and sender.title:  # для каналов/групп
                    sender_name = sender.title
                elif hasattr(sender, 'username') and sender.username:  # для пользователей
                    sender_name = sender.username

            if replied_message and replied_message.text:
                context_messages.append({
                    'text': replied_message.text,
                    'sender_id': replied_message.sender_id,
                    'sender_name': sender_name
                })
                current_event = replied_message
            else:
                break
        except Exception as e:
            print(f"Ошибка получения контекста: {e}")
            if len(context_messages) != 0:
                return list(reversed(context_messages))  # Возвращаем в хронологическом порядке
            break
    
    return list(reversed(context_messages))  # Возвращаем в хронологическом порядке


async def get_personal_channel_and_posts(client, user_id, n_posts=2):
    full = await client(GetFullUserRequest(user_id))
    channel_id = full.full_user.personal_channel_id
    if not channel_id:
        return None, []
    personal_channel = next((chat for chat in full.chats if chat.id == channel_id), None)

    if personal_channel:
        print(f"Закреплённый канал: {personal_channel.title} (@{personal_channel.username})")
    else:
        print("Закреплённый канал не найден")
    if not personal_channel:
        return None, []
    posts = []
    async for msg in client.iter_messages(personal_channel, limit=20):
        if msg.fwd_from is not None:
            continue

        posts.append({
            "id": msg.id,
            "text": msg.text,
            "media": msg.media is not None
        })
        if len(posts) >= n_posts:
            break
    return personal_channel, posts

async def download_profile_photo(client, entity, file_path):
    await client.download_profile_photo(entity, file=file_path)
    return file_path if os.path.exists(file_path) else None

async def download_media(client, message, file_path):
    if message.media:
        await client.download_media(message, file=file_path)
        return file_path if os.path.exists(file_path) else None
    return None

def build_account_json(user_id, username, full_name, channel, channel_posts, user_photo_path, channel_photo_path, post_media_paths, messages=None):

    data = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "profile_photo": user_photo_path,
        "personal_channel": {
            "title": channel.title if channel else None,
            "username": channel.username if channel else None,
            "photo": channel_photo_path,
            "last_posts": [
                {
                    "text": post["text"],
                    "media": post_media_paths.get(post["id"])
                }
                for post in channel_posts
            ]
        }
    } 
    if messages:
        data['messages'] = messages
    return data
