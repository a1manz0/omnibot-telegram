import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, BigInteger, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlalchemy import func, case


Base = declarative_base()

# Модели данных


class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    full_name = Column(String(500))
    profile_photo_base64 = Column(Text)
    is_bot = Column(Boolean, default=False)
    confidence = Column(Float)
    thoughts = Column(Text)
    check_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Отношения
    personal_channel = relationship(
        "PersonalChannel", back_populates="user", uselist=False)
    messages = relationship("UserMessage", back_populates="user")


class PersonalChannel(Base):
    __tablename__ = 'personal_channels'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'))
    title = Column(String(255))
    username = Column(String(255))
    photo_base64 = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="personal_channel")
    posts = relationship("ChannelPost", back_populates="channel")


class ChannelPost(Base):
    __tablename__ = 'channel_posts'

    id = Column(BigInteger, primary_key=True)
    channel_id = Column(Integer, ForeignKey(
        'personal_channels.id', ondelete='CASCADE'))
    post_id = Column(BigInteger)
    text = Column(Text)
    media_base64 = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    channel = relationship("PersonalChannel", back_populates="posts")


class UserMessage(Base):
    __tablename__ = 'user_messages'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'))
    chat_id = Column(BigInteger)
    message_id = Column(BigInteger)
    text = Column(Text)
    context = Column(Text)
    media_base64 = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="messages")


class DatabaseSQLAlchemy:
    def __init__(self):
        self.database_url = os.getenv(
            'DATABASE_URL', 'postgresql://doom_user:doom_password@localhost:5432/doom_bot')
        # Конвертируем в async URL
        self.async_database_url = self.database_url.replace(
            'postgresql://', 'postgresql+asyncpg://')
        self.engine = None
        self.session_factory = None
        self.MAX_CHECKS_BEFORE_CLEANUP = 3

    async def connect(self):
        """Подключение к базе данных"""
        self.engine = create_async_engine(
            self.async_database_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=10,
            echo_pool=True,        # 👈 Покажет работу пула
            echo=False
        )
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        print("Подключение к базе данных SQLAlchemy установлено")

    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.engine:
            await self.engine.dispose()

    async def save_user_message(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        text: str,
        context: Optional[str] = None,
        media_base64: Optional[str] = None
    ) -> bool:
        """Сохраняет сообщение пользователя в базу данных"""
        async with self.session_factory() as session:
            msg = UserMessage(
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                context=context,
                media_base64=media_base64,
                created_at=datetime.utcnow()
            )
            session.add(msg)
            await session.commit()
        return True

    async def get_user_with_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя с его каналом, сообщениями и постами в канале, игнорируя служебные поля"""
        async with self.session_factory() as session:
            stmt = (
                select(User)
                .where(User.id == user_id)
                .options(
                    selectinload(User.messages),
                    selectinload(User.personal_channel).selectinload(
                        PersonalChannel.posts)
                )
            )
            result = await session.execute(stmt)
            user: Optional[User] = result.scalar_one_or_none()

            if not user:
                return None

            posts = [
                {
                    "text": post.text,
                    "media_base64": post.media_base64
                }
                for post in user.personal_channel.posts
            ]
            return {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name,
                "profile_photo_base64": user.profile_photo_base64,
                "is_bot": user.is_bot,
                "confidence": user.confidence,
                "thoughts": user.thoughts,
                "messages": [
                    f"""Контекст: {msg.context or ''} \n Сообщение: {
                        msg.text or ''}""".strip()
                    for msg in user.messages
                    if msg.text or msg.context
                ],
                "personal_channel": {
                    "title": user.personal_channel.title,
                    "username": user.personal_channel.username,
                    "photo_base64": user.personal_channel.photo_base64,
                    "posts": posts if posts else None
                } if user.personal_channel else None
            }

    async def update_user_analysis(
        self,
        user_id: int,
        is_bot: bool,
        confidence: float,
        thoughts: str
    ) -> bool:
        """Обновляет анализ пользователя от LLM, увеличивает счётчик проверок и очищает изображения при необходимости"""
        async with self.session_factory() as session:
            # Обновляем и сразу получаем новый check_count
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(
                    is_bot=is_bot,
                    confidence=confidence,
                    thoughts=thoughts,
                    check_count=case(
                        (User.check_count == None, 1),
                        else_=User.check_count + 1
                    ),
                    updated_at=datetime.utcnow()
                )
                .returning(User.check_count)
            )
            result = await session.execute(stmt)
            check_count = result.scalar()
            print(f"Updated check_count: {check_count}")

            await session.commit()
            # Если лимит достигнут — очищаем изображения
            if check_count >= self.MAX_CHECKS_BEFORE_CLEANUP:
                print(f"""Очищаем изображения пользователя {
                    user_id} после {check_count} проверок""")
                await self.cleanup_user_images(user_id)

        return True

    async def should_check_user(self, user_id: int) -> bool:
        """Проверяет, нужно ли проверять пользователя"""
        async with self.session_factory() as session:
            stmt = select(User.check_count).where(User.id == user_id)
            result = await session.execute(stmt)
            check_count = result.scalar()

            print(f"CHECK_COUNT: {check_count}")
            return check_count is None or check_count < self.MAX_CHECKS_BEFORE_CLEANUP

    async def cleanup_user_images(self, user_id: int) -> bool:
        """Очищает изображения пользователя после достижения лимита проверок"""
        async with self.session_factory() as session:
            # Очищаем изображение профиля
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(profile_photo_base64=None)
            )

            # Очищаем изображение канала
            await session.execute(
                update(PersonalChannel)
                .where(PersonalChannel.user_id == user_id)
                .values(photo_base64=None)
            )

            # Очищаем изображения постов
            await session.execute(
                update(ChannelPost)
                .where(ChannelPost.channel_id.in_(
                    select(PersonalChannel.id).where(
                        PersonalChannel.user_id == user_id)
                ))
                .values(media_base64=None)
            )

            # Очищаем изображения сообщений
            await session.execute(
                update(UserMessage)
                .where(UserMessage.user_id == user_id)
                .values(media_base64=None)
            )

            await session.commit()
        return True

    async def should_cleanup_images(self, user_id: int) -> bool:
        """Проверяет, нужно ли очистить изображения пользователя"""
        async with self.session_factory() as session:
            stmt = select(User.check_count).where(User.id == user_id)
            result = await session.execute(stmt)
            check_count = result.scalar()
            return check_count >= self.MAX_CHECKS_BEFORE_CLEANUP if check_count else False

    async def save_user(self, user_data: Dict[str, Any]) -> bool:
        """Сохранение пользователя с использованием SQLAlchemy"""
        async with self.session_factory() as session:
            # Создаем или обновляем пользователя
            user = User(
                id=user_data['user_id'],
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                full_name=user_data.get('full_name'),
                profile_photo_base64=user_data.get('profile_photo_base64'),
                is_bot=user_data.get('is_bot', False),
                confidence=user_data.get('confidence'),
                thoughts=user_data.get('thoughts')
            )

            await session.merge(user)  # merge автоматически создает или обновляет

            # Сохраняем канал если есть
            if user_data.get('personal_channel'):
                channel_data = user_data['personal_channel']
                channel = PersonalChannel(
                    user_id=user_data['user_id'],
                    title=channel_data.get('title'),
                    username=channel_data.get('username'),
                    photo_base64=channel_data.get('photo_base64')
                )
                await session.merge(channel)

                # Сохраняем посты
                if channel_data.get('last_posts'):
                    for post_data in channel_data['last_posts']:
                        post = ChannelPost(
                            channel_id=channel.id,
                            text=post_data.get('text'),
                            media_base64=post_data.get('media_base64')
                        )
                        session.add(post)

            await session.commit()
        return True


db = DatabaseSQLAlchemy()
# Пример использования:
"""
# Инициализация
db = DatabaseSQLAlchemy()
await db.connect()

# Использование
await db.increment_check_count(user_id)
if await db.should_cleanup_images(user_id):
    await db.cleanup_user_images(user_id)

# Закрытие
await db.close()
"""
