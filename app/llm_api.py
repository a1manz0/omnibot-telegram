from openai import OpenAI
import os
from dotenv import load_dotenv
from image_utils import encode_image_to_base64
import requests
import base64


load_dotenv(".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = 'https://openrouter.ai/api/v1'
MODELS_TO_TRY = ["mistralai/mistral-small-3.2-24b-instruct:free", "google/gemini-2.5-flash-lite-preview-06-17"]

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)

def get_antibot_prompt(account_json, user_name, chat_language="ru"):
    prompt_for_spam = f'''Определи, является ли пользователь {user_name} спам-ботом. Используй признаки:
1. Реклама, поиск работы/заработка  
2. Часто от женских имён: заготовки в виде восторженных рецензий на фильмы/сериалы/мультфильмы; шаблонные, вежливо-слащавые тексты без реакции на чат; иногда только смайлик ❤️  

— У пользователей могут быть персональные каналы. Подозрительный канал усиливает подозрение, но **только если текст уже странный**  

**Примеры спам-ботов:**
От Милая Лили
Текст: Ой, как же я рада! 😍 «Москва слезам не верит» — это же классика! Не могу дождаться, чтобы увидеть современную интерпретацию. Надеюсь, что актеры будут на высоте и атмосфера останется такой же теплой и трогательной, как в оригинале. Обязательно посмотрю! 🎬❤️
От Василиса
**Подозрения по профилю:** Аватар с девушкой
Текст: 🥰
От Yulia Naryshkina
ЗАКРЕПЛЁННЫЙ КАНАЛ ПОЛЬЗОВАТЕЛЯ:Ваши победы тут 💸💸💸 (@e16_89A_1a6_Ff9_525
Текс: Лобо? Зачем он там?

**НЕ спам-бот (NSFW-имя, но нормальное поведение):**
От Hentai_Miki  
Текст: Помню я на том моменте сериал и скипнул, стоит оно того дальше? Ведь, после этого он ещё и "добрый" вроде стал, что меня конкретно смутило.  
— Имя подозрительное, но сообщение осмысленное, не шаблонное. Пользователь — скорее аниме-фан, а не бот.

**НЕ спам-бот (резкий, но живой участник):**
От Bunaby  
Текст: Это канал по всяким военным приколам, нам тут вашей гиковской херни не надо  
— Сообщение резкое, но похоже на реакцию. Если это защита от пропаганды, а не её продвижение — не бот.

**Важно:**
- Оцени только по совокупности признаков: подозрительное сообщение + шаблонный стиль + имя + канал.
- Если сообщение единичное, короткое и могло быть опечаткой — не помечай как бота.

---
Будет представлен список из сообщений пользователя messages, в нем:
"Контекст" — это предыдущее сообщение, на которое пользователь отвечает.
"Сообщение" — это собственный текст пользователя. Обязательно обращай внимание на сообщения пользователя, если они однотипные, то это признак бота
Ответь в формате JSON: { '{' }\"thoughts\":..., \"is_bot\": true/false, \"confidence\": 0-1 { '}'}

ВАЖНО: используй язык чата — {chat_language.upper()} — для ответа в поле "thoughts".\n\nДанные: {account_json}'''
    return prompt_for_spam

def remove_none_values(obj):
    if isinstance(obj, dict):
        return {
            k: remove_none_values(v)
            for k, v in obj.items()
            if v is not None
        }
    elif isinstance(obj, list):
        return [remove_none_values(v) for v in obj]
    else:
        return obj

def preprocess_account_data_for_llm(account_json_pre):
    account_json = account_json_pre.copy()
    # Удаляем поля с изображениями
    account_json = account_json.copy()
    account_json.pop("profile_photo_base64", None)

    if "personal_channel" in account_json:
        account_json["personal_channel"] = account_json["personal_channel"].copy()
        account_json["personal_channel"].pop("photo_base64", None)

        if "posts" in account_json["personal_channel"]:
            if account_json["personal_channel"]["posts"]:
                for post in account_json["personal_channel"]["posts"]:
                    post.pop("media_base64", None)


    account_json = remove_none_values(account_json)

    if account_json.get("personal_channel") == {}:
        account_json.pop("personal_channel")
    return account_json

async def analyze_account_with_llm(account_json, chat_language="ru"):
    account_json_processed = preprocess_account_data_for_llm(account_json)
    print('account_json: ', account_json_processed)
    # Формируем сообщения для LLM
    system_prompt = "Ты фильтр, который определяет, является ли аккаунт спам-ботом."
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": get_antibot_prompt(account_json_processed, chat_language)}
            ]
        }
    ]
    if account_json['profile_photo_base64']:
        messages[1]["content"].append({
            "type": "text",
            "text": "Аватарка пользователя:"
        })

        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": account_json['profile_photo_base64']}
        })

    if account_json['personal_channel']:
        personal_channel = account_json['personal_channel']
        if personal_channel['photo_base64']:
            messages[1]["content"].append({
                "type": "text",
                "text": "Аватарка канала:"
            })

            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": personal_channel['photo_base64']}
            })
            if personal_channel['posts']:
                for p in personal_channel['posts']:
                    if p['text']:
                        messages[1]["content"].append({
                            "type": "text",
                            "text": p['text']
                        })
                    if p['media_base64']:
                        messages[1]["content"].append({
                            "type": "image_url",
                            "image_url": {"url": p['media_base64']}
                    })

    for model_name in MODELS_TO_TRY:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.01,
            )
        except Exception as e:
            print(f"Ошибка при обращении к OpenAI API модель {model_name}: {e}")
            continue 
    response = completion.choices[0].message.content
    print(f'АНТИСПАМБОТ ответ: {response}')
    return response

async def moderate_message_with_llm(message_text, user_name, image_path=None, is_bot=None, dialog_context=None, chat_language='ru', channel_name=None):
    # Формируем prompt для модерации
    channel_description = 'Канал гиковской тематики'
    sensitivity = "low"  # можно менять на high/medium в зависимости от настроек канала
    messages = []

# system prompt
    messages.append({
        "role": "system",
        "content": (
            f"""Ты модерируешь чат (канал: {channel_name}, описание канала: {channel_description}).\n
Модерируй только если сообщение направлено на живого участника ЧАТА и содержит:

1. Прямое оскорбление (пример: "ты долбоёб").
2. NSFW-контент.
3. Угрозы вреда (физического, деанон и т.п.).

НЕ флагай:
- Маты и сарказм.
- Критика канала, постов или актеров.
- Гипотетические споры или идеи.

**Сенситивность {sensitivity.upper()}**:
- LOW: флагай только очевидные нарушения.
- MEDIUM: флагай, если скорее всего нарушение.
- HIGH: флагай и потенциальные нарушения.

Ответ в JSON-формате:
{{
  "thoughts": "<объяснение>",
  "is_violating": true/false,
  "action": "warn"/"delete_and_ban"/"",
  "moderation_message": "<сообщение для пользователя, если нужно>"
}}"""
        )
    })

# добавляем диалоговый контекст
    for msg in dialog_context:  # это список словарей типа {"user": "Имя", "text": "Сообщение"}
        messages.append({
            "role": "user",
            "content": f"{msg['sender_name']}: {msg['text']}"
        })

# добавляем проверяемое сообщение
    messages.append({
        "role": "user",
        "content": f"{user_name}: {message_text}"
    })

# добавляем запрос на модерацию
    messages.append({
        "role": "user",
        "content": (
            f"Нарушает ли это последнее сообщение правила? Проверь ТОЛЬКО его. "
            f"Ответь в формате JSON, как указано выше. Язык чата — {chat_language.upper()}."
        )
    })
    if image_path:
        base64_image = encode_image_to_base64(image_path)
        if base64_image:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": base64_image}
            })

    for model_name in MODELS_TO_TRY:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.01,
            )
        except Exception as e:
            print(f"Ошибка при обращении к OpenAI API модель {model_name}: {e}")
            continue 
    response = completion.choices[0].message.content
    print(f'Для Входа: {messages}\n Ответ: {response}')
    return response 
