import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from database.models import Base, Product, MonitoredChannel, AllowedUser, InviteCode
from config import DATABASE_PATH


def _db_url() -> str:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    return f"sqlite+aiosqlite:///{DATABASE_PATH}"


engine = create_async_engine(_db_url(), echo=False)
SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


DEFAULT_CHANNELS = [
    "@cnfansfinds9",
    "@hacooesp",
    "@SPAINHACOOLINKS",
]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    for username in DEFAULT_CHANNELS:
        await add_channel(username)


def get_session() -> AsyncSession:
    return SessionFactory()


async def search_products_by_brand(brand: str, limit: int = 10) -> list[Product]:
    since = datetime.now(timezone.utc) - timedelta(days=365)
    async with SessionFactory() as session:
        result = await session.execute(
            select(Product)
            .where(
                Product.brand.ilike(f"%{brand}%"),
                Product.created_at >= since,
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def search_products(brand: str, category: str, color: str) -> list[Product]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Product)
            .where(
                Product.brand.ilike(brand),
                Product.category.ilike(category),
                Product.color.ilike(color),
            )
            .order_by(Product.created_at.desc())
        )
        return list(result.scalars().all())


async def get_categories_for_brand(brand: str) -> list[str]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Product.category)
            .where(Product.brand.ilike(brand))
            .distinct()
        )
        return [row[0] for row in result.all()]


async def get_colors_for_brand_category(brand: str, category: str) -> list[str]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Product.color)
            .where(
                Product.brand.ilike(brand),
                Product.category.ilike(category),
            )
            .distinct()
        )
        return [row[0] for row in result.all()]


async def add_product(
    brand: str,
    category: str,
    color: str,
    title: str,
    description: str,
    telegram_post_link: str,
    external_product_link: str | None,
    channel_id: str,
    message_id: int,
) -> bool:
    """Insert a product. Returns True if inserted, False if duplicate."""
    async with SessionFactory() as session:
        existing = await session.execute(
            select(Product).where(Product.telegram_post_link == telegram_post_link)
        )
        if existing.scalar_one_or_none() is not None:
            return False
        product = Product(
            brand=brand,
            category=category,
            color=color,
            title=title,
            description=description,
            telegram_post_link=telegram_post_link,
            external_product_link=external_product_link,
            channel_id=channel_id,
            message_id=message_id,
        )
        session.add(product)
        await session.commit()
        return True


async def add_channel(channel_username: str) -> bool:
    """Add a channel to monitor. Returns True if added, False if already exists."""
    async with SessionFactory() as session:
        existing = await session.execute(
            select(MonitoredChannel).where(MonitoredChannel.channel_username == channel_username)
        )
        if existing.scalar_one_or_none() is not None:
            return False
        channel = MonitoredChannel(channel_username=channel_username)
        session.add(channel)
        await session.commit()
        return True


async def remove_channel(channel_username: str) -> bool:
    """Remove a monitored channel. Returns True if removed, False if not found."""
    async with SessionFactory() as session:
        result = await session.execute(
            select(MonitoredChannel).where(MonitoredChannel.channel_username == channel_username)
        )
        channel = result.scalar_one_or_none()
        if channel is None:
            return False
        session.delete(channel)
        await session.commit()
        return True


async def add_allowed_user(user_id: int, username: str | None) -> bool:
    async with SessionFactory() as session:
        existing = await session.execute(
            select(AllowedUser).where(AllowedUser.user_id == user_id)
        )
        if existing.scalar_one_or_none() is not None:
            return False
        session.add(AllowedUser(user_id=user_id, username=username))
        await session.commit()
        return True


async def remove_allowed_user(user_id: int) -> bool:
    async with SessionFactory() as session:
        result = await session.execute(
            select(AllowedUser).where(AllowedUser.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        session.delete(user)
        await session.commit()
        return True


async def is_allowed_user(user_id: int) -> bool:
    async with SessionFactory() as session:
        result = await session.execute(
            select(AllowedUser).where(AllowedUser.user_id == user_id)
        )
        return result.scalar_one_or_none() is not None


async def get_allowed_users() -> list[AllowedUser]:
    async with SessionFactory() as session:
        result = await session.execute(select(AllowedUser).order_by(AllowedUser.added_at))
        return list(result.scalars().all())


async def create_invite_code(code: str) -> None:
    async with SessionFactory() as session:
        session.add(InviteCode(code=code))
        await session.commit()


async def use_invite_code(code: str, user_id: int, username: str | None) -> bool:
    """Returns True if code was valid and user was registered."""
    async with SessionFactory() as session:
        result = await session.execute(
            select(InviteCode).where(InviteCode.code == code, InviteCode.used == False)  # noqa: E712
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            return False
        invite.used = True
        session.add(AllowedUser(user_id=user_id, username=username))
        await session.commit()
        return True


async def get_channels() -> list[MonitoredChannel]:
    async with SessionFactory() as session:
        result = await session.execute(select(MonitoredChannel).order_by(MonitoredChannel.added_at))
        return list(result.scalars().all())
