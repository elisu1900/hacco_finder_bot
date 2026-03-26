from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    telegram_post_link: Mapped[str] = mapped_column(String(255), unique=True)
    external_product_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_id: Mapped[str] = mapped_column(String(100))
    message_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Product id={self.id} brand={self.brand!r} category={self.category!r} color={self.color!r}>"


class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_username: Mapped[str] = mapped_column(String(100), unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<MonitoredChannel id={self.id} username={self.channel_username!r}>"
