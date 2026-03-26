import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from database.models import Base, Product, MonitoredChannel
from config import DATABASE_PATH


def _db_url() -> str:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    return f"sqlite+aiosqlite:///{DATABASE_PATH}"


engine = create_async_engine(_db_url(), echo=False)
SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    return SessionFactory()


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


async def get_channels() -> list[MonitoredChannel]:
    async with SessionFactory() as session:
        result = await session.execute(select(MonitoredChannel).order_by(MonitoredChannel.added_at))
        return list(result.scalars().all())
